"""Storage intelligence: treemap, largest/stale/junk, duplicate finder
(size -> partial hash -> full hash), quarantine with undo, AI insights."""
import hashlib
import os
import shutil
import threading
import time
import uuid

from . import config, db
from . import privacy
from .filesys import protected_move

DUP_PROGRESS = {"running": False, "phase": "", "groups": 0, "done": False}
DUP_RESULTS = []

EXCLUDE_PARTS = {"windows", "program files", "program files (x86)", "programdata",
                 "appdata", "$recycle.bin", "system volume information", ".git",
                 "site-packages", "__pycache__", "node_modules", ".aegis", "quarantine"}

CATEGORIES = {
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".ppt", ".pptx",
                  ".xls", ".xlsx", ".csv"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp"},
    "Videos": {".mp4", ".mkv", ".mov", ".avi", ".webm"},
    "Audio": {".mp3", ".wav", ".flac", ".ogg", ".m4a"},
    "Archives": {".zip", ".rar", ".tar", ".gz", ".7z"},
    "Code": {".js", ".jsx", ".ts", ".py", ".java", ".c", ".cpp", ".html",
             ".css", ".json"},
    "Apps": {".exe", ".msi", ".dmg", ".apk"},
}


def category(ext):
    for cat, exts in CATEGORIES.items():
        if (ext or "").lower() in exts:
            return cat
    return "Other"


def _excluded(path):
    parts = {p.lower() for p in path.split(os.sep)}
    return bool(parts & EXCLUDE_PARTS)


def overview():
    r = db.q("SELECT COUNT(*), COALESCE(SUM(size),0) FROM files", one=True)
    by_cat, by_ext = {}, {}
    for row in db.q("SELECT ext, SUM(size), COUNT(*) FROM files GROUP BY ext"):
        cat = category(row[0])
        by_cat[cat] = by_cat.get(cat, 0) + (row[1] or 0)
        by_ext[row[0] or "(none)"] = {"size": row[1] or 0, "count": row[2]}
    junk = junk_files(fast=True)
    dup_waste = sum(g["waste"] for g in DUP_RESULTS)
    return {
        "count": r[0], "total": r[1] or 0,
        "by_category": sorted(by_cat.items(), key=lambda x: -x[1]),
        "top_exts": sorted(by_ext.items(), key=lambda x: -x[1]["size"])[:12],
        "junk_count": len(junk), "junk_bytes": sum(f["size"] for f in junk),
        "dup_groups": len(DUP_RESULTS), "dup_waste": dup_waste,
        "reclaimable": sum(f["size"] for f in junk) + dup_waste,
    }


def treemap(path):
    """Direct children (dirs from rollup + top files) for drill-down."""
    path = os.path.abspath(path or os.path.expanduser("~"))
    kids = db.q("SELECT path, size, count FROM dirs WHERE parent=? ORDER BY size DESC",
                (path,))
    files = db.q("SELECT path, name, size FROM files WHERE folder=? ORDER BY size DESC LIMIT 200",
                 (path,))
    return {
        "path": path,
        "dirs": [{"path": k["path"], "name": os.path.basename(k["path"]),
                  "size": k["size"], "count": k["count"]} for k in kids],
        "files": [{"path": f["path"], "name": f["name"], "size": f["size"]}
                  for f in files],
    }


def largest(n=50):
    return [dict(r) for r in db.q(
        "SELECT path, name, size, mtime, tier FROM files ORDER BY size DESC LIMIT ?", (n,))]


def stale_large(min_bytes=50 * 1024 * 1024, months=6):
    cutoff = time.time() - months * 30 * 86400
    return [dict(r) for r in db.q(
        """SELECT path, name, size, mtime, tier FROM files
           WHERE size >= ? AND mtime < ? ORDER BY size DESC LIMIT 100""",
        (min_bytes, cutoff))]


def junk_files(fast=False):
    out = []
    rows = db.q("SELECT path, name, size FROM files"
                + (" LIMIT 200000" if fast else ""))
    for r in rows:
        low = (r["path"] or "").lower()
        name = (r["name"] or "").lower()
        if (any(f"/{j}/" in low.replace(os.sep, "/") for j in
                ("node_modules", "__pycache__", ".cache", "/temp/", "/tmp/"))
                or name in config.JUNK_NAMES
                or name.endswith((".tmp", ".temp", ".bak", ".old"))):
            out.append({"path": r["path"], "name": r["name"], "size": r["size"]})
    return out


# ---------------- duplicates ----------------
def _partial(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(65536))
        try:
            f.seek(-65536, os.SEEK_END)
            h.update(f.read(65536))
        except OSError:
            pass
    return h.hexdigest()


def _full(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def start_dups():
    if DUP_PROGRESS["running"]:
        return {"started": False}
    threading.Thread(target=_dup_run, daemon=True).start()
    return {"started": True}


def _dup_run():
    global DUP_RESULTS
    DUP_PROGRESS.update(running=True, done=False, groups=0, phase="grouping by size")
    try:
        same = db.q("""SELECT size FROM files WHERE size > 0 GROUP BY size
                       HAVING COUNT(*) > 1""")
        sizes = {r["size"] for r in same}
        cands = [dict(r) for r in db.q("SELECT path, size FROM files WHERE size > 0")
                 if r["size"] in sizes and not _excluded(r["path"])]
        DUP_PROGRESS["phase"] = "partial hashing"
        partial = {}
        for c in cands:
            try:
                partial.setdefault(_partial(c["path"]), []).append(c)
            except OSError:
                continue
        DUP_PROGRESS["phase"] = "full hashing"
        groups = []
        for _ph, items in partial.items():
            if len(items) < 2:
                continue
            full = {}
            for c in items:
                try:
                    full.setdefault(_full(c["path"]), []).append(c)
                except OSError:
                    continue
            for _fh, g in full.items():
                if len(g) > 1:
                    g.sort(key=lambda x: x["path"])
                    groups.append({"hash": _fh[:16], "files": g,
                                   "waste": g[0]["size"] * (len(g) - 1)})
        groups.sort(key=lambda g: -g["waste"])
        DUP_RESULTS = groups
        DUP_PROGRESS["groups"] = len(groups)
    finally:
        DUP_PROGRESS.update(running=False, done=True, phase="done")


# ---------------- quarantine (undoable) ----------------
def quarantine(paths):
    batch = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
    moved = []
    for p in paths or []:
        ok, reason = protected_move(p, "")  # src-side checks only
        if not ok:
            moved.append({"path": p, "ok": False, "error": reason})
            continue
        dest = config.QUARANTINE / batch / os.path.basename(p)
        dest.parent.mkdir(parents=True, exist_ok=True)
        base, i = str(dest), 1
        while os.path.exists(base):
            base = f"{dest} ({i})"
            i += 1
        try:
            shutil.move(p, base)
            db.q("INSERT INTO quar(batch, orig, quar, ts) VALUES (?,?,?,?)",
                 (batch, p, base, time.time()), commit=True)
            moved.append({"path": p, "ok": True, "quar": base})
        except OSError as e:
            moved.append({"path": p, "ok": False, "error": str(e)})
    return {"batch": batch, "moved": moved}


def quarantine_undo(batch):
    rows = db.q("SELECT * FROM quar WHERE batch=? AND restored=0", (batch,))
    out = []
    for r in rows:
        try:
            os.makedirs(os.path.dirname(r["orig"]), exist_ok=True)
            shutil.move(r["quar"], r["orig"])
            db.q("UPDATE quar SET restored=1 WHERE id=?", (r["id"],), commit=True)
            out.append({"path": r["orig"], "ok": True})
        except OSError as e:
            out.append({"path": r["orig"], "ok": False, "error": str(e)})
    return {"batch": batch, "restored": out}


def quarantine_empty(confirm=False):
    if not confirm:
        return {"deleted": 0, "need_confirm": True}
    n = 0
    if config.QUARANTINE.exists():
        for child in config.QUARANTINE.iterdir():
            try:
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                n += 1
            except OSError:
                continue
    return {"deleted": n}


# ---------------- AI insights (aggregates only) ----------------
def ai_insights():
    ov = overview()
    original = (f"Storage report. Files: {ov['count']}. Total bytes: {ov['total']}. "
                f"By category: {dict(ov['by_category'])}. Junk files: {ov['junk_count']} "
                f"({ov['junk_bytes']} bytes). Duplicate groups: {ov['dup_groups']} "
                f"wasting {ov['dup_waste']} bytes.")
    prompt = ("You are a storage analyst. Given ONLY these aggregate stats "
              "(no filenames were sent), reply JSON: "
              '{"insights": [{"title": "...", "detail": "..."}]}. ' + original)

    def local():
        tips = []
        if ov["dup_waste"]:
            tips.append({"title": f"{ov['dup_groups']} duplicate groups",
                         "detail": "Review them in the Duplicates tab."})
        if ov["junk_bytes"]:
            tips.append({"title": "Build caches and temp files found",
                         "detail": "Quarantine node_modules/__pycache__/.tmp first."})
        tips.append({"title": "Largest category",
                     "detail": f"{ov['by_category'][0][0]} dominates. Check largest files."}
                    if ov["by_category"] else {"title": "Scan first",
                                               "detail": "No data yet."})
        return {"insights": tips[:4]}

    return privacy.gateway(purpose="storage-insights", original=original,
                           prompt=prompt, local_fn=local)
