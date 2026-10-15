"""Aegis HTTP API. Binds 127.0.0.1 only; Host/Origin guard rejects
non-localhost callers (DNS rebinding / cross-site). No permanent deletes
except confirmed quarantine-empty."""
import os
import re
import sys
from pathlib import Path

import mimetypes

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import config, db
from . import agent, changes, filesys, indexer, organize, privacy, search, storage, unnamed

def _app_dir():
    # frozen (PyInstaller): --add-data lands under sys._MEIPASS
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


FRONTEND = _app_dir() / "frontend" / "index.html"
LOCAL_HOST = re.compile(r"^(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$")
LOCAL_ORIGIN = re.compile(r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$")

app = FastAPI(title="Aegis")
# self-hosted fonts (offline-safe): /fonts/*.woff2 next to index.html
app.mount("/fonts", StaticFiles(directory=str(FRONTEND.parent / "fonts")),
          name="fonts")


@app.middleware("http")
async def host_guard(request: Request, call_next):
    host = (request.headers.get("host") or "").lower()
    if not LOCAL_HOST.match(host):
        return JSONResponse({"error": "forbidden: non-local host"}, 403)
    origin = request.headers.get("origin") or ""
    if origin and not LOCAL_ORIGIN.match(origin):
        return JSONResponse({"error": "forbidden: non-local origin"}, 403)
    return await call_next(request)


@app.get("/")
def index():
    return FileResponse(str(FRONTEND))


@app.get("/manifest.json")
def manifest():
    m = FRONTEND.parent / "manifest.json"
    if m.exists():
        return FileResponse(str(m), media_type="application/manifest+json")
    return JSONResponse({
        "name": "Aegis — Private AI File Manager",
        "short_name": "Aegis Web",
        "start_url": "/",
        "display": "standalone"
    })


@app.get("/sw.js")
def service_worker():
    sw = FRONTEND.parent / "sw.js"
    if sw.exists():
        return FileResponse(str(sw), media_type="application/javascript")
    return Response("self.addEventListener('install', e => self.skipWaiting());",
                    media_type="application/javascript")


@app.get("/favicon.ico")
@app.get("/aegis.ico")
def favicon():
    ico = _app_dir() / "aegis.ico"
    if ico.exists():
        return FileResponse(str(ico), media_type="image/x-icon")
    return Response(status_code=404)


@app.get("/api/health")
def health():
    try:
        indexer.start_upgrade()
    except Exception:
        pass
    return {"ok": True, "embedder": indexer.embedder_name(),
            "offline": config.SETTINGS["offline"],
            "provider": config.SETTINGS["provider"]}


# ---------------- settings ----------------
@app.get("/api/settings")
def get_settings():
    s = dict(config.SETTINGS)
    s["api_key"] = "****" if s["api_key"] else ""  # never leak the key
    return s


@app.post("/api/settings")
def set_settings(body: dict):
    for k in ("provider", "model", "base_url", "ollama_url", "ollama_model"):
        if k in body:
            config.SETTINGS[k] = str(body[k])[:500]
    if body.get("api_key"):
        config.SETTINGS["api_key"] = str(body["api_key"])
    if body.get("clear_key"):
        config.SETTINGS["api_key"] = ""
    return get_settings()


@app.post("/api/offline")
def set_offline(body: dict):
    config.SETTINGS["offline"] = bool(body.get("on"))
    return {"offline": config.SETTINGS["offline"]}


# ---------------- scan / search ----------------
@app.post("/api/scan")
def scan(body: dict):
    roots = [os.path.abspath(p) for p in (body.get("paths") or [])
             if os.path.isdir(p)]
    if not roots:
        roots = [os.path.expanduser("~")]
    return indexer.scan_roots(roots)


@app.get("/api/scan/progress")
def scan_progress():
    return indexer.PROGRESS


@app.post("/api/scan/stop")
def scan_stop():
    return indexer.stop_scan()


@app.get("/api/scan/history")
def scan_history():
    return [dict(r) for r in
            db.q("SELECT * FROM scans ORDER BY id DESC LIMIT 10")]


@app.get("/api/search")
def do_search(q: str = "", limit: int = 30):
    return search.search(q, min(limit, 100))


@app.post("/api/redact-test")
def redact_test(body: dict):
    text = (body.get("text") or "")[:4000]
    red, spans, counts = privacy.redact(text, use_spacy=bool(body.get("spacy")))
    guarded, residual = privacy.egress_guard(red)
    back = privacy.VAULT.rehydrate(guarded)
    return {"redacted": red, "guarded": guarded, "spans": spans,
            "counts": counts, "residual": residual,
            "rehydrated": back, "roundtrip_ok": back == text}


# ---------------- explorer ----------------
@app.get("/api/drives")
def api_drives():
    home = os.path.expanduser("~")
    specials = [{"label": n, "path": os.path.join(home, n)}
                for n in ("Desktop", "Documents", "Downloads", "Pictures",
                          "Music", "Videos") if os.path.isdir(os.path.join(home, n))]
    return {"drives": filesys.drives(), "home": home, "specials": specials}


@app.get("/api/tree")
def api_tree(path: str = ""):
    return {"children": filesys.tree(path or os.path.expanduser("~"))}


@app.get("/api/ls")
def api_ls(path: str = "", power: bool = False):
    if not path:
        return {"error": "missing path", "items": []}
    return filesys.ls(path, power=power)


@app.post("/api/open")
def api_open(body: dict):
    return filesys.open_path(body.get("path", ""))


@app.post("/api/reveal")
def api_reveal(body: dict):
    return filesys.reveal(body.get("path", ""))


@app.get("/api/file/read")
def api_file_read(path: str = ""):
    if not path:
        return JSONResponse({"ok": False, "error": "No path provided"}, 400)
    p = os.path.normpath(os.path.abspath(path))
    if not os.path.exists(p):
        return JSONResponse({"ok": False, "error": "File not found"}, 404)
    if os.path.isdir(p):
        return JSONResponse({"ok": False, "error": "Path is a folder"}, 400)

    try:
        st = os.stat(p)
        size = st.st_size
        filename = os.path.basename(p)
        ext = os.path.splitext(filename)[1].lower()

        mime, _ = mimetypes.guess_type(p)
        if not mime:
            if ext in config.TEXT_EXTS or ext in {".env", ".gitignore", ".gitattributes", ".dockerignore", ".lock", ".cfg", ".conf", ".pyi", ".log", ".jsonl"}:
                mime = "text/plain"
            elif ext in {".exe", ".msi", ".dll", ".bin"}:
                mime = "application/x-msdownload"
            else:
                mime = "application/octet-stream"

        is_image = mime.startswith("image/")
        is_pdf = mime == "application/pdf"
        is_audio = mime.startswith("audio/")
        is_video = mime.startswith("video/")

        content = ""
        is_text = False
        truncated = False

        if not (is_image or is_pdf or is_audio or is_video):
            try:
                with open(p, "rb") as fh:
                    sample = fh.read(1024)
                    if b"\0" not in sample:
                        is_text = True
            except Exception:
                pass

            if is_text or ext in config.TEXT_EXTS:
                is_text = True
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read(300_000)
                        if fh.read(1):
                            truncated = True
                except Exception as ex:
                    content = f"Error reading content: {ex}"

        row = db.q("SELECT tier, pii, snippet FROM files WHERE path=?", (p,), one=True)
        tier = row["tier"] if row else "Public"
        pii = row["pii"] if row else ""
        if not content and row and row["snippet"]:
            content = row["snippet"]

        return {
            "ok": True,
            "path": p,
            "name": filename,
            "folder": os.path.dirname(p),
            "ext": ext,
            "size": size,
            "mtime": st.st_mtime,
            "mime": mime,
            "is_text": is_text,
            "is_image": is_image,
            "is_pdf": is_pdf,
            "is_audio": is_audio,
            "is_video": is_video,
            "content": content,
            "truncated": truncated,
            "tier": tier,
            "pii": pii
        }
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, 500)


@app.get("/api/file/raw")
def api_file_raw(path: str = ""):
    if not path:
        return Response("Missing path", status_code=400)
    p = os.path.normpath(os.path.abspath(path))
    if not os.path.exists(p):
        return Response("File not found", status_code=404)
    if os.path.isdir(p):
        return Response("Path is a directory", status_code=400)

    filename = os.path.basename(p)
    mime, _ = mimetypes.guess_type(p)
    if not mime:
        ext = os.path.splitext(filename)[1].lower()
        if ext in config.TEXT_EXTS or ext in {".env", ".gitignore", ".gitattributes", ".dockerignore", ".lock", ".cfg", ".conf", ".pyi", ".log", ".jsonl"}:
            mime = "text/plain; charset=utf-8"
        else:
            mime = "application/octet-stream"

    return FileResponse(
        p,
        media_type=mime,
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )



# ---------------- storage ----------------
@app.get("/api/storage/overview")
def storage_overview():
    return storage.overview()


@app.get("/api/storage/treemap")
def storage_treemap(path: str = ""):
    return storage.treemap(path)


@app.get("/api/storage/largest")
def storage_largest(n: int = 50):
    return storage.largest(min(n, 200))


@app.get("/api/storage/stale")
def storage_stale():
    return storage.stale_large()


@app.get("/api/storage/junk")
def storage_junk():
    return storage.junk_files()


@app.post("/api/dups/start")
def dups_start():
    return storage.start_dups()


@app.get("/api/dups/status")
def dups_status():
    return {**storage.DUP_PROGRESS, "groups": storage.DUP_RESULTS}


@app.post("/api/quarantine")
def api_quarantine(body: dict):
    return storage.quarantine(body.get("paths") or [])


@app.post("/api/quarantine/undo")
def api_quarantine_undo(body: dict):
    return storage.quarantine_undo(body.get("batch", ""))


@app.post("/api/quarantine/empty")
def api_quarantine_empty(body: dict):
    return storage.quarantine_empty(confirm=bool(body.get("confirm")))


@app.post("/api/insights")
def api_insights():
    return storage.ai_insights()


@app.post("/api/agent")
def api_agent(body: dict):
    return agent.answer((body or {}).get("text", ""))


# ---------------- organize ----------------
@app.post("/api/organize/plan")
def organize_plan(body: dict):
    return organize.make_plan(body.get("base", ""),
                             recursive=bool(body.get("recursive")))


@app.post("/api/organize/apply")
def organize_apply(body: dict):
    return organize.apply_plan(body.get("batch", ""), body.get("selected") or [])


@app.post("/api/organize/undo")
def organize_undo(body: dict):
    return organize.undo_batch(body.get("batch", ""))


# ---------------- dashboard (one call for the whole overview) ----------------
@app.get("/api/dashboard")
def dashboard():
    ov = storage.overview()
    n = db.q("SELECT COUNT(*), COALESCE(SUM(size),0) FROM files", one=True)
    tiers = {r[0]: r[1] for r in
             db.q("SELECT tier, COUNT(*) FROM files GROUP BY tier")}
    st = db.q("SELECT COUNT(*), COALESCE(SUM(bytes_sent),0) FROM ledger WHERE egress=1",
              one=True)
    ent = db.q("SELECT COALESCE(SUM(json_array_length(json_extract(entities,'$.spans'))),0)"
               " FROM ledger", one=True)
    withheld = db.q("SELECT COALESCE(SUM(files_withheld),0) FROM ledger", one=True)
    scans = [dict(r) for r in db.q("SELECT * FROM scans ORDER BY id DESC LIMIT 5")]
    recent = [dict(r) for r in
              db.q("SELECT id, ts, purpose, provider, egress, bytes_sent, files_sent,"
                   " files_withheld, residual, ok FROM ledger ORDER BY id DESC LIMIT 5")]
    largest = [dict(r) for r in db.q(
        "SELECT path, name, size, mtime, tier FROM files ORDER BY size DESC LIMIT 5")]
    sens = []
    for r in db.q("SELECT path, name, size, snippet FROM files WHERE tier='Sensitive'"
                  " ORDER BY size DESC LIMIT 5"):
        _red, spans, _c = privacy.redact(
            f"{r['name']}\n{(r['snippet'] or '')[:2000]}")
        sens.append({"path": r["path"], "name": r["name"], "size": r["size"],
                     "types": sorted({s["type"] for s in spans})[:3]})
    try:
        top_folders = storage.treemap("")["dirs"][:7]
    except Exception:
        top_folders = []
    return {
        "indexed": (n[0] or 0) > 0, "files": n[0] or 0, "total": n[1] or 0,
        "reclaimable": ov["reclaimable"], "junk_count": ov["junk_count"],
        "dup_groups": ov["dup_groups"], "dup_waste": ov["dup_waste"],
        "by_category": ov["by_category"][:6],
        "sensitive": tiers.get("Sensitive", 0), "internal": tiers.get("Internal", 0),
        "cloud_requests": st[0] or 0, "bytes_sent": st[1] or 0,
        "entities": (ent[0] if ent else 0) or 0,
        "withheld": (withheld[0] if withheld else 0) or 0,
        "scans": scans, "recent_ledger": recent,
        "largest": largest, "sensitive": sens, "top_folders": top_folders,
        "sensitive_count": tiers.get("Sensitive", 0),
    }


# ---------------- ledger ----------------
@app.get("/api/ledger")
def ledger_list(limit: int = 50):
    rows = db.q("SELECT * FROM ledger ORDER BY id DESC LIMIT ?", (min(limit, 200),))
    out = []
    for r in rows:
        d = dict(r)
        import json as _j
        try:
            d["entities"] = _j.loads(d["entities"] or "{}")
        except Exception:
            d["entities"] = {}
        out.append(d)
    stats = db.q("""SELECT COUNT(*), COALESCE(SUM(bytes_sent),0),
                    COALESCE(SUM(residual),0) FROM ledger WHERE egress=1""",
                 one=True)
    red = db.q("SELECT COALESCE(SUM(json_array_length(json_extract(entities,'$.spans'))),0) FROM ledger",
               one=True)
    withheld = db.q("SELECT COALESCE(SUM(files_withheld),0) FROM ledger", one=True)
    return {"rows": out,
            "stats": {"cloud_requests": stats[0], "bytes_sent": stats[1],
                      "residual": stats[2],
                      "entities_redacted": (red[0] if red else 0) or 0,
                      "withheld": (withheld[0] if withheld else 0) or 0}}


# ---------------- change engine (visual confirmation -> commit) ----------------
@app.post("/api/change/preview")
def api_change_preview(body: dict):
    kind = body.get("kind", "")
    return changes.preview(kind, body)


@app.post("/api/change/commit")
def api_change_commit(body: dict):
    token = body.get("token", "")
    return changes.commit(token)


@app.post("/api/change/cancel")
def api_change_cancel(body: dict):
    token = body.get("token", "")
    return changes.cancel(token)


@app.get("/api/history")
def api_history():
    return {"batches": changes.history()}


# ---------------- recycle bin ----------------
@app.get("/api/bin")
def api_bin():
    return changes.bin_items()


# ---------------- unnamed files & suggestions ----------------
@app.get("/api/unnamed")
def api_unnamed(path: str = ""):
    return unnamed.find_unnamed(path)


# ---------------- sensitive tiers breakdown & grouping ----------------
@app.get("/api/privacy/tiers")
def privacy_tiers():
    counts = {r[0]: r[1] for r in db.q("SELECT tier, COUNT(*) FROM files GROUP BY tier")}
    bytes_by_tier = {r[0]: (r[1] or 0) for r in db.q("SELECT tier, SUM(size) FROM files GROUP BY tier")}

    type_counts = {}
    rows = db.q("SELECT pii FROM files WHERE pii != ''")
    for r in rows:
        for t in (r["pii"] or "").split(","):
            t = t.strip()
            if t:
                type_counts[t] = type_counts.get(t, 0) + 1

    sens_files = [dict(r) for r in db.q(
        "SELECT id, path, name, folder, ext, size, mtime, tier, pii, snippet FROM files WHERE tier='Sensitive' ORDER BY size DESC LIMIT 40")]
    internal_files = [dict(r) for r in db.q(
        "SELECT id, path, name, folder, ext, size, mtime, tier, pii, snippet FROM files WHERE tier='Internal' ORDER BY size DESC LIMIT 20")]
    public_files = [dict(r) for r in db.q(
        "SELECT id, path, name, folder, ext, size, mtime, tier, snippet FROM files WHERE tier='Public' ORDER BY size DESC LIMIT 20")]

    return {
        "summary": {
            "Sensitive": {"count": counts.get("Sensitive", 0), "bytes": bytes_by_tier.get("Sensitive", 0)},
            "Internal": {"count": counts.get("Internal", 0), "bytes": bytes_by_tier.get("Internal", 0)},
            "Public": {"count": counts.get("Public", 0), "bytes": bytes_by_tier.get("Public", 0)},
        },
        "entity_types": sorted(type_counts.items(), key=lambda x: -x[1]),
        "sensitive_files": sens_files,
        "internal_files": internal_files,
        "public_files": public_files
    }
