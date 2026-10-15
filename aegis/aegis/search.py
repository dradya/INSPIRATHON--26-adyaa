"""Hybrid search: SQLite FTS5 (BM25) + embedding cosine, fused with RRF.
Time phrases boost matching mtime ranges (never hard-filter). 100% local."""
import re
import time

import numpy as np

from . import db
from . import privacy
from .indexer import embed

TIME_PHRASES = [
    (r"last\s+week|past\s+week", 7),
    (r"last\s+month|past\s+month", 30),
    (r"last\s+semester|past\s+semester|past\s+6\s+months|last\s+sem", 180),
    (r"last\s+year|past\s+year", 365),
]

RRF_K = 60


def parse_time(query):
    q = query
    span = None
    for pat, days in TIME_PHRASES:
        if re.search(pat, q, re.I):
            now = time.time()
            span = (now - days * 86400, now)
            q = re.sub(pat, " ", q, flags=re.I)
    return re.sub(r"\s+", " ", q).strip(), span


def _fts_terms(q):
    terms = [re.sub(r"[\"*:()^]", "", t) for t in re.findall(r"\w+", q.lower())]
    return [t for t in terms if len(t) > 1][:12]


def fts_search(match, limit=100):
    if not match:
        return []
    try:
        return db.q("""SELECT rowid AS id, bm25(files_fts) AS s FROM files_fts
                       WHERE files_fts MATCH ? ORDER BY s LIMIT ?""",
                    (match, limit))
    except Exception:
        return []


def sem_search(vec, limit=100):
    rows = db.q("SELECT id, embedding FROM files WHERE embedding IS NOT NULL")
    if not rows:
        return []
    scored = []
    qn = vec / (np.linalg.norm(vec) or 1)
    for r in rows:
        try:
            v = np.frombuffer(r["embedding"], dtype=np.float32)
            if v.shape != qn.shape:
                continue
            scored.append((r["id"], float(qn @ v)))
        except Exception:
            continue
    scored.sort(key=lambda x: -x[1])
    return scored[:limit]


def search(query, limit=30):
    stripped, span = parse_time(query or "")
    terms = _fts_terms(stripped)
    match = " OR ".join(f'"{t}"*' for t in terms)
    fts = fts_search(match)
    vec = embed([stripped or query])[0]
    sem = sem_search(vec)
    fts_rank = {r["id"]: i for i, r in enumerate(fts)}
    sem_rank = {fid: i for i, (fid, _s) in enumerate(sem)}
    fused = {}
    for fid, r in list(fts_rank.items()) + list(sem_rank.items()):
        fused[fid] = fused.get(fid, 0) + 1.0 / (RRF_K + r)
    if not fused:
        return {"results": [], "time_boost": bool(span)}
    ids = sorted(fused, key=lambda i: -fused[i])[:limit * 2]
    placeholders = ",".join("?" * len(ids))
    rows = {r["id"]: r for r in db.q(
        f"SELECT * FROM files WHERE id IN ({placeholders})", ids)}
    out = []
    for fid in ids:
        r = rows.get(fid)
        if not r:
            continue
        score = fused[fid]
        if span and span[0] <= (r["mtime"] or 0) <= span[1]:
            score *= 1.5  # boost, don't filter
        in_fts, in_sem = fid in fts_rank, fid in sem_rank
        reason = "keyword + meaning" if in_fts and in_sem else (
            "keyword" if in_fts else "meaning")
        red, _, _ = privacy.redact((r["snippet"] or "")[:240])
        out.append({
            "id": r["id"], "path": r["path"], "name": r["name"],
            "folder": r["folder"], "ext": r["ext"], "size": r["size"],
            "mtime": r["mtime"], "tier": r["tier"] or "Public",
            "snippet": (r["snippet"] or "")[:500],
            "cloud_view": red, "withheld": (r["tier"] == "Sensitive"),
            "score": round(score, 4), "reason": reason,
        })
    out.sort(key=lambda x: -x["score"])
    return {"results": out[:limit], "time_boost": bool(span)}
