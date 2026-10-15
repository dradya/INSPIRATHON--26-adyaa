"""Unnamed and generic files detection with smart name suggestions.

Finds files named 'Untitled', 'IMG_1234', 'Screenshot...', 'New Document...',
or long hex/numeric hashes, and generates high-quality, human-readable
name suggestions based on document content, topics, entities, and context.
100% on-device, never touches disk without confirmation.
"""
import os
import re
import time
from pathlib import Path

from . import config, db, privacy, semantic

GENERIC_NAME_RE = re.compile(
    r"^(?:untitled(?:\s*document)?|new\s*(?:text\s*document|folder|file|document|microsoft\s*\w+)|"
    r"img|dsc|pxl|pic|photo|image|screenshot|screen\s*shot|capture|download|file|doc|document|"
    r"scan|temp|tmp|test|copy(?:\s*of)?|output|data|notes?)"
    r"(?:[\s_\-0-9().]+.*)?$|"
    r"^[a-f0-9]{10,}(?:\.[a-z0-9]+)?$|"
    r"^\d{6,}(?:\.[a-z0-9]+)?$",
    re.I
)


def is_unnamed_or_generic(filename):
    stem = os.path.splitext(filename)[0].strip()
    if not stem:
        return True
    return bool(GENERIC_NAME_RE.match(stem))


def _title_from_text(snippet):
    if not snippet:
        return ""
    lines = [line.strip() for line in snippet.splitlines() if line.strip()]
    for line in lines[:4]:
        clean = re.sub(r"^[#*=\-\d.\s]+", "", line).strip()
        clean = re.sub(r"[<>:\"/\\|?*]", "", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        if 4 <= len(clean) <= 60 and not clean.startswith("http") and not clean.isdigit():
            # capitalize nicely
            words = clean.split()
            if len(words) <= 7:
                return " ".join(w.capitalize() if not w.isupper() else w for w in words)
            return " ".join(w.capitalize() if not w.isupper() else w for w in words[:6])
    return ""


def _topic_from_text(snippet):
    if not snippet:
        return ""
    intent = semantic.understand(snippet[:2000])
    concepts = intent.get("concepts", [])
    core = intent.get("core", [])
    terms = [c.capitalize() for c in core if len(c) > 3][:3]
    if terms:
        return "_".join(terms)
    if concepts:
        return f"{concepts[0].upper()}_Notes"
    return ""


def suggest_name(path, name, ext, snippet="", tier="Public", pii_str=""):
    stem, extension = os.path.splitext(name)
    ext = ext or extension
    ext_lower = ext.lower()

    # 1. PII / Sensitive hints
    types = [t.strip() for t in pii_str.split(",") if t.strip()] if pii_str else []
    if "AADHAAR" in types:
        return f"Aadhaar_Card{ext}"
    if "PAN" in types:
        return f"PAN_Card{ext}"
    if "PASSPORT" in types:
        return f"Passport_Document{ext}"
    if "IFSC" in types or "ACCOUNT_NO" in types:
        return f"Bank_Account_Statement{ext}"

    # 2. Text / Doc / PDF / Presentation content hints
    if snippet:
        # Check for first heading or title
        title = _title_from_text(snippet)
        if title:
            clean_title = re.sub(r"[^\w\s\-]", "", title).strip()
            clean_title = re.sub(r"\s+", "_", clean_title)
            if clean_title:
                return f"{clean_title[:55]}{ext}"

        # Topic concept fallback
        topic = _topic_from_text(snippet)
        if topic:
            return f"{topic}{ext}"

    # 3. Contextual fallback (Folder + Date or Type)
    parent_folder = os.path.basename(os.path.dirname(path))
    date_str = ""
    try:
        st = os.stat(path)
        date_str = time.strftime("%Y-%m-%d", time.localtime(st.st_mtime))
    except Exception:
        date_str = time.strftime("%Y-%m-%d")

    clean_folder = re.sub(r"[^\w\-]", "", parent_folder).strip() or "Saved"

    if ext_lower in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"}:
        if "screen" in name.lower():
            return f"Screenshot_{clean_folder}_{date_str}{ext}"
        return f"Photo_{clean_folder}_{date_str}{ext}"

    if ext_lower in {".mp4", ".mov", ".mkv", ".webm"}:
        return f"Video_{clean_folder}_{date_str}{ext}"

    if ext_lower in {".pdf", ".docx", ".doc", ".txt", ".md"}:
        return f"Document_{clean_folder}_{date_str}{ext}"

    return f"File_{clean_folder}_{date_str}{ext}"


def find_unnamed(path="", limit=60):
    """Scan indexed files or specified folder for unnamed/generic files and generate suggestions."""
    items = []
    if path and os.path.isdir(path):
        # Scan folder directly
        try:
            for root, _dirs, files in os.walk(path):
                for f in files:
                    if is_unnamed_or_generic(f):
                        p = os.path.join(root, f)
                        try:
                            st = os.stat(p)
                            ext = os.path.splitext(f)[1]
                            snip = ""
                            if ext.lower() in config.TEXT_EXTS:
                                try:
                                    with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                                        snip = fh.read(2000)
                                except Exception:
                                    pass
                            suggested = suggest_name(p, f, ext, snip)
                            if suggested.lower() != f.lower():
                                items.append({
                                    "path": p, "name": f, "folder": root, "ext": ext,
                                    "size": st.st_size, "mtime": st.st_mtime,
                                    "suggested_name": suggested,
                                    "snippet": snip[:200],
                                    "tier": "Public"
                                })
                        except OSError:
                            continue
                    if len(items) >= limit:
                        break
                if len(items) >= limit:
                    break
        except Exception:
            pass
        return {"items": items, "count": len(items)}

    # From Database
    rows = db.q("SELECT id, path, name, folder, ext, size, mtime, tier, snippet, pii FROM files LIMIT 5000")
    for r in rows:
        name = r["name"] or ""
        if is_unnamed_or_generic(name):
            suggested = suggest_name(
                r["path"], name, r["ext"] or "",
                r["snippet"] or "", r["tier"] or "Public", r["pii"] or ""
            )
            if suggested.lower() != name.lower():
                items.append({
                    "id": r["id"],
                    "path": r["path"],
                    "name": name,
                    "folder": r["folder"],
                    "ext": r["ext"] or "",
                    "size": r["size"],
                    "mtime": r["mtime"],
                    "suggested_name": suggested,
                    "snippet": (r["snippet"] or "")[:200],
                    "tier": r["tier"] or "Public",
                    "pii": r["pii"] or ""
                })
        if len(items) >= limit:
            break

    return {"items": items, "count": len(items)}
