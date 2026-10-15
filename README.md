# 🛡️ VaultLens & Aegis — AI File System Intelligence (PS3)

> **INSPIRATHON '26 — Problem Statement 3: File System Intelligence**  
> An on-device first, privacy-preserving file intelligence system that resolves storage chaos, detects sensitive data, and provides automated organization without compromising private user data.

---

## 🌟 The Core Innovation: Hybrid Privacy Architecture

Modern operating systems have rigid file search and obscure granular control, while traditional cloud AI services pose unacceptable privacy hazards by uploading raw personal files, financial statements, and sensitive documents.

**VaultLens** & **Aegis** solve this with a **Zero-Egress / On-Device First Privacy Pipeline**:

```
[ Local Files / Storage ] 
        │
        ▼ (Local WebCrypto & Regex Parsing)
[ On-Device Scanner & 12 PII Recognizers ]
        │  • Aadhaar, PAN, Passports, SSNs, UPI, Cards, API Keys, Passwords
        ▼
[ Local Tokenization & SHA-256 Hashing ]
        │  • Names redacted to [REDACTED:TYPE]
        │  • Duplicate detection via identical-size group hashing
        ▼
[ Sanitized Metadata / Cloud AI Gateway ] ◄── Sensitive data NEVER leaves the machine!
        │  • Only scrubbed tokens and structural aggregates
        ▼
[ Actionable Insights & Instant Organization ]
        │  • Safe 2-step cleanup, batch reorganization, semantic search
```

---

## 🚀 Two Powerful Implementations

This repository includes two production-grade implementations designed for different environments:

### 1. 🌐 **VaultLens (Modern Web Application)**
- **Tech Stack:** React 18, Vite, Tailwind CSS, Framer Motion, Recharts, Lucide Icons, Supabase Edge Functions.
- **Key Features:**
  - **Browser File System Access API:** Directly inspect and analyze real local folders on Chrome/Edge with native system handles.
  - **Realistic Messy Demo Vault:** Seeded PRNG creating a representative student/developer laptop filesystem for zero-setup live demos.
  - **Semantic & Intent Search:** Fuzzy keyword mapping, purpose expansion (e.g., `resume` finds `cv`, `curriculum`, `vitae`), and date/size qualifiers.
  - **Tree & Table Explorer:** Dual list/folder tree view displaying real-time redaction tags, PII warnings, and byte weights.
  - **Interactive 2-Step Cleanup:** Safe duplicate and stale file removal with calculated byte reclamation and safety confirmation.
  - **Conversational Vault Agent:** Heuristic offline reasoning + optional LLM integration with contextual quick-action buttons and storage optimization advice.
  - **Dynamic Privacy Controls:** 12 live detector toggles with instant client-side re-redaction and cloud payload transparency preview.

### 2. 🖥️ **Aegis (Standalone Native Desktop Application)**
- **Tech Stack:** Python 3, FastAPI, SQLite with FTS5, PyWebView, PyInstaller (`dist/Aegis/Aegis.exe`).
- **Key Features:**
  - **Compiled Windows Executable:** Runs completely self-contained without needing Python or external runtimes.
  - **15 Local Recognizers & Reversible Token Vault:** Strict egress guard with local fallback rules, Ollama, Anthropic, or OpenAI-compatible backends.
  - **Privacy Ledger:** Side-by-side original vs. outbound inspection proving zero raw bytes sent.
  - **Quarantine & Safe Undo:** Dry-run reorganization plans with atomic rollbacks.

---

## ⚡ Quick Start Guide

### Running VaultLens (Web App)

```bash
# 1. Install dependencies
npm install

# 2. Start the development server
npm run dev
# → Open http://localhost:5173
```

- **Production build check:**
  ```bash
  npm run build
  ```

### Running Aegis (Desktop App / Tests)

```bash
# Run unit test suite (30 passing tests)
python aegis/tests/run_tests.py

# Launch desktop app (if Python installed)
cd aegis
pip install -r requirements.txt
python desktop.py

# Or launch the pre-compiled binary:
# Run: aegis/dist/Aegis/Aegis.exe
```

---

## 🏆 3-Minute Judge Walkthrough

1. **Dashboard & Demo Vault:**
   - Click **"Try the demo vault"** on the landing page.
   - Observe the circular **Health Score**, total used space, recoverable duplicates, and detected PII metrics.
2. **Semantic Search & Tree View (Explorer):**
   - Navigate to **Explorer** (`/explorer`).
   - Switch between **List view** and **Tree view** (`📁 Root`).
   - Type `resume`, `movie`, or `sensitive` into the search box to see **semantic intent matching** highlight relevant files.
3. **Interactive Cleanup (Cleanup Queue):**
   - Open **Cleanup** (`/cleanup`).
   - Review duplicate clusters, select redundant items, and click **Queue cleanup** → **Confirm delete**. Watch space update in real time.
4. **Actionable Insights:**
   - Open **Insights** (`/insights`).
   - Click **Accept** on any insight (e.g. Duplicates or Stale files) to automatically jump to the relevant remediation tool.
5. **Privacy Proof (Privacy Pipeline):**
   - Open **Privacy** (`/privacy`).
   - Toggle individual detectors (Aadhaar, PAN, SSN, API Keys) and inspect the live **Redaction Log** and **Cloud Payload Preview** proving no raw data leaves.
6. **VaultLens AI Agent:**
   - Open **Agent** (`/agent`) or click the floating widget.
   - Ask: *"What can I delete?"*, *"Show duplicates"*, or *"Optimize my storage"*. Click the contextual response buttons for instant navigation.

---

## 📁 Repository Structure

```
INSPIRATHON '26/
├── src/
│   ├── components/         # Navbar, CommandPalette (⌘K), AgentWidget, Toasts, UI primitives
│   ├── context/            # FSContext (on-device engine & storage), AuthContext
│   ├── lib/
│   │   ├── files/          # scanner.js, pii.js, insights.js, demoData.js
│   │   ├── agent.js        # AI agent heuristics & semantic query engine
│   │   └── supabase.js     # Supabase client integration
│   ├── pages/              # Dashboard, Explorer, Cleanup, Insights, Privacy, Agent
│   ├── App.jsx             # Shell & animated route transitions
│   └── main.jsx
├── aegis/                  # Native desktop engine (FastAPI, SQLite FTS5, PyWebView)
│   ├── aegis/              # privacy.py, db.py, indexer.py, search.py, storage.py
│   ├── dist/Aegis/         # Standalone compiled executable (Aegis.exe)
│   └── tests/              # 30 automated test suites
├── supabase/               # Backend schema, RLS policies, and edge functions
└── index.html
```

---

*Built with ❤️ for INSPIRATHON '26 · Private, local-first, intelligent.*
