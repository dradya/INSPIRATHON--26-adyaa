"""Search by meaning. 100% local.

Pipeline:  understand query -> stemmed FTS5 (strict AND + concept-expanded OR)
           + concept-aware vector cosine -> fused rank -> coverage / kind /
           time boosts -> explanation + best passage per hit. Folders too.
"""
import os
import re
import threading
import time

import numpy as np

from . import db
from . import privacy, semantic
from .indexer import embed, embedder_name

RRF_K = 60
_MAT = {"ids": None, "m": None, "key": None}
_mat_lock = threading.Lock()


def invalidate():
    with _mat_lock:
        _MAT.update(ids=None, m=None, key=None)


def parse_time(query):
    """Back-compat helper: (query without time phrase, (start, end) | None)."""
    q, span, _ = semantic.parse_time(query or "")
    return re.sub(r"\s+", " ", q).strip(), span


def _matrix():
    name = embedder_name()
    with _mat_lock:
        if _MAT["m"] is not None and _MAT["key"] == name:
            return _MAT["ids"], _MAT["m"]
    rows = db.q("SELECT id, embedding FROM files WHERE embedding IS NOT NULL AND embedder=?",
                (name,))
    ids, vecs = [], []
    dim = None
    for r in rows:
        v = np.frombuffer(r["embedding"], dtype=np.float32)
        if dim is None:
            dim = v.shape[0]
        if v.shape[0] == dim:
            ids.append(r["id"])
            vecs.append(v)
    m = np.vstack(vecs) if vecs else np.zeros((0, 1), np.float32)
    ids = np.asarray(ids, dtype=np.int64)
    with _mat_lock:
        _MAT.update(ids=ids, m=m, key=name)
    return ids, m


def sem_search(vec, limit=150):
    ids, m = _matrix()
    if not len(ids) or m.shape[1] != vec.shape[0]:
        return []
    sims = m @ (vec / (np.linalg.norm(vec) or 1))
    k = min(limit, len(sims))
    top = np.argpartition(-sims, k - 1)[:k]
    top = top[np.argsort(-sims[top])]
    return [(int(ids[i]), float(sims[i])) for i in top]


def _q(term):
    t = re.sub(r"[^\w+#]", "", term)
    return f'"{t}"' if t else ""


def fts_search(match, limit=150):
    if not match:
        return []
    try:
        return db.q("""SELECT rowid AS id, bm25(files_fts, 8.0, 2.0, 1.0) AS s
                       FROM files_fts WHERE files_fts MATCH ? ORDER BY s LIMIT ?""",
                    (match, limit))
    except Exception:
        return []


def _clause(t):
    q = _q(t)
    if not q:
        return ""
    return f"({q} OR {q}*)" if len(t) >= 3 else q


def _folders(intent, limit=6):
    terms = [t for t in intent["core"] if len(t) > 2][:5]
    if not terms:
        return []
    like = " OR ".join(["LOWER(path) LIKE ?"] * len(terms))
    rows = db.q(f"SELECT path, size, count FROM dirs WHERE {like} LIMIT 400",
                [f"%{t.lower()}%" for t in terms])
    out = []
    for r in rows:
        base = os.path.basename(r["path"] or "").lower()
        hits = [t for t in terms if t.lower() in base]
        if not hits:
            continue
        score = len(hits) / len(terms) + (0.3 if base in terms else 0)
        out.append({"path": r["path"], "name": os.path.basename(r["path"]),
                    "size": r["size"], "count": r["count"], "score": score,
                    "matched": hits})
    out.sort(key=lambda x: (-x["score"], -(x["count"] or 0)))
    return out[:limit]


def _present(stem_list, hay_tokens):
    hs = {semantic.stem(t) for t in hay_tokens}
    return [s for s in stem_list if s in hs or any(h.startswith(s) for h in hs if len(s) >= 4)]


def _kind_only(intent, limit):
    exts = sorted(intent["exts"])
    where, args = [], []
    if exts:
        where.append(f"ext IN ({','.join('?' * len(exts))})")
        args += exts
    if intent["span"]:
        where.append("mtime BETWEEN ? AND ?")
        args += list(intent["span"])
    if not where:
        return []
    return [r["id"] for r in db.q(
        f"SELECT id FROM files WHERE {' AND '.join(where)} ORDER BY mtime DESC LIMIT ?",
        args + [limit])]


def search(query, limit=30):
    t0 = time.time()
    intent = semantic.understand(query or "")
    span = intent["span"]
    core, stems = intent["core"], intent["stems"]
    related = semantic.expansions(intent)
    folders = _folders(intent)

    strict = " AND ".join(c for c in (_clause(t) for t in core) if c)
    loose = " OR ".join(c for c in (_clause(t) for t in core + related) if c)
    fts_strict = fts_search(strict) if len(core) > 1 else []
    fts_loose = fts_search(loose)
    sem = sem_search(semantic.embed_query(intent) if embedder_name() != "minilm"
                     else embed([intent["text"] or intent["raw"]])[0]) if (core or intent["concepts"]) else []

    r_strict = {r["id"]: i for i, r in enumerate(fts_strict)}
    r_loose = {r["id"]: i for i, r in enumerate(fts_loose)}
    sem_sim = dict(sem)
    r_sem = {fid: i for i, (fid, _s) in enumerate(sem)}

    fused = {}
    for fid, r in r_strict.items():
        fused[fid] = fused.get(fid, 0) + 1.7 / (RRF_K + r)
    for fid, r in r_loose.items():
        fused[fid] = fused.get(fid, 0) + 1.0 / (RRF_K + r)
    for fid, r in r_sem.items():
        if sem_sim[fid] > 0.08:
            fused[fid] = fused.get(fid, 0) + 1.2 / (RRF_K + r)
    if not core:
        for i, fid in enumerate(_kind_only(intent, limit * 3)):
            fused[fid] = fused.get(fid, 0) + 1.0 / (RRF_K + i)

    base = {"results": [], "folders": folders, "time_boost": bool(span),
            "intent": _public_intent(intent, related), "ms": 0}
    if not fused:
        base["ms"] = int((time.time() - t0) * 1000)
        return base

    ids = sorted(fused, key=lambda i: -fused[i])[:max(limit * 4, 80)]
    rows = {r["id"]: r for r in db.q(
        f"SELECT * FROM files WHERE id IN ({','.join('?' * len(ids))})", ids)}
    rel_stems = [semantic.stem(w) for w in related]
    out = []
    for fid in ids:
        r = rows.get(fid)
        if not r:
            continue
        name_toks = semantic.tokens(semantic.split_name(r["name"]))
        body_toks = semantic.tokens((r["snippet"] or "")[:8000])
        in_name = _present(stems, name_toks)
        in_body = _present(stems, body_toks)
        got = set(in_name) | set(in_body)
        rel_hit = [w for w, s in zip(related, rel_stems)
                   if s in {semantic.stem(t) for t in body_toks + name_toks}][:5]
        coverage = len(got) / len(stems) if stems else 0.5
        score = fused[fid] * (0.55 + 0.9 * coverage) * (1.15 if in_name else 1.0)
        if rel_hit and not got:
            score *= 1.0 + min(0.4, 0.08 * len(rel_hit))
        ext = (r["ext"] or "").lower()
        kind_hit = bool(intent["exts"]) and ext in intent["exts"]
        if kind_hit:
            score *= 1.35
        time_hit = bool(span) and span[0] <= (r["mtime"] or 0) <= span[1]
        if time_hit:
            score *= 1.5  # boost, don't filter
        why = []
        if in_name:
            why.append("name has " + ", ".join(_orig(core, stems, in_name)))
        body_only = [s for s in in_body if s not in in_name]
        if body_only:
            why.append("mentions " + ", ".join(_orig(core, stems, body_only)))
        if rel_hit:
            why.append("about " + ", ".join(rel_hit[:3]))
        if not why and fid in r_sem:
            why.append("similar topic")
        if kind_hit:
            why.append(f"is {ext.lstrip('.')}")
        if time_hit:
            why.append(f"from {intent['time_label']}")
        in_fts, in_sem = fid in r_loose or fid in r_strict, fid in r_sem
        reason = "keyword + meaning" if in_fts and in_sem else (
            "keyword" if in_fts else "meaning")
        terms = _orig(core, stems, list(got)) + rel_hit
        passage = semantic.best_passage(r["snippet"] or "", terms)
        red, _, _ = privacy.redact((r["snippet"] or "")[:240])
        out.append({
            "id": r["id"], "path": r["path"], "name": r["name"],
            "folder": r["folder"], "ext": r["ext"], "size": r["size"],
            "mtime": r["mtime"], "tier": r["tier"] or "Public",
            "snippet": (r["snippet"] or "")[:500], "passage": passage,
            "cloud_view": red, "withheld": (r["tier"] == "Sensitive"),
            "score": score, "reason": reason, "why": why, "terms": terms,
            "similarity": round(sem_sim.get(fid, 0.0), 3),
        })
    out.sort(key=lambda x: -x["score"])
    out = out[:limit]
    top = out[0]["score"] if out else 1
    for x in out:
        rel = x["score"] / top
        x["match"] = "Best match" if rel > 0.8 else ("Strong" if rel > 0.45 else "Related")
        x["score"] = round(x["score"] * 1000, 2)
    base["results"] = out
    base["ms"] = int((time.time() - t0) * 1000)
    return base


def _orig(core, stems, picked):
    m = dict(zip(stems, core))
    return [m.get(s, s) for s in picked]


def _public_intent(intent, related):
    return {"topic": intent["core"], "kinds": intent["kinds"],
            "folder": intent["folder"], "time": intent["time_label"],
            "concepts": intent["concepts"][:3], "related": related[:8]}
