# Aegis — privacy-first AI file manager (PS3)

Local web app: **Python backend on 127.0.0.1 + single `frontend/index.html`**, no build step.
Works on your **real** files. No dummy data anywhere.

```
aegis/
  app.py                 # python app.py [--port 8000]  (browser mode)
  desktop.py             # python desktop.py            (native window)
  requirements.txt       # fastapi, uvicorn, numpy, pywebview
  requirements-optional.txt  # MiniLM, pypdf, spacy (all feature-detected)
  aegis/
    privacy.py           # detectors, Vault, tiers, egress guard, gateway() — the ONLY outbound caller
    db.py                # SQLite + FTS5, ledger, journals
    indexer.py           # 3-phase background scan (metadata → content → embeddings)
    search.py            # FTS5 BM25 + cosine, RRF fusion, time-phrase boost
    storage.py           # treemap, largest/stale/junk, duplicates, quarantine, insights
    organize.py          # dry-run planner (LLM + local fallback), apply, undo
    filesys.py           # read-only explorer, drives/UNC, Power Mode, protected_move()
    api.py               # FastAPI + Host/Origin rebinding guard
    config.py            # settings (API key in RAM only, never on disk)
  frontend/index.html    # 5 tabs: Search | Explorer | Storage | Organize | Privacy Ledger
  tests/run_tests.py     # 30 unit tests (stdlib only) — pitfalls as regression tests
  tests/smoke.py         # 20 acceptance tests on real temp files
```

## Run it

```bash
cd aegis
pip install -r requirements.txt
python app.py                 # → http://127.0.0.1:8000
python tests/run_tests.py    # unit tests, no server needed
python tests/smoke.py        # needs server on :8001 (python app.py --port 8001 --no-browser)
```

First scan: type a path (or leave blank = home dir) in the top bar → Scan.
Providers: Settings → `local-rules` (default, zero egress), Anthropic, OpenAI-compatible,
or Ollama. Offline toggle forces local-only. Keys stay in server RAM; the API never returns them.

## The privacy story (say this on stage)

1. **Detect locally** — 15 recognizers (Aadhaar, PAN, IFSC, UPI, phone, email, Luhn-checked
   cards, label-based account no/person/DOB, IPv4, secrets, private keys, username-in-path,
   + spaCy PERSON if installed).
2. **Tokenize** — Vault maps each value to `[TYPE_N]` in RAM only. Same value, same token.
3. **Reason** — the cloud sees only `f1 | redacted name | ext | size | date` + a 240-char
   redacted snippet. Never paths. Sensitive files are **withheld entirely** and filed by
   local rules into `Private_Vault/{Identity,Finance,Medical,Credentials}`.
4. **Guard** — a second, stricter pass masks leftover digit runs, `@`-strings, long tokens
   and user paths (never touching `[TOKENS]`). Leftovers are counted as *residual masked*.
5. **Rehydrate** — the LLM's JSON is parsed **first**, then tokens are swapped back per field.

Every `gateway()` call — cloud, Ollama, or local — lands in the **Privacy Ledger** with
side-by-side Original-vs-Sent and the dark-red token chips.

## 🚀 1-Click GUI Installer & Setup Wizard (Zero Commands Needed)

Aegis includes a graphical Setup Wizard with Apple/macOS aesthetics:
- **`AegisSetup.exe`**: Standalone executable setup wizard.
- **`Install-Aegis.bat`**: 1-click batch launcher in both root and `aegis/` folders.
- **`installer.py`**: Python GUI wizard (Tkinter + high-DPI support).

### What the Setup Wizard does:
1. Automatically discovers host Python and windowless `pythonw.exe` interpreters.
2. Deploys application modules, frontend assets, and multi-resolution icons into `%LOCALAPPDATA%\Programs\Aegis`.
3. Verifies & installs required dependencies (`fastapi`, `uvicorn`, `pywebview`, `numpy`, `pypdf`).
4. Creates a 1-click **Desktop shortcut** (`Aegis.lnk`) with the custom Aegis shield icon (`aegis.ico`).
5. Adds Aegis to the **Windows Start Menu**.
6. Generates zero-console silent background launchers (`AegisLauncher.vbs` & `run_aegis.bat`).
7. Users can launch Aegis with a simple double-click on their Desktop — **zero terminal interaction required!**

```bash
# To run the GUI Setup Wizard manually from terminal:
python aegis/installer.py

# Or double-click AegisSetup.exe / Install-Aegis.bat in Windows Explorer!
```

Notes:
- Fully offline: fonts self-hosted, zero external requests (only 127.0.0.1).
  Default provider is `local-rules`, so nothing ever leaves the machine.
- Needs Microsoft Edge WebView2 (preinstalled on Win10/11). Without it, run
  `python desktop.py` (falls back to browser) or `python app.py`.
- DB lives at `~/.aegis/aegis.db` — your index survives reinstalls.
- Avoid `--onefile`: slower startup + common AV false-positives on demo day.

Options compared:

| Path | Effort | Verdict |
|---|---|---|
| **pywebview + PyInstaller one-folder** | 10 min | ✅ do this — same code, native window, no rewrite |
| PyInstaller `--onefile` | 10 min | slower startup, AV false-positives common — avoid for demo day |
| Tauri | hours + Rust toolchain | nicer binary, but a rewrite of the shell for ~zero judging gain |
| Electron | heavy, ships Chromium | pointless — pywebview already uses Edge/WebKit |
| Browser shortcut to 127.0.0.1 | 1 min | fine fallback: `app.py` + a `.url`/desktop shortcut |

Extra credit if time permits: `pystray` tray icon with Show/Quit, autostart shortcut,
and pinning the port (already default 8000). Do **not** add these before H22 freeze.

## Judge demo (3 min)

1. Scan `~/Downloads` live (progress bar moves — architecture points).
2. Search tab: `rent agreement last semester` → real file, tier badge, match reason.
3. Organize tab → Build plan → show **dry-run + withheld Sensitive list**.
4. **Privacy Ledger**: stat strip (0 bytes if local-rules), Original-vs-Sent chips,
   redaction tester with your own PAN pasted live.
5. Flip **Offline** → repeat → Ledger proves 0 bytes sent (feasibility + honesty).
6. Storage → reclaim headline → quarantine one duplicate → undo it.

## Acceptance coverage

| # | Test | Where |
|---|---|---|
| 1 | home scan + time-phrase search | `smoke.py` (fixture), Search tab |
| 2 | organize Downloads, ledger shows tokens only + withheld | `smoke.py`, Organize + Ledger |
| 3 | apply → undo restores | `smoke.py` |
| 4 | dups → quarantine → undo | `smoke.py`, Storage tab |
| 5 | explorer C:\, Power Mode, UNC box | Explorer tab (manual) |
| 6 | offline → 0 bytes | `smoke.py` |
| 7 | `Host: evil.com` → 403 | `smoke.py` |

Known honest limits (say them before judges ask): real-folder scan needs
Chromium-only APIs — irrelevant here, the backend does the scanning; MiniLM/pypdf/spaCy
absent → graceful fallbacks kick in (see `/api/health` embedder field); embeddings for a
full home dir take minutes — phase 1 metadata is usable immediately.
