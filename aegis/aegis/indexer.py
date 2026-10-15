"""3-phase background scanner. Phase 1 metadata (fast, scandir stat cache),
phase 2 content + PII + tiers, phase 3 embeddings. Unchanged files are reused."""
import hashlib
import os
import re
import threading
import time
import zipfile

import numpy as np

from . import config, db
from . import privacy, semantic

PROGRESS = {"running": False, "phase": "", "root": "", "seen": 0,
            "done": False, "error": ""}
STOP = False  # set by /api/scan/stop; checked in every scan loop

SKIP_PARTS = {"windows", "program files", "program files (x86)", "programdata",
              "appdata", "$recycle.bin", "system volume information", ".git",
              "site-packages", ".aegis", "quarantine"}
# recorded as junk but never descended into (too big / noisy)
PRUNE_PARTS = {"node_modules", "__pycache__", ".venv", "venv", ".cache",
               "site-packages", ".git"}

_model, _model_tried = None, False


def _skip(parts):
    return any(p in SKIP_PARTS for p in parts)


def iter_files(root):
    """Yield (dirpath, DirEntry) depth-first. Skips symlinks, survives perms."""
    stack = [root]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                entries = list(it)
        except (PermissionError, OSError, FileNotFoundError):
            continue
        for e in entries:
            if STOP:
                return
            try:
                if e.is_symlink():
                    continue
                if e.is_dir(follow_symlinks=False):
                    parts = [p.lower() for p in
                             os.path.relpath(e.path, root).split(os.sep)]
                    if _skip(parts):
                        continue
                    if e.name.lower() in PRUNE_PARTS:
                        yield ("__junkdir__", e)
                        continue
                    stack.append(e.path)
                elif e.is_file(follow_symlinks=False):
                    yield (cur, e)
            except (PermissionError, OSError):
                continue


def extract_text(path, ext):
    try:
        if ext == ".pdf":
            from pypdf import PdfReader
            r = PdfReader(path)
            return "\n".join((p.extract_text() or "") for p in r.pages[:20])[:20000]
        if ext in (".docx", ".pptx"):
            with zipfile.ZipFile(path) as z:
                blobs = [z.read(n) for n in sorted(z.namelist())
                         if n == "word/document.xml"
                         or re.match(r"ppt/slides/slide\d+\.xml$", n)]
            txt = b" ".join(blobs).decode("utf-8", "ignore")
            txt = re.sub(r"</w:p>|</a:p>", "\n", txt)
            return re.sub(r"[ \t]+", " ", re.sub(r"<[^>]+>", " ", txt))[:20000]
        if ext == ".ipynb":
            import json as _json
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                nb = _json.load(f)
            return "\n".join("".join(c.get("source", [])) for c in nb.get("cells", []))[:20000]
        if ext in config.TEXT_EXTS:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(200000)
    except Exception:
        pass
    return ""


def hash_embed(text, dim=512):
    v = np.zeros(dim, dtype=np.float32)
    toks = re.findall(r"[a-z0-9]+", (text or "").lower())
    for t in toks:
        grams = ["w:" + t]
        if len(t) >= 3:
            grams += ["c:" + t[i:i + 3] for i in range(len(t) - 2)]
        for g in grams:
            h = hashlib.md5(g.encode()).digest()
            idx = int.from_bytes(h[:4], "little") % dim
            v[idx] += 1.0 if h[4] % 2 == 0 else -1.0
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def embedder_name():
    global _model, _model_tried
    if _model_tried:
        return "minilm" if _model else semantic.EMBEDDER
    _model_tried = True
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        return "minilm"
    except Exception:
        _model = None
        return semantic.EMBEDDER


def embed(texts, names=None):
    name = embedder_name()
    if name == "minilm":
        return np.asarray(_model.encode(texts, normalize_embeddings=True),
                          dtype=np.float32)
    names = names or [""] * len(texts)
    return np.stack([semantic.embed_text(t, n) for t, n in zip(texts, names)])


def scan_roots(roots):
    global STOP
    if PROGRESS["running"]:
        return {"started": False, "reason": "scan already running"}
    STOP = False
    t = threading.Thread(target=_run, args=(roots,), daemon=True)
    t.start()
    return {"started": True}


def stop_scan():
    global STOP
    STOP = True
    return {"stopping": True}


def _run(roots):
    PROGRESS.update(running=True, done=False, error="", seen=0)
    try:
        for root in roots:
            root = os.path.abspath(root)
            PROGRESS.update(phase="metadata", root=root, seen=0)
            db.q("INSERT INTO scans(root, phase, started) VALUES (?,?,?)",
                 (root, "metadata", time.time()), commit=True)
            sid = db.q("SELECT id FROM scans ORDER BY id DESC LIMIT 1",
                       one=True)["id"]
            _phase1(root)
            if STOP:
                break
            PROGRESS["phase"] = "content"
            _phase2()
            if STOP:
                break
            PROGRESS["phase"] = "embeddings"
            _phase3()
            if STOP:
                break
            _rollup_dirs(root)
            db.q("UPDATE scans SET phase=?, finished=?, seen=? WHERE id=?",
                 ("done", time.time(), PROGRESS["seen"], sid), commit=True)
    except Exception as e:  # noqa: BLE001 - surface in progress, keep server up
        PROGRESS["error"] = str(e)
    PROGRESS.update(running=False, done=True, phase="done")
    from . import search
    search.invalidate()


def _phase1(root):
    now = time.time()
    batch = []
    for _dir, e in iter_files(root):
        if _dir == "__junkdir__":
            continue
        try:
            st = e.stat(follow_symlinks=False)
        except OSError:
            continue
        p = e.path
        name = e.name
        ext = os.path.splitext(name)[1].lower()
        batch.append((p, name, os.path.dirname(p), ext, st.st_size,
                      st.st_mtime))
        PROGRESS["seen"] += 1
        if len(batch) >= 2000:
            _upsert_meta(batch, now)
            batch = []
    if batch:
        _upsert_meta(batch, now)


def _upsert_meta(batch, now):
    with db._lock:  # noqa: SLF001 - bulk path needs one transaction
        c = db.conn()
        for p, name, folder, ext, size, mtime in batch:
            old = c.execute("SELECT size, mtime FROM files WHERE path=?",
                            (p,)).fetchone()
            if old and old[0] == size and old[1] == mtime:
                continue  # unchanged -> reuse snippet + embedding
            c.execute("""INSERT INTO files(path, name, folder, ext, size, mtime)
                         VALUES (?,?,?,?,?,?)
                         ON CONFLICT(path) DO UPDATE SET name=excluded.name,
                           folder=excluded.folder, ext=excluded.ext,
                           size=excluded.size, mtime=excluded.mtime,
                           indexed_at=0""",
                      (p, name, folder, ext, size, mtime))
        c.commit()


def _phase2():
    rows = db.q("""SELECT id, path, name, folder, ext FROM files
                   WHERE indexed_at=0 LIMIT 200000""")
    for i in range(0, len(rows), 200):
        if STOP:
            break
        updates = []
        for r in rows[i:i + 200]:
            if STOP:
                break
            text = extract_text(r["path"], r["ext"] or "")
            snippet = (text or "")[:8000]
            _, spans, counts = privacy.redact(f"{r['name']}\n{snippet[:3000]}")
            types = sorted({s["type"] for s in spans})
            tier = privacy.tier_of(r["name"], r["folder"], types, r["ext"])
            updates.append((snippet, tier, ",".join(types), time.time(), r["id"]))
        with db._lock:  # noqa: SLF001 - short batches keep the UI responsive
            c = db.conn()
            c.executemany("UPDATE files SET snippet=?, tier=?, pii=?, indexed_at=?"
                          " WHERE id=?", updates)
            c.commit()


def _embed_text_of(r):
    folder = os.path.basename(r["folder"] or "")
    return f"{semantic.split_name(r['name'])} {folder} {(r['snippet'] or '')[:3000]}"


def _phase3():
    name = embedder_name()
    db.q("UPDATE files SET embedding=NULL WHERE embedder != ?", (name,), commit=True)
    rows = db.q("SELECT id, name, folder, snippet FROM files WHERE embedding IS NULL")
    for i in range(0, len(rows), 128):
        if STOP:
            break
        chunk = rows[i:i + 128]
        vecs = embed([_embed_text_of(r) for r in chunk], [r["name"] for r in chunk])
        with db._lock:  # noqa: SLF001
            c = db.conn()
            c.executemany("UPDATE files SET embedding=?, embedder=? WHERE id=?",
                          [(v.astype(np.float32).tobytes(), name, r["id"])
                           for r, v in zip(chunk, vecs)])
            c.commit()
        PROGRESS["embedded"] = i + len(chunk)


UPGRADE = {"running": False, "done": 0, "total": 0, "phase": ""}


def start_upgrade():
    """Bring an older index up to the current meaning engine, in background."""
    if PROGRESS["running"] or UPGRADE["running"]:
        return
    threading.Thread(target=_upgrade, daemon=True).start()


def _upgrade():
    UPGRADE["running"] = True
    try:
        name = embedder_name()
        if db.get_kv("content_v") != "2":
            # PDFs/Office files were name-only before pypdf; re-read them
            db.q("""UPDATE files SET indexed_at=0 WHERE ext IN
                    ('.pdf','.docx','.pptx','.md','.txt','.ipynb','.tex')""", commit=True)
            UPGRADE["phase"] = "reading documents"
            _phase2()
            db.set_kv("content_v", "2")
        stale = db.q("SELECT COUNT(*) FROM files WHERE embedder != ? OR embedding IS NULL",
                     (name,), one=True)[0]
        if stale:
            UPGRADE.update(phase="understanding meaning", total=stale)
            _phase3()
    except Exception as e:  # noqa: BLE001 - never crash the server
        UPGRADE["phase"] = f"error: {e}"
    finally:
        UPGRADE["running"] = False
        from . import search
        search.invalidate()


def _rollup_dirs(root):
    rows = db.q("SELECT folder, SUM(size), COUNT(*) FROM files WHERE path LIKE ? GROUP BY folder",
                (root + "%",))
    with db._lock:  # noqa: SLF001
        c = db.conn()
        for folder, size, count in rows:
            parent = os.path.dirname(folder or root)
            c.execute("""INSERT INTO dirs(path, parent, size, count) VALUES (?,?,?,?)
                         ON CONFLICT(path) DO UPDATE SET parent=excluded.parent,
                           size=excluded.size, count=excluded.count""",
                      (folder, parent, size or 0, count or 0))
        c.commit()


def forget(path):
    """Drop a path (file or whole folder) from the index after it moved away."""
    p = os.path.abspath(path)
    like = p.rstrip("\\/") + os.sep + "%"
    db.q("DELETE FROM files WHERE path=? OR path LIKE ?", (p, like), commit=True)
    db.q("DELETE FROM dirs WHERE path=? OR path LIKE ?", (p, like), commit=True)


def reindex(paths, cap=3000):
    """Index specific paths right now (after rename / move / restore)."""
    global STOP
    if not PROGRESS["running"]:
        STOP = False
    batch, now = [], time.time()
    for p in paths:
        p = os.path.abspath(p)
        if os.path.isdir(p):
            for _d, e in iter_files(p):
                if _d == "__junkdir__":
                    continue
                try:
                    st = e.stat(follow_symlinks=False)
                except OSError:
                    continue
                batch.append((e.path, e.name, os.path.dirname(e.path),
                              os.path.splitext(e.name)[1].lower(), st.st_size, st.st_mtime))
                if len(batch) >= cap:
                    break
        elif os.path.isfile(p):
            st = os.stat(p)
            batch.append((p, os.path.basename(p), os.path.dirname(p),
                          os.path.splitext(p)[1].lower(), st.st_size, st.st_mtime))
    if batch:
        _upsert_meta(batch, now)
        _phase2()
        _phase3()
    from . import search
    search.invalidate()
