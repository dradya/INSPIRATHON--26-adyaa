"""SQLite store: files + FTS5, dirs rollup, ledger, ops/undo journals, quarantine."""
import json
import sqlite3
import threading
import time

from .config import DB_PATH

_lock = threading.RLock()
_db = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS files(
  id INTEGER PRIMARY KEY, path TEXT UNIQUE, name TEXT, folder TEXT, ext TEXT,
  size INTEGER, mtime REAL, tier TEXT DEFAULT 'Public', snippet TEXT DEFAULT '',
  indexed_at REAL DEFAULT 0, embedder TEXT DEFAULT '', embedding BLOB);
CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(name, folder, snippet,
  content='files', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS files_fts_ai AFTER INSERT ON files BEGIN
  INSERT INTO files_fts(rowid, name, folder, snippet)
  VALUES (new.id, new.name, new.folder, new.snippet); END;
CREATE TRIGGER IF NOT EXISTS files_fts_ad AFTER DELETE ON files BEGIN
  INSERT INTO files_fts(files_fts, rowid, name, folder, snippet)
  VALUES ('delete', old.id, old.name, old.folder, old.snippet); END;
CREATE TRIGGER IF NOT EXISTS files_fts_au AFTER UPDATE ON files BEGIN
  INSERT INTO files_fts(files_fts, rowid, name, folder, snippet)
  VALUES ('delete', old.id, old.name, old.folder, old.snippet);
  INSERT INTO files_fts(rowid, name, folder, snippet)
  VALUES (new.id, new.name, new.folder, new.snippet); END;
CREATE TABLE IF NOT EXISTS dirs(
  path TEXT PRIMARY KEY, parent TEXT, size INTEGER DEFAULT 0, count INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS scans(
  id INTEGER PRIMARY KEY, root TEXT, phase TEXT, started REAL, finished REAL, seen INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS ledger(
  id INTEGER PRIMARY KEY, ts REAL, purpose TEXT, provider TEXT, model TEXT,
  egress INTEGER, original TEXT, sent TEXT, entities TEXT, bytes_sent INTEGER,
  files_sent INTEGER, files_withheld INTEGER, residual INTEGER, ok INTEGER, error TEXT);
CREATE TABLE IF NOT EXISTS ops(
  id INTEGER PRIMARY KEY, batch TEXT, ts REAL, kind TEXT, src TEXT, dst TEXT, undone INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS quar(
  id INTEGER PRIMARY KEY, batch TEXT, orig TEXT, quar TEXT, ts REAL, restored INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT);
"""


def conn():
    global _db
    with _lock:
        if _db is None:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            _db = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            _db.row_factory = sqlite3.Row
            _db.execute("PRAGMA journal_mode=WAL")
            _db.executescript(SCHEMA)
        return _db


def q(sql, args=(), one=False, commit=False):
    with _lock:
        c = conn()
        cur = c.execute(sql, args)
        if commit:
            c.commit()
        rows = cur.fetchall()
    if one:
        return rows[0] if rows else None
    return rows


def log_ledger(purpose, provider, model, egress, original, sent, entities,
               bytes_sent, files_sent, files_withheld, residual, ok, error=""):
    from .config import LEDGER_TEXT_CAP
    q("""INSERT INTO ledger(ts, purpose, provider, model, egress, original, sent,
         entities, bytes_sent, files_sent, files_withheld, residual, ok, error)
         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
      (time.time(), purpose, provider, model, int(bool(egress)),
       (original or "")[:LEDGER_TEXT_CAP], (sent or "")[:LEDGER_TEXT_CAP],
       json.dumps(entities or {}), bytes_sent, files_sent, files_withheld,
       residual, int(bool(ok)), error or ""), commit=True)


def get_kv(k, default=""):
    r = q("SELECT v FROM kv WHERE k=?", (k,), one=True)
    return r["v"] if r else default


def set_kv(k, v):
    q("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
      (k, v), commit=True)
