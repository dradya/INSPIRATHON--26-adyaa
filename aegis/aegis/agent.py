"""Vault agent for Aegis: answers from the LOCAL index (real file data).
Gives clickable results that take the user directly into the Explorer.
100% on-device by default; never leaks raw names to cloud.
"""
import os
import re

from . import db, privacy, search, storage


def _gb(b):
    if not b:
        return "0 B"
    if b >= 1073741824:
        return f"{b / 1073741824:.1f} GB"
    if b >= 1048576:
        return f"{round(b / 1048576)} MB"
    if b >= 1024:
        return f"{round(b / 1024)} KB"
    return f"{b} B"


def _indexed():
    r = db.q("SELECT COUNT(*) FROM files", one=True)
    return (r[0] or 0) > 0


def answer(text):
    t = (text or "").lower().strip()
    if not t:
        return {"reply": "Ask me to find files, free space, or audit privacy.", "tab": None, "items": []}

    if re.match(r"^(hi|hello|hey|yo)\b", t) and len(t) < 24:
        return {
            "reply": "Hey! I'm your on-device Vault Agent. Try asking “Find my notes about inheritance and polymorphism” or “What can I delete?”.",
            "tab": None,
            "items": []
        }

    if "help" in t or "what can you" in t:
        return {
            "reply": ("I can:\n"
                      "• Find files by meaning (“Find my notes about inheritance and polymorphism”)\n"
                      "• Free up space & duplicates (“What can I delete?”, “Show duplicates”)\n"
                      "• Locate unnamed & messy files (“Suggest names for unnamed files”)\n"
                      "• Audit privacy & sensitive tiers (“Is my data private?”)"),
            "tab": None,
            "items": []
        }

    if not _indexed():
        return {
            "reply": "No files indexed yet — run a scan from the Dashboard or Explorer first, then ask away.",
            "tab": "dashboard",
            "items": []
        }

    # 1. Duplicates
    if re.search(r"duplicat|copy|copies|same file", t):
        gs = storage.DUP_RESULTS
        if not gs:
            return {
                "reply": "No duplicate scan run yet. Open Storage and click “Find duplicates” to identify matching files.",
                "tab": "storage",
                "items": []
            }
        waste = sum(g["waste"] for g in gs)
        items = []
        lines = []
        for g in gs[:5]:
            f0 = g["files"][0]
            name = os.path.basename(f0["path"])
            items.append({
                "path": f0["path"], "name": name, "folder": os.path.dirname(f0["path"]),
                "is_dir": False, "size": f0["size"], "tier": "Public",
                "badge": f"{len(g['files'])} copies"
            })
            lines.append(f"• {len(g['files'])}× {name} ({_gb(f0['size'])} each)")

        return {
            "reply": f"Found {len(gs)} duplicate groups wasting {_gb(waste)}. Click any file to view it in Explorer:\n" + "\n".join(lines),
            "tab": "storage",
            "items": items
        }

    # 2. Privacy & Sensitive Tiers
    if re.search(r"private|privacy|pii|sensitive|tier|leak|safe|cloud|redact", t) and not re.search(r"space|delete|free|big", t):
        sens_files = db.q("SELECT path, name, folder, size, tier, pii FROM files WHERE tier='Sensitive' ORDER BY size DESC LIMIT 6")
        if not sens_files:
            return {
                "reply": "All clear — zero Sensitive-tier files detected on this device. Open the Privacy Shield for full verification.",
                "tab": "ledger",
                "items": []
            }
        items = [{
            "path": r["path"], "name": r["name"], "folder": r["folder"],
            "is_dir": False, "size": r["size"], "tier": r["tier"],
            "badge": r["pii"] or "Sensitive"
        } for r in sens_files]
        lines = [f"• {r['name']} ({_gb(r['size'])}) — {r['pii'] or 'Confidential'}" for r in sens_files]
        return {
            "reply": f"Identified {len(items)} Sensitive files withheld from any cloud reasoning. Click any file to inspect in Explorer:\n" + "\n".join(lines),
            "tab": "ledger",
            "items": items
        }

    # 3. Storage / Deletion / Space
    if re.search(r"space|storage|big|largest|free|delete|cleanup|waste", t):
        n = db.q("SELECT COUNT(*), COALESCE(SUM(size),0) FROM files", one=True)
        big = db.q("SELECT path, name, folder, size, tier FROM files ORDER BY size DESC LIMIT 5")
        items = [{
            "path": r["path"], "name": r["name"], "folder": r["folder"],
            "is_dir": False, "size": r["size"], "tier": r["tier"],
            "badge": _gb(r["size"])
        } for r in big]
        lines = [f"• {r['name']} — {_gb(r['size'])}" for r in big]
        return {
            "reply": f"Indexed {_gb(n[1])} across {n[0]} files. Largest files taking space:\n" + "\n".join(lines),
            "tab": "storage",
            "items": items
        }

    # 4. Unnamed Files & Suggestions
    if re.search(r"unname|generic|untitled|suggest name|rename", t):
        from . import unnamed
        un = unnamed.find_unnamed(limit=6)
        if not un["items"]:
            return {
                "reply": "No unnamed or generic files found — your filenames look well structured!",
                "tab": "organize",
                "items": []
            }
        items = [{
            "path": x["path"], "name": x["name"], "folder": x["folder"],
            "is_dir": False, "size": x["size"], "tier": x["tier"],
            "badge": f"→ {x['suggested_name']}"
        } for x in un["items"]]
        lines = [f"• {x['name']} → suggest: “{x['suggested_name']}”" for x in un["items"][:5]]
        return {
            "reply": f"Found {un['count']} files with generic names. Click to reveal in Explorer or review in Organize:\n" + "\n".join(lines),
            "tab": "organize",
            "items": items
        }

    # 5. Natural Language Search (e.g. "Find my notes about inheritance and polymorphism")
    # Matches queries like "find ...", "where is ...", "show me ...", or general topical questions
    m = re.match(r"^(find|search|look for|show me|where is|where'?s|get|open|locate)\s+(.+)", t)
    query_str = (m.group(2) if m else t).strip("?.,! ")

    res = search.search(query_str, limit=6)
    folder_hits = res.get("folders", [])
    file_hits = res.get("results", [])

    if file_hits or folder_hits:
        items = []
        lines = []

        # Add top folders if matched
        for f in folder_hits[:2]:
            items.append({
                "path": f["path"], "name": f["name"], "folder": os.path.dirname(f["path"]),
                "is_dir": True, "size": f["size"], "tier": "Public",
                "badge": "Folder"
            })
            lines.append(f"📁 {f['name']}/ (folder)")

        # Add top files
        for x in file_hits[:5]:
            badge = " · ".join(x.get("why", [])[:1]) or x.get("match", "Match")
            items.append({
                "path": x["path"], "name": x["name"], "folder": x["folder"],
                "is_dir": False, "size": x["size"], "tier": x["tier"],
                "badge": badge
            })
            lines.append(f"📄 {x['name']} ({_gb(x['size'])}) — {badge}")

        time_hint = " (boosted by time)" if res.get("time_boost") else ""
        return {
            "reply": f"Found {len(items)} matching results{time_hint}. Click any item to jump straight to it in Explorer:\n" + "\n".join(lines),
            "tab": "explorer",
            "items": items,
            "focus_path": items[0]["path"] if items else None
        }

    if re.search(r"thank", t):
        return {"reply": "You're welcome! Always keeping your files safe and completely local.", "tab": None, "items": []}

    # Fallback to cloud reasoning IF user explicitly configured an API key and is online
    from . import config
    if not config.SETTINGS["offline"] and config.SETTINGS["provider"] != "local-rules" and config.SETTINGS["api_key"]:
        n = db.q("SELECT COUNT(*), COALESCE(SUM(size),0) FROM files", one=True)
        original = f"User asks: {t}. Index: {n[0]} files, {n[1]} bytes."
        cloud_res = privacy.gateway(
            purpose="agent-chat", original=original,
            prompt=('You are a file-manager assistant. Stats only, no filenames sent. Reply JSON {"reply": "..."}. ' + original),
            local_fn=lambda: {"reply": None}
        )
        if cloud_res.get("ok") and isinstance(cloud_res.get("data"), dict) and cloud_res["data"].get("reply"):
            return {"reply": cloud_res["data"]["reply"], "tab": None, "items": []}

    return {
        "reply": ("Try asking:\n"
                  "• “Find my notes about inheritance and polymorphism”\n"
                  "• “Where are my tax documents from last year?”\n"
                  "• “What files can I safely delete?”\n"
                  "• “Suggest names for unnamed files”\n"
                  "• “Is my sensitive data protected?”"),
        "tab": None,
        "items": []
    }
