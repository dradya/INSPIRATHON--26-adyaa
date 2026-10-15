"""Aegis Web Application entry point: uvicorn on 127.0.0.1.
Usage: python app.py [--port 8000] [--no-browser]
"""
import argparse
import sys
import urllib.request
import webbrowser

import uvicorn

from aegis import db  # noqa: F401 - init schema on boot


def main():
    ap = argparse.ArgumentParser(description="Aegis Web Application")
    ap.add_argument("--port", type=int, default=8000, help="Port to run web app on")
    ap.add_argument("--no-browser", action="store_true", help="Don't automatically open browser")
    args = ap.parse_args()

    url = f"http://127.0.0.1:{args.port}"
    print("=" * 60)
    print("🛡️   AEGIS — Private AI File Manager (Web Application)")
    print(f"🌐  Running at: {url}")
    print("🔒  100% On-Device · Zero Cloud Egress · Apple-Grade UI")
    print("=" * 60)

    # Check if already running on this port
    try:
        req = urllib.request.urlopen(f"{url}/api/health", timeout=0.6)
        if req.status == 200:
            print(f"\n[+] Aegis Web App is already active on {url}!")
            if not args.no_browser:
                print("[+] Opening Aegis Web App in your browser...")
                webbrowser.open(url)
            return 0
    except Exception:
        pass

    if not args.no_browser:
        # Delay opening by 200ms in background thread so server has bound
        import threading, time
        def _open():
            time.sleep(0.4)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run("aegis.api:app", host="127.0.0.1", port=args.port,
                log_level="warning")


if __name__ == "__main__":
    sys.exit(main())

