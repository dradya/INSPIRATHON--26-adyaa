"""Aegis entry point: uvicorn on 127.0.0.1 only. Usage: python app.py [--port 8000]"""
import argparse
import sys
import webbrowser

import uvicorn

from aegis import db  # noqa: F401 - init schema on boot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    url = f"http://127.0.0.1:{args.port}"
    print(f"Aegis on {url}  (loopback only)")
    if not args.no_browser:
        webbrowser.open(url)
    uvicorn.run("aegis.api:app", host="127.0.0.1", port=args.port,
                log_level="warning")


if __name__ == "__main__":
    sys.exit(main())
