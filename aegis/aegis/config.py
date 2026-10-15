"""Aegis global settings. API keys live in RAM only — never written to disk."""
from pathlib import Path

SETTINGS = {
    "provider": "local-rules",   # local-rules | anthropic | openai | ollama
    "api_key": "",               # MEMORY ONLY. /api/settings never returns it.
    "model": "",
    "base_url": "",              # OpenAI-compatible endpoint base
    "ollama_url": "http://127.0.0.1:11434",
    "ollama_model": "llama3.1",
    "offline": False,            # True -> Ollama if up, else local-rules. Zero egress.
}

AEGIS_HOME = Path.home() / ".aegis"
DB_PATH = AEGIS_HOME / "aegis.db"
QUARANTINE = AEGIS_HOME / "quarantine"

BLOCK_OPEN_EXTS = {".exe", ".bat", ".cmd", ".ps1", ".msi", ".scr", ".vbs", ".lnk"}

JUNK_NAMES = {"node_modules", "__pycache__", ".cache", "temp", "tmp",
              "thumbs.db", "desktop.ini", "$recycle.bin", ".git", ".venv", "venv"}

TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".js", ".jsx", ".ts", ".py",
             ".java", ".c", ".cpp", ".html", ".css", ".xml", ".yml", ".yaml",
             ".log", ".ini", ".toml", ".rs", ".go", ".ipynb", ".tex", ".sql",
             ".kt", ".cs", ".rb", ".php", ".sh", ".h", ".hpp", ".rst"}

MAX_SNIPPET_FILE = 5 * 1024 * 1024     # don't read content past this
SNIPPET_LEN = 240                      # redacted snippet length for cloud
LEDGER_TEXT_CAP = 6000                 # cap stored original/sent per row
ORGANIZE_CAP = 250                     # max files per organize plan
