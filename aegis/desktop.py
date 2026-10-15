"""Aegis desktop shell: FastAPI on a background thread + native window.

  python desktop.py               -> native window (needs pywebview)
  python desktop.py --no-window   -> backend only (browser at 127.0.0.1:8000)
  AEGIS_NO_WINDOW=1               -> same as --no-window (for automated tests)
"""
import argparse
import os
import threading
import time
import urllib.request
import webbrowser

import uvicorn

# direct import (not a string) so PyInstaller traces the whole package
from aegis.api import app as api_app


def _wait(port):
    for _ in range(120):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health",
                                   timeout=1)
            return True
        except Exception:
            time.sleep(0.25)
    return False


def serve(port):
    try:
        req = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=0.5)
        if req.status == 200:
            return None
    except Exception:
        pass
    t = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": api_app, "host": "127.0.0.1", "port": port,
                "log_level": "warning"},
        daemon=True)
    t.start()
    return t


def main(port=8000, no_window=False):
    t = serve(port)
    if t is not None and not _wait(port):
        print("backend failed to start")
        return 1
    url = f"http://127.0.0.1:{port}"
    if no_window or os.environ.get("AEGIS_NO_WINDOW") == "1":
        print(f"Aegis backend on {url} (no window)")
        if t is not None:
            t.join()
        return 0
    try:
        import webview
        webview.create_window("Aegis — private file manager", url,
                              width=1320, height=880)
        webview.start()
    except Exception as e:
        print(f"Native window fallback ({e}). Running in browser instead: {url}")
        webbrowser.open(url)
        if t is not None:
            t.join()
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-window", action="store_true")
    args = ap.parse_args()
    raise SystemExit(main(args.port, args.no_window))
