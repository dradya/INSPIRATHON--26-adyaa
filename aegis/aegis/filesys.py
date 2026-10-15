"""Read-only explorer ops, drive roots, Power Mode, open/reveal,
and protected_move() — the single choke point for every move/organize/quarantine."""
import ctypes
import os
import stat
import subprocess
import sys
from pathlib import Path

from . import config, db

SYSTEM_WIN = [Path("C:/Windows"), Path("C:/Program Files"),
              Path("C:/Program Files (x86)"), Path("C:/ProgramData")]
SYSTEM_UNIX = [Path("/usr"), Path("/etc"), Path("/bin"), Path("/sbin"),
               Path("/System"), Path("/Library"), Path("/proc"), Path("/sys")]


def _resolve(p):
    try:
        return Path(p).resolve()
    except OSError:
        return None


def is_protected_location(p):
    """True for drive roots, system dirs, home itself, home's direct
    children (Documents/Downloads/...), and direct children of the
    users container (C:\\Users\\Bob, /home/alice)."""
    r = _resolve(p)
    if r is None:
        return True
    if r.parent == r:  # drive root / filesystem root
        return True
    home = Path.home().resolve()
    if r == home:
        return True
    try:
        rel = r.relative_to(home)
        if len(rel.parts) == 1:  # direct child of home
            return True
    except ValueError:
        pass
    container = home.parent  # C:\\Users, /home, /Users
    try:
        rel = r.relative_to(container)
        if len(rel.parts) == 1:  # direct child of users container
            return True
    except ValueError:
        pass
    syss = SYSTEM_WIN if sys.platform == "win32" else SYSTEM_UNIX
    for s in syss:
        try:
            if r == s.resolve() or s.resolve() in r.parents:
                return True
        except OSError:
            continue
    return False


def protected_move(src, dst):
    """Gate every relocation. dst may be '' for src-side pre-checks."""
    rs = _resolve(src)
    if rs is None or not rs.exists():
        return False, "source missing"
    if is_protected_location(rs):
        return False, "source is a protected location"
    if dst:
        rd = _resolve(dst)
        if rd is None:
            return False, "bad destination"
        if is_protected_location(rd):
            return False, "destination is a protected location"
    return True, ""


def drives():
    if sys.platform == "win32":
        return [f"{c}:\\" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                if os.path.exists(f"{c}:\\")]
    return ["/"]


def _hidden(p):
    name = os.path.basename(p)
    if sys.platform == "win32":
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(p))
            if attrs != -1 and (attrs & 0x2 or attrs & 0x4):
                return True
        except Exception:
            pass
    return name.startswith(".")


def _tier_for(path, name):
    row = db.q("SELECT tier FROM files WHERE path=?", (path,), one=True)
    if row:
        return row["tier"]
    from . import privacy
    return privacy.tier_of(name, os.path.dirname(path), [], "")


def tree(path):
    """Lazy children: dirs only, with has_children flags."""
    out = []
    try:
        with os.scandir(path) as it:
            for e in it:
                try:
                    if e.is_symlink() or not e.is_dir(follow_symlinks=False):
                        continue
                    try:
                        has = any(x.is_dir(follow_symlinks=False)
                                  for x in os.scandir(e.path))
                    except OSError:
                        has = False
                    out.append({"path": e.path, "name": e.name,
                                "has_children": has, "hidden": _hidden(e.path)})
                except OSError:
                    continue
    except (PermissionError, OSError, FileNotFoundError):
        pass
    out.sort(key=lambda x: x["name"].lower())
    return out


def ls(path, power=False):
    """Read-only listing. power=True also shows hidden/system entries."""
    items = []
    try:
        with os.scandir(path) as it:
            for e in it:
                try:
                    if e.is_symlink():
                        continue
                    hidden = _hidden(e.path)
                    if hidden and not power:
                        continue
                    st = e.stat(follow_symlinks=False)
                    is_dir = e.is_dir(follow_symlinks=False)
                    size = 0
                    if is_dir:
                        r = db.q("SELECT size FROM dirs WHERE path=?",
                                 (e.path,), one=True)
                        size = r["size"] if r else 0
                    else:
                        size = st.st_size
                    items.append({
                        "path": e.path, "name": e.name, "is_dir": is_dir,
                        "size": size, "mtime": st.st_mtime,
                        "perms": stat.filemode(st.st_mode), "hidden": hidden,
                        "tier": _tier_for(e.path, e.name) if not is_dir else "Public",
                    })
                except OSError:
                    continue
    except (PermissionError, OSError, FileNotFoundError) as ex:
        return {"error": str(ex), "items": []}
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return {"items": items}


def open_path(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in config.BLOCK_OPEN_EXTS:
        return {"ok": False, "error": f"blocked executable type {ext}"}
    if not os.path.exists(path):
        return {"ok": False, "error": "missing"}
    try:
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606 - local desktop action
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return {"ok": True}
    except OSError as e:
        return {"ok": False, "error": str(e)}


def reveal(path):
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", os.path.abspath(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(os.path.abspath(path))])
        return {"ok": True}
    except OSError as e:
        return {"ok": False, "error": str(e)}
