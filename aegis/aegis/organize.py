"""AI organization assistant. Plans are dry-run JSON, NEVER auto-applied.
Sensitive files are withheld from the cloud and planned by local rules."""
import json
import os
import re
import shutil
import time
import uuid

from . import config, db
from . import privacy
from .filesys import is_protected_location, protected_move

PLANS = {}  # batch_id -> plan (memory only)

KEYWORD_FOLDERS = [
    ("Finance", ("bill", "invoice", "receipt", "bank", "tax", "salary", "pay", "fee")),
    ("College", ("assign", "lecture", "notes", "syllabus", "sem", "exam", "college", "lab")),
    ("Travel", ("ticket", "boarding", "hotel", "visa", "itinerary", "trip")),
    ("Legal", ("agreement", "contract", "affidavit", "certificate", "license")),
    ("Career", ("resume", "cv", "offer", "interview", "portfolio")),
    ("Medical", ("prescription", "report", "diagnos", "hospital", "medical")),
    ("Photos", ()),
    ("Receipts", ()),
]

TYPE_FOLDERS = {"image": "Images", "video": "Videos", "audio": "Audio",
                "document": "Docs", "archive": "Archives", "code": "Code",
                "app": "Installers", "temp": "Temp", "other": "Misc"}

MEANINGLESS = re.compile(
    r"^(img|dsc|screenshot|untitled|new |download|file|document|track|photo|image)"
    r"[\s_\-0-9().]*$|^[a-f0-9]{12,}$|^[0-9]{6,}$", re.I)


def _kind(ext):
    from .storage import category
    return {"Documents": "document", "Images": "image", "Videos": "video",
            "Audio": "audio", "Archives": "archive", "Code": "code",
            "Apps": "app"}.get(category(ext), "other")


def collect(base, recursive):
    items = []
    if recursive:
        for dp, _dn, fn in os.walk(base):
            for f in fn:
                items.append(os.path.join(dp, f))
                if len(items) >= config.ORGANIZE_CAP:
                    return items
    else:
        try:
            with os.scandir(base) as it:
                for e in it:
                    try:
                        if e.is_file(follow_symlinks=False):
                            items.append(e.path)
                    except OSError:
                        continue
                    if len(items) >= config.ORGANIZE_CAP:
                        break
        except OSError:
            pass
    return items[:config.ORGANIZE_CAP]


def _describe(path):
    """Redacted one-line description for the cloud payload (id assigned later)."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    name = os.path.basename(path)
    ext = os.path.splitext(name)[1].lower()
    red_name, spans, _ = privacy.redact(name)
    types = sorted({s["type"] for s in spans})
    tier = privacy.tier_of(name, os.path.dirname(path), types, ext)
    return {"path": path, "name": name, "red_name": red_name, "ext": ext,
            "size_kb": round(st.st_size / 1024, 1),
            "date": time.strftime("%Y-%m-%d", time.localtime(st.st_mtime)),
            "tier": tier, "types": types}


def local_plan(items):
    """Fallback planner: keywords -> types -> vault routing for Sensitive."""
    moves, insights = [], []
    for it in items:
        low = it["name"].lower()
        if it["tier"] == "Sensitive":
            folder = f"Private_Vault/{privacy.vault_subfolder(it['name'], it['types'])}"
            reason = "withheld from cloud; filed locally by entity type"
            src = "local-rules"
        else:
            folder, reason, src = None, "", "local-rules"
            for fname, words in KEYWORD_FOLDERS:
                if words and any(w in low for w in words):
                    folder, reason = fname, f"keyword match ({fname.lower()})"
                    break
            if not folder:
                folder = TYPE_FOLDERS.get(_kind(it["ext"]), "Misc")
                reason = f"by file type ({it['ext'] or 'no ext'})"
        new_name = it["name"]
        if MEANINGLESS.match(os.path.splitext(it["name"])[0]):
            stem = (first_sentence(it["path"]) or it["date"]).strip()[:60]
            stem = safe_name(re.sub(r"[<>:\"/\\|?*]", "", stem))
            new_name = stem + it["ext"]
            reason += "; renamed from content/date"
        moves.append({"id": it["id"], "folder": folder, "new_name": new_name,
                      "reason": reason, "source": src})
    insights.append(f"Local planner filed {len(moves)} files with no cloud call.")
    return moves, insights


def first_sentence(path):
    """Content-derived rename stem. Text files only, control-char free —
    binary garbage must never become a filename."""
    if os.path.splitext(path)[1].lower() not in config.TEXT_EXTS:
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read(2000).strip()
        m = re.split(r"[.\n]", txt, 1)
        s = re.sub(r"\s+", " ", m[0]).strip()
        if not 3 < len(s) < 80:
            return ""
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", s):
            return ""
        return s
    except OSError:
        return ""


def safe_name(name):
    return re.sub(r"[\x00-\x1f\x7f<>\"/\\|?*:]", "", name).strip() or "file"


PROMPT_TMPL = """You are a file organizer. Given files as {id, name (already
redacted), ext, size_kb, date}, reply JSON ONLY:
{"moves": [{"id": "f1", "folder": "...", "new_name": "...", "reason": "..."}],
 "insights": ["..."]}.
Rules: max 12 folders, max 2 levels deep (A/B), keep every extension,
rename ONLY meaningless names (IMG_1234, Untitled, hashes), keep other
names unchanged. Folders like Finance/Bills, College, Travel, Legal,
Career, Images, Videos, Docs. No prose.
FILES:
"""


def make_plan(base, recursive=False):
    base = os.path.abspath(base)
    if not os.path.isdir(base):
        return {"ok": False, "error": "not a folder"}
    if is_protected_location(base) or os.path.ismount(base):
        return {"ok": False, "error": "refusing system location / drive root"}
    paths = collect(base, recursive)
    items = []
    for i, p in enumerate(paths, 1):
        d = _describe(p)
        if d:
            d["id"] = f"f{i}"
            items.append(d)
    if not items:
        return {"ok": False, "error": "no files found"}
    cloud_items = [i for i in items if i["tier"] != "Sensitive"]
    withheld = [i for i in items if i["tier"] == "Sensitive"]
    original = "\n".join(
        f'{i["id"]} | {i["red_name"]} | {i["ext"]} | {i["size_kb"]}kb | {i["date"]}'
        for i in cloud_items) or "(all files withheld as Sensitive)"
    res = privacy.gateway(
        purpose="organize-plan", original=original,
        files_sent=len(cloud_items), files_withheld=len(withheld),
        prompt=PROMPT_TMPL + original,
        local_fn=lambda: {"moves": [], "insights": [], "_local": True})
    if not res["ok"]:
        return {"ok": False, "error": res.get("error", "planner failed"),
                "withheld": [w["name"] for w in withheld]}
    data = res["data"] if isinstance(res["data"], dict) else {}
    if res.get("egress") is False and data.get("_local"):
        moves, insights = local_plan(items)  # local path plans everything
        data = {"moves": moves, "insights": insights}
        source = "local-rules"
    else:
        source = "cloud"
        # cloud only planned non-sensitive; finish sensitive locally
        lmoves, linsights = local_plan(withheld)
        data = {"moves": (data.get("moves") or []) + lmoves,
                "insights": (data.get("insights") or []) + linsights}
    moves = [m for m in _validate(base, items, data.get("moves") or [])]
    batch = uuid.uuid4().hex[:8]
    PLANS[batch] = {"base": base, "items": {i["id"]: i for i in items},
                    "moves": moves}
    return {"ok": True, "batch": batch, "moves": moves,
            "insights": data.get("insights", []), "source": source,
            "withheld": [w["name"] for w in withheld],
            "ledger": {"egress": res.get("egress"),
                       "entities": res.get("entities", {}),
                       "residual": res.get("residual", 0)}}


def _validate(base, items, moves):
    by_id = {i["id"]: i for i in items}
    folders = set()
    clean = []
    for m in moves:
        i = by_id.get(m.get("id"))
        if not i:
            continue
        folder = (m.get("folder") or "Misc").strip().strip("/")
        parts = [p for p in folder.split("/") if p not in ("", ".", "..")]
        if not parts or len(parts) > 2 or ".." in folder:
            parts = ["Misc"]
        folders.add(parts[0])
        if len(folders) > 12:
            parts = ["Misc"]
        new_name = safe_name(m.get("new_name") or i["name"])
        if os.path.splitext(new_name)[1].lower() != i["ext"]:
            new_name = os.path.splitext(new_name)[0] + i["ext"]
        stem = os.path.splitext(i["name"])[0]
        if new_name != i["name"] and not MEANINGLESS.match(stem):
            new_name = i["name"]  # rename only meaningless names
        dest = os.path.abspath(os.path.join(base, *parts, new_name))
        if not dest.startswith(base + os.sep):
            continue  # no path traversal, ever
        clean.append({"id": i["id"], "old": i["path"], "dest": dest,
                      "folder": "/".join(parts), "new_name": new_name,
                      "reason": m.get("reason", "")[:200],
                      "tier": i["tier"]})
    return clean


def apply_plan(batch, selected):
    plan = PLANS.get(batch)
    if not plan:
        return {"ok": False, "error": "unknown batch"}
    base = plan["base"]
    applied = []
    for m in plan["moves"]:
        if m["id"] not in set(selected or []):
            continue
        ok, reason = protected_move(m["old"], m["dest"])
        if not ok:
            applied.append({"id": m["id"], "ok": False, "error": reason})
            continue
        try:
            os.makedirs(os.path.dirname(m["dest"]), exist_ok=True)
            dest = m["dest"]
            if os.path.exists(dest):
                stem, ext = os.path.splitext(dest)
                k = 1
                while os.path.exists(f"{stem} ({k}){ext}"):
                    k += 1
                dest = f"{stem} ({k}){ext}"
            shutil.move(m["old"], dest)
            db.q("INSERT INTO ops(batch, ts, kind, src, dst) VALUES (?,?,?,?,?)",
                 (batch, time.time(), "move", m["old"], dest), commit=True)
            applied.append({"id": m["id"], "ok": True, "dest": dest})
        except OSError as e:
            applied.append({"id": m["id"], "ok": False, "error": str(e)})
    return {"ok": True, "batch": batch, "applied": applied}


def undo_batch(batch):
    rows = db.q("SELECT * FROM ops WHERE batch=? AND undone=0 ORDER BY id DESC",
                (batch,))
    out = []
    for r in rows:
        try:
            os.makedirs(os.path.dirname(r["src"]), exist_ok=True)
            dest = r["src"]
            if os.path.exists(dest):
                stem, ext = os.path.splitext(dest)
                k = 1
                while os.path.exists(f"{stem} ({k}){ext}"):
                    k += 1
                dest = f"{stem} ({k}){ext}"
            shutil.move(r["dst"], dest)
            # remove now-empty folders (never above the move's own tree)
            d = os.path.dirname(r["dst"])
            for _ in range(3):
                try:
                    os.rmdir(d)
                except OSError:
                    break
                d = os.path.dirname(d)
            db.q("UPDATE ops SET undone=1 WHERE id=?", (r["id"],), commit=True)
            out.append({"id": r["id"], "ok": True})
        except OSError as e:
            out.append({"id": r["id"], "ok": False, "error": str(e)})
    return {"ok": True, "batch": batch, "undone": out}


def validate_json_first(raw_text):
    """Parse BEFORE rehydrating (real values may contain quotes)."""
    return json.loads(raw_text)
