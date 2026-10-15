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
from . import privacy

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
                blobs = [z.read(n) for n in z.namelist()
                         if n.endswith(".xml") and ("word/" in n or "slides/" in n)]
            txt = b" ".join(blobs).decode("utf-8", "ignore")
            return re.sub(r"<[^>]+>", " ", txt)[:20000]
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
        return "minilm" if _model else "hash512"
    _model_tried = True
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        return "minilm"
    except Exception:
        _model = None
        return "hash512"


def embed(texts):
    name = embedder_name()
    if name == "minilm":
        return np.asarray(_model.encode(texts, normalize_embeddings=True),
                          dtype=np.float32)
    return np.stack([hash_embed(t) for t in texts])


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
    with db._lock:  # noqa: SLF001
        c = db.conn()
        for r in rows:
            if STOP:
                break
            text = extract_text(r["path"], r["ext"] or "")
            snippet = (text or "")[:4000]
            _, spans, counts = privacy.redact(f"{r['name']}\n{snippet[:2000]}")
            types = sorted({s["type"] for s in spans})
            tier = privacy.tier_of(r["name"], r["folder"], types, r["ext"])
            c.execute("UPDATE files SET snippet=?, tier=?, indexed_at=? WHERE id=?",
                      (snippet, tier, time.time(), r["id"]))
        c.commit()


def _phase3():
    name = embedder_name()
    db.q("UPDATE files SET embedding=NULL WHERE embedder != '' AND embedder != ?",
         (name,), commit=True)
    rows = db.q("SELECT id, name, folder, snippet FROM files WHERE embedding IS NULL")
    texts = [f"{r['name']} {r['folder']} {(r['snippet'] or '')[:2000]}" for r in rows]
    for i in range(0, len(texts), 64):
        if STOP:
            break
        vecs = embed(texts[i:i + 64])
        with db._lock:  # noqa: SLF001
            c = db.conn()
            for r, v in zip(rows[i:i + 64], vecs):
                c.execute("UPDATE files SET embedding=?, embedder=? WHERE id=?",
                          (v.astype(np.float32).tobytes(), name, r["id"]))
            c.commit()


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
