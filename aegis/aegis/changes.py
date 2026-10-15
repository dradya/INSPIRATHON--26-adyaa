"""The ONLY place that changes files on disk.

Two-step contract, enforced here (not just in the UI):
    preview(kind, payload) -> {token, ops, groups, ...}   # nothing touched
    commit(token)          -> executes exactly the previewed ops

Every committed change set is journaled as a batch (ops + batches tables)
so it can be undone. Deleting = moving to Aegis' Recycle Bin; the only
permanent action is emptying the Bin, which is flagged irreversible.
"""
import os
import shutil
import time
import uuid

from . import config, db, indexer
from .filesys import is_protected_location, protected_move

PENDING = {}       # token -> change set (memory only)
TTL = 15 * 60
INVALID = set('<>:"/\\|?*') | {chr(i) for i in range(32)}


def _size(p):
    try:
        if os.path.isdir(p):
            r = db.q("SELECT size FROM dirs WHERE path=?", (p,), one=True)
            if r and r["size"]:
                return r["size"]
            total = 0
            for i, (dp, _dn, fn) in enumerate(os.walk(p)):
                for f in fn:
                    try:
                        total += os.path.getsize(os.path.join(dp, f))
                    except OSError:
                        pass
                if i > 400:
                    break
            return total
        return os.path.getsize(p)
    except OSError:
        return 0


def _free(dest):
    if not os.path.exists(dest):
        return dest
    stem, ext = os.path.splitext(dest)
    if os.path.isdir(dest):
        stem, ext = dest, ""
    k = 2
    while os.path.exists(f"{stem} ({k}){ext}"):
        k += 1
    return f"{stem} ({k}){ext}"


def _op(kind, src, dst, **extra):
    is_dir = os.path.isdir(src) if src and os.path.exists(src) else extra.pop("is_dir", False)
    return {"op": kind, "src": src, "dst": dst,
            "name": os.path.basename(src) if src else "",
            "new_name": os.path.basename(dst) if dst else "",
            "from_dir": os.path.dirname(src) if src else "",
            "to_dir": os.path.dirname(dst) if dst else "",
            "is_dir": is_dir, "size": _size(src) if src and os.path.exists(src) else 0,
            **extra}


def _valid_name(name):
    n = (name or "").strip()
    if not n or n in (".", "..") or any(c in INVALID for c in n) or len(n) > 240:
        return False
    return not n.rstrip(" .") != n


# ---------------- builders (pure: read-only) ----------------
def _b_trash(p):
    ops, blocked = [], []
    for src in p.get("paths") or []:
        src = os.path.abspath(src)
        ok, why = protected_move(src, "")
        if not ok:
            blocked.append({"src": src, "reason": why})
            continue
        ops.append(_op("trash", src, os.path.join("Recycle Bin", os.path.basename(src))))
    n = len(ops)
    return {"title": f"Move {n} item{'s' * (n != 1)} to the Recycle Bin",
            "verb": "Move to Bin", "destructive": True, "reversible": True,
            "note": "Items stay in Aegis' Recycle Bin until you empty it. Restore any time."}, ops, blocked


def _b_rename(p):
    src = os.path.abspath(p.get("path", ""))
    new = (p.get("new_name") or "").strip()
    if not _valid_name(new):
        return {"title": "Rename", "verb": "Rename"}, [], [
            {"src": src, "reason": "that name has characters files can't use"}]
    ok, why = protected_move(src, "")
    if not ok:
        return {"title": "Rename", "verb": "Rename"}, [], [{"src": src, "reason": why}]
    dst = os.path.join(os.path.dirname(src), new)
    if os.path.exists(dst) and os.path.normcase(dst) != os.path.normcase(src):
        return {"title": "Rename", "verb": "Rename"}, [], [
            {"src": src, "reason": f"“{new}” already exists here"}]
    return {"title": f"Rename “{os.path.basename(src)}”", "verb": "Rename",
            "reversible": True}, [_op("rename", src, dst)], []


def _b_renames(p):
    ops, blocked, seen = [], [], set()
    for it in p.get("items") or []:
        src = os.path.abspath(it.get("path", ""))
        new = (it.get("new_name") or "").strip()
        if not _valid_name(new):
            blocked.append({"src": src, "reason": "invalid name"})
            continue
        ok, why = protected_move(src, "")
        if not ok:
            blocked.append({"src": src, "reason": why})
            continue
        dst = os.path.join(os.path.dirname(src), new)
        if os.path.exists(dst) or dst.lower() in seen:
            dst = _free(dst) if os.path.exists(dst) else dst
        seen.add(dst.lower())
        ops.append(_op("rename", src, dst))
    n = len(ops)
    return {"title": f"Rename {n} file{'s' * (n != 1)}", "verb": "Rename All",
            "reversible": True}, ops, blocked


def _b_move(p):
    dest_dir = os.path.abspath(p.get("dest", ""))
    ops, blocked = [], []
    if not os.path.isdir(dest_dir):
        return {"title": "Move", "verb": "Move"}, [], [{"src": dest_dir, "reason": "destination folder not found"}]
    if is_protected_location(dest_dir) and not os.path.isdir(dest_dir):
        return {"title": "Move", "verb": "Move"}, [], [{"src": dest_dir, "reason": "protected destination"}]
    for src in p.get("paths") or []:
        src = os.path.abspath(src)
        dst = os.path.join(dest_dir, os.path.basename(src))
        if os.path.normcase(os.path.dirname(src)) == os.path.normcase(dest_dir):
            blocked.append({"src": src, "reason": "already in that folder"})
            continue
        if os.path.isdir(src) and (dest_dir + os.sep).lower().startswith(src.lower() + os.sep):
            blocked.append({"src": src, "reason": "can't move a folder into itself"})
            continue
        ok, why = protected_move(src, "")
        if not ok:
            blocked.append({"src": src, "reason": why})
            continue
        ops.append(_op("move", src, _free(dst)))
    n = len(ops)
    return {"title": f"Move {n} item{'s' * (n != 1)} to “{os.path.basename(dest_dir) or dest_dir}”",
            "verb": "Move", "reversible": True}, ops, blocked


def _b_mkdir(p):
    parent = os.path.abspath(p.get("parent", ""))
    name = (p.get("name") or "untitled folder").strip()
    if not os.path.isdir(parent):
        return {"title": "New Folder", "verb": "Create"}, [], [{"src": parent, "reason": "folder not found"}]
    if not _valid_name(name):
        return {"title": "New Folder", "verb": "Create"}, [], [{"src": parent, "reason": "invalid name"}]
    dst = _free(os.path.join(parent, name))
    op = {"op": "mkdir", "src": "", "dst": dst, "name": "", "new_name": os.path.basename(dst),
          "from_dir": "", "to_dir": parent, "is_dir": True, "size": 0}
    return {"title": f"Create folder “{os.path.basename(dst)}”", "verb": "Create",
            "reversible": True}, [op], []


def _b_restore(p):
    ids = p.get("ids") or []
    rows = db.q(f"SELECT * FROM quar WHERE restored=0 AND id IN ({','.join('?' * len(ids))})",
                ids) if ids else db.q("SELECT * FROM quar WHERE restored=0")
    ops, blocked = [], []
    for r in rows:
        if not os.path.exists(r["quar"]):
            blocked.append({"src": r["orig"], "reason": "no longer in the Bin"})
            continue
        o = _op("restore", r["quar"], _free(r["orig"]), qid=r["id"])
        o["name"] = os.path.basename(r["orig"])
        o["from_dir"] = "Recycle Bin"
        ops.append(o)
    n = len(ops)
    return {"title": f"Put back {n} item{'s' * (n != 1)}", "verb": "Put Back",
            "reversible": True, "note": "Each item returns to the folder it came from."}, ops, blocked


def _b_purge(p):
    ids = p.get("ids") or []
    rows = db.q(f"SELECT * FROM quar WHERE restored=0 AND id IN ({','.join('?' * len(ids))})",
                ids) if ids else db.q("SELECT * FROM quar WHERE restored=0")
    ops = []
    for r in rows:
        if os.path.exists(r["quar"]):
            o = _op("purge", r["quar"], "", qid=r["id"])
            o["name"] = os.path.basename(r["orig"])
            o["from_dir"] = os.path.dirname(r["orig"])
            ops.append(o)
    n = len(ops)
    return {"title": (f"Permanently delete {n} item{'s' * (n != 1)}" if ids
                      else "Empty the Recycle Bin"),
            "verb": "Delete Forever", "destructive": True, "reversible": False,
            "note": "This can't be undone. These items will be erased from this computer."}, ops, []


def _b_organize(p):
    from . import organize
    plan = organize.PLANS.get(p.get("batch", ""))
    if not plan:
        return {"title": "Organize", "verb": "Apply"}, [], [{"src": "", "reason": "plan expired — build it again"}]
    sel = set(p.get("selected") or [])
    ops, blocked = [], []
    for m in plan["moves"]:
        if m["id"] not in sel:
            continue
        ok, why = protected_move(m["old"], m["dest"])
        if not ok:
            blocked.append({"src": m["old"], "reason": why})
            continue
        o = _op("move", m["old"], _free(m["dest"]), reason=m.get("reason", ""),
                tier=m.get("tier", ""))
        ops.append(o)
    n = len(ops)
    return {"title": f"Organize {n} file{'s' * (n != 1)} in “{os.path.basename(plan['base'])}”",
            "verb": "Organize", "reversible": True}, ops, blocked


def _b_undo(p):
    b = p.get("batch", "")
    meta = db.q("SELECT * FROM batches WHERE batch=?", (b,), one=True)
    rows = db.q("SELECT * FROM ops WHERE batch=? AND undone=0 ORDER BY id DESC", (b,))
    if not rows or (meta and not meta["reversible"]):
        return {"title": "Undo", "verb": "Undo"}, [], [{"src": "", "reason": "nothing to undo"}]
    ops, blocked = [], []
    for r in rows:
        if r["kind"] == "mkdir":
            o = {"op": "rmdir", "src": r["dst"], "dst": "", "name": os.path.basename(r["dst"]),
                 "new_name": "", "from_dir": os.path.dirname(r["dst"]), "to_dir": "",
                 "is_dir": True, "size": 0, "ref": r["id"]}
        elif not os.path.exists(r["dst"]):
            blocked.append({"src": r["dst"], "reason": "item has moved since"})
            continue
        else:
            o = _op("undo", r["dst"], _free(r["src"]) if os.path.exists(r["src"]) else r["src"],
                    ref=r["id"], undo_of=r["kind"])
            if r["kind"] == "trash":
                o["from_dir"] = "Recycle Bin"
                o["name"] = os.path.basename(r["src"])
            if r["kind"] == "restore":
                o["to_dir"] = "Recycle Bin"
        ops.append(o)
    title = (meta["title"] if meta else "change")
    return {"title": f"Undo “{title}”", "verb": "Undo", "reversible": True}, ops, blocked


BUILDERS = {"trash": _b_trash, "rename": _b_rename, "renames": _b_renames,
            "move": _b_move, "mkdir": _b_mkdir, "restore": _b_restore,
            "purge": _b_purge, "organize": _b_organize, "undo": _b_undo}


def _groups(ops):
    g = {}
    for o in ops:
        key = (o["from_dir"], o["to_dir"])
        e = g.setdefault(key, {"from": o["from_dir"], "to": o["to_dir"], "items": [], "bytes": 0})
        e["items"].append({"name": o["name"], "new_name": o["new_name"], "is_dir": o["is_dir"],
                           "size": o["size"], "op": o["op"]})
        e["bytes"] += o["size"] or 0
    return sorted(g.values(), key=lambda x: -len(x["items"]))


def preview(kind, payload):
    for t in [t for t, v in PENDING.items() if time.time() - v["ts"] > TTL]:
        PENDING.pop(t, None)
    b = BUILDERS.get(kind)
    if not b:
        return {"ok": False, "error": f"unknown change '{kind}'"}
    meta, ops, blocked = b(payload or {})
    token = uuid.uuid4().hex
    new_dirs = sorted({o["to_dir"] for o in ops if o["to_dir"] and o["to_dir"] != "Recycle Bin"
                       and o["op"] in ("move", "undo", "restore") and not os.path.isdir(o["to_dir"])})
    cs = {"ok": True, "token": token, "kind": kind, "ts": time.time(),
          "title": meta.get("title", kind), "verb": meta.get("verb", "Apply"),
          "destructive": meta.get("destructive", False),
          "reversible": meta.get("reversible", True), "note": meta.get("note", ""),
          "ops": ops, "blocked": blocked, "groups": _groups(ops),
          "count": len(ops), "bytes": sum(o["size"] or 0 for o in ops),
          "new_folders": new_dirs}
    if ops:
        PENDING[token] = cs
    return {k: v for k, v in cs.items() if k != "ts"}


def cancel(token):
    PENDING.pop(token, None)
    return {"ok": True}


def _move(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)


def commit(token):
    cs = PENDING.pop(token, None)
    if not cs:
        return {"ok": False, "error": "This change wasn't confirmed or has expired. Review it again."}
    batch = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
    results, touched, gone = [], [], []
    for o in cs["ops"]:
        try:
            k = o["op"]
            if k == "trash":
                ok, why = protected_move(o["src"], "")
                if not ok:
                    raise OSError(why)
                dest = _free(str(config.QUARANTINE / batch / os.path.basename(o["src"])))
                _move(o["src"], dest)
                db.q("INSERT INTO quar(batch, orig, quar, ts) VALUES (?,?,?,?)",
                     (batch, o["src"], dest, time.time()), commit=True)
                _journal(batch, "trash", o["src"], dest)
                gone.append(o["src"])
            elif k in ("rename", "move"):
                ok, why = protected_move(o["src"], o["dst"])
                if not ok:
                    raise OSError(why)
                dest = _free(o["dst"]) if os.path.normcase(o["src"]) != os.path.normcase(o["dst"]) else o["dst"]
                _move(o["src"], dest)
                _journal(batch, k, o["src"], dest)
                gone.append(o["src"])
                touched.append(dest)
            elif k == "mkdir":
                os.makedirs(o["dst"], exist_ok=False)
                _journal(batch, "mkdir", "", o["dst"])
            elif k == "restore":
                dest = _free(o["dst"])
                _move(o["src"], dest)
                db.q("UPDATE quar SET restored=1 WHERE id=?", (o["qid"],), commit=True)
                _journal(batch, "restore", o["src"], dest)
                touched.append(dest)
            elif k == "purge":
                if os.path.isdir(o["src"]) and not os.path.islink(o["src"]):
                    shutil.rmtree(o["src"])
                else:
                    os.unlink(o["src"])
                db.q("UPDATE quar SET restored=2 WHERE id=?", (o["qid"],), commit=True)
                _prune_bin(o["src"])
            elif k == "rmdir":
                os.rmdir(o["src"])
                db.q("UPDATE ops SET undone=1 WHERE id=?", (o["ref"],), commit=True)
            elif k == "undo":
                dest = _free(o["dst"]) if os.path.exists(o["dst"]) else o["dst"]
                _move(o["src"], dest)
                db.q("UPDATE ops SET undone=1 WHERE id=?", (o["ref"],), commit=True)
                if o.get("undo_of") == "trash":
                    db.q("UPDATE quar SET restored=1 WHERE quar=?", (o["src"],), commit=True)
                    _prune_bin(o["src"])
                    touched.append(dest)
                elif o.get("undo_of") == "restore":
                    db.q("UPDATE quar SET restored=0 WHERE quar=?", (dest,), commit=True)
                    gone.append(o["src"])
                else:
                    gone.append(o["src"])
                    touched.append(dest)
                _cleanup_empty(os.path.dirname(o["src"]))
            results.append({"src": o["src"], "dst": o.get("dst", ""), "ok": True})
        except OSError as e:
            results.append({"src": o["src"], "dst": o.get("dst", ""), "ok": False, "error": str(e)})
    n_ok = sum(1 for r in results if r["ok"])
    if cs["kind"] == "undo":
        undone_batch = cs["ops"][0].get("ref") and db.q(
            "SELECT batch FROM ops WHERE id=?", (cs["ops"][0]["ref"],), one=True)
        if undone_batch:
            db.q("UPDATE batches SET undone=1 WHERE batch=?", (undone_batch["batch"],), commit=True)
    if n_ok and cs["kind"] not in ("undo",):
        db.q("""INSERT INTO batches(batch, ts, kind, title, count, bytes, reversible)
                VALUES (?,?,?,?,?,?,?)""",
             (batch, time.time(), cs["kind"], cs["title"], n_ok, cs["bytes"],
              int(cs["reversible"])), commit=True)
    for g in gone:
        indexer.forget(g)
    try:
        if touched:
            indexer.reindex(touched[:200])
        else:
            from . import search
            search.invalidate()
    except Exception:  # noqa: BLE001 - index refresh must never fail a commit
        pass
    return {"ok": True, "batch": batch, "kind": cs["kind"], "title": cs["title"],
            "done": n_ok, "failed": len(results) - n_ok, "results": results,
            "undoable": bool(n_ok) and cs["reversible"] and cs["kind"] != "undo"}


def _journal(batch, kind, src, dst):
    db.q("INSERT INTO ops(batch, ts, kind, src, dst) VALUES (?,?,?,?,?)",
         (batch, time.time(), kind, src, dst), commit=True)


def _prune_bin(path):
    d = os.path.dirname(path)
    try:
        if os.path.dirname(d) == str(config.QUARANTINE) and not os.listdir(d):
            os.rmdir(d)
    except OSError:
        pass


def _cleanup_empty(d):
    for _ in range(3):
        try:
            if is_protected_location(d):
                return
            os.rmdir(d)  # only succeeds if empty
        except OSError:
            return
        d = os.path.dirname(d)


# ---------------- read models ----------------
def bin_items():
    rows = db.q("SELECT * FROM quar WHERE restored=0 ORDER BY ts DESC")
    out = []
    for r in rows:
        if not os.path.exists(r["quar"]):
            continue
        out.append({"id": r["id"], "name": os.path.basename(r["orig"]), "orig": r["orig"],
                    "from": os.path.dirname(r["orig"]), "ts": r["ts"],
                    "is_dir": os.path.isdir(r["quar"]), "size": _size(r["quar"]),
                    "batch": r["batch"]})
    return {"items": out, "count": len(out), "bytes": sum(i["size"] for i in out)}


def history(limit=40):
    rows = db.q("SELECT * FROM batches ORDER BY ts DESC LIMIT ?", (limit,))
    return [dict(r) for r in rows]
