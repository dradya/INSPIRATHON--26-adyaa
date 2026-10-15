"""Vault agent for Aegis: answers from the LOCAL index (real file data).
Open questions can use the gateway (cloud) with redacted aggregates only —
raw names and paths never leave. Every cloud call is ledger-logged there."""
import re

from . import db, privacy, storage

SUGGESTIONS = ["What can I delete?", "Show duplicates",
               "Is my data private?", "Find my resume"]


def _gb(b):
    if not b:
        return "0 B"
    if b >= 1073741824:
        return f"{b / 1073741824:.1f} GB"
    return f"{round(b / 1048576)} MB"


def _indexed():
    r = db.q("SELECT COUNT(*) FROM files", one=True)
    return (r[0] or 0) > 0


def answer(text):
    t = (text or "").lower().strip()
    if not t:
        return {"reply": "Ask me to find files, free space, or audit privacy.", "tab": None}
    if re.match(r"^(hi|hello|hey|yo)\b", t) and len(t) < 24:
        return {"reply": "Hey! I read your local index. Try “what can I delete?” or “is my data private?”.", "tab": None}
    if "help" in t or "what can you" in t:
        return {"reply": ("I can:\n• find files (“find resume”, “show me large videos”)\n"
                          "• free space (“what can I delete?”, “show duplicates”)\n"
                          "• audit privacy (“is my data private?”)\n"
                          "• advise organizing (“how should I organize Downloads?”)"),
                "tab": None}
    if not _indexed():
        return {"reply": "Nothing indexed yet — scan a folder from the Dashboard first, then ask away.", "tab": "dashboard"}

    if re.search(r"duplicat|copy|copies|same file", t):
        gs = storage.DUP_RESULTS
        if not gs:
            return {"reply": "No duplicate scan yet — open Storage and hit “Find duplicates”, then ask again.", "tab": "storage"}
        waste = sum(g["waste"] for g in gs)
        lines = [f"• {len(g['files'])}× {g['files'][0]['path'].split('/')[-1].split(chr(92))[-1]} ({_gb(g['files'][0]['size'])} each)" for g in gs[:4]]
        return {"reply": f"{len(gs)} duplicate groups wasting {_gb(waste)}:\n" + "\n".join(lines), "tab": "storage"}

    if re.search(r"private|privacy|pii|sensitive|leak|safe|cloud|redact", t) and not re.search(r"space|delete|free|big", t):
        tiers = {r[0]: r[1] for r in db.q("SELECT tier, COUNT(*) FROM files GROUP BY tier")}
        sens = tiers.get("Sensitive", 0)
        if not sens:
            return {"reply": "Clean — no Sensitive-tier files detected. The Privacy Ledger holds the proof.", "tab": "ledger"}
        rows = db.q("SELECT name FROM files WHERE tier='Sensitive' ORDER BY size DESC LIMIT 3")
        ex = "\n".join(f"• {r['name']}" for r in rows)
        return {"reply": (f"{sens} Sensitive files, all withheld from any cloud call and redacted on-device.\nBiggest:\n{ex}\n\nOpen the Ledger for per-request proof."), "tab": "ledger"}

    if re.search(r"space|storage|big|largest|free|delete|hog|cleanup", t):
        n = db.q("SELECT COUNT(*), COALESCE(SUM(size),0) FROM files", one=True)
        big = db.q("SELECT name, size FROM files ORDER BY size DESC LIMIT 5")
        waste = sum(g["waste"] for g in storage.DUP_RESULTS)
        lines = "\n".join(f"• {r['name']} — {_gb(r['size'])}" for r in big)
        return {"reply": (f"{_gb(n[1])} across {n[0]} files.\nBiggest:\n{lines}\n"
                          f"Duplicates could free {_gb(waste)}. Opening cleanup…"), "tab": "storage"}

    if re.search(r"organiz|organise|mess|chaos|sort|advice|suggest|tidy", t):
        cats = db.q("SELECT ext, SUM(size) FROM files GROUP BY ext ORDER BY 2 DESC LIMIT 1", one=True)
        return {"reply": ("Top advice: run Organize on Downloads (dry-run, you approve every move). "
                          f"Biggest extension family is {cats[0] or 'mixed'} — sort those into type folders first."), "tab": "organize"}

    m = re.match(r"^(find|search|look for|show me|where is|where'?s|get|open)\s+(.+)", t)
    if m or (re.search(r"resume|photo|video|document|pdf|mp4|jpg|ppt", t) and "how many" not in t):
        from . import search as _search
        q = (m.group(2) if m else t).strip("?.,! ")
        r = _search.search(q, limit=6)
        if not r["results"]:
            return {"reply": f"Nothing matches “{q}”. Try an extension (pdf, mp4) or the Explorer.", "tab": "search"}
        lines = "\n".join(f"• {x['name']} ({_gb(x['size'])}){' ⚠️' if x['tier'] == 'Sensitive' else ''}" for x in r["results"][:5])
        return {"reply": f"Found:\n{lines}", "tab": "search"}

    if re.search(r"thank", t):
        return {"reply": "Anytime — go reclaim those gigabytes. 🧹", "tab": None}
    if re.search(r"how many|summary|status|overview|report", t):
        n = db.q("SELECT COUNT(*), COALESCE(SUM(size),0) FROM files", one=True)
        return {"reply": f"{n[0]} files indexed, {_gb(n[1])} total. Ask “what can I delete?” for the cleanup plan.", "tab": None}

    # open question → cloud ONLY if a provider is configured (redacted aggregates)
    from . import config
    if not config.SETTINGS["offline"] and config.SETTINGS["provider"] != "local-rules" and config.SETTINGS["api_key"]:
        n = db.q("SELECT COUNT(*), COALESCE(SUM(size),0) FROM files", one=True)
        original = f"User asks: {t}. Index: {n[0]} files, {n[1]} bytes."
        res = privacy.gateway(purpose="agent-chat", original=original,
                              prompt=("You are a file-manager assistant. Stats only, no filenames were sent. Reply JSON {\"reply\": \"...\"}. " + original),
                              local_fn=lambda: {"reply": None})
        if res.get("ok") and isinstance(res.get("data"), dict) and res["data"].get("reply"):
            return {"reply": res["data"]["reply"], "tab": None}
    return {"reply": ("I work best on index questions — try:\n• “what can I delete?”\n• “show duplicates”\n• “is my data private?”\n• “find …”"), "tab": None}
