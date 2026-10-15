"""Privacy engine: detect -> tokenize (Vault, RAM only) -> gateway -> rehydrate.

RULE: gateway() is the ONLY function in this codebase allowed to make an
outbound network call. Everything else is local. Verified by: grep urlopen aegis/
"""
import getpass
import json
import re
import time
import urllib.request
from pathlib import Path

from . import config, db

USER = getpass.getuser()
HOME = str(Path.home())
TOKEN_RE = re.compile(r"\[([A-Z_]+)_(\d+)\]")  # types may contain _ (PHONE_IN…)


def luhn_ok(s):
    d = [int(c) for c in s if c.isdigit()]
    if len(d) < 13:
        return False
    t = 0
    for i, ch in enumerate(reversed(d)):
        n = ch if i % 2 == 0 else ch * 2
        t += n if n < 10 else n - 9
    return t % 10 == 0


def ipv4_ok(s):
    try:
        return all(0 <= int(p) <= 255 for p in s.split("."))
    except ValueError:
        return False


# (type, pattern, flags, value-mode, check). ACCOUNT_NO runs BEFORE CARD
# so a labeled account number is never mislabeled as a card.
RECOGNIZERS = [
    ("PRIVATE_KEY", r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----", 0, None, None),
    ("EMAIL", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", 0, None, None),
    ("PHONE_IN", r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)", 0, None, None),
    ("AADHAAR", r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b", 0, None, None),
    ("PAN", r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", 0, None, None),
    ("IFSC", r"\b[A-Z]{4}0[A-Z0-9]{6}\b", 0, None, None),
    ("ACCOUNT_NO", r"(?:a/?c(?:count)?\.?\s*no\.?|account\s*(?:number|no\.?)|acc\.?\s*no\.?)\s*[:#-]?\s*\d{9,18}", re.I, "tail", None),
    # ends on a digit (never swallows a trailing space), Luhn-verified
    ("CARD", r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)", 0, None, "luhn"),
    ("UPI", r"\b[\w.\-]{2,30}@[a-zA-Z]{2,}\b(?!\.\w)", 0, None, None),
    ("PASSPORT", r"\b[A-Z][0-9]{7}\b", 0, None, None),
    ("DOB", r"(?:dob|date of birth|born)\s*[:\-–]?\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})", re.I, "group1", None),
    ("IPV4", r"\b(?:\d{1,3}\.){3}\d{1,3}\b", 0, None, "ipv4"),
    ("SECRET", r"\b(?:sk-[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{16,}|AIza[A-Za-z0-9_\-]{16,}|xox[bap]-[A-Za-z0-9\-]{8,})\b", 0, None, None),
    ("PASSWORD", r"(?:password|passwd|pwd)\s*[:=]\s*(\S+)", re.I, "group1", None),
    ("PERSON", r"(?:name|mr\.?|mrs\.?|ms\.?|s\/o|d\/o|holder|applicant|customer|patient)\s*[:\-–]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})", re.I, "group1", None),
]

_spacy_nlp = None


def _spacy_persons(text):
    """Optional spaCy PERSON pass. Absent model -> []. Never raises."""
    global _spacy_nlp
    try:
        if _spacy_nlp is None:
            import spacy
            _spacy_nlp = spacy.load("en_core_web_sm")
        return [(e.start_char, e.end_char, e.text)
                for e in _spacy_nlp(text[:4000]).ents if e.label_ == "PERSON"]
    except Exception:
        return []


def detect(text, use_spacy=False):
    """Ordered recognizers with span-claiming (first match wins overlaps)."""
    if not text:
        return []
    spans, occupied = [], []

    def free(s, e):
        return all(e <= a or s >= b for a, b in occupied)

    for typ, pat, flags, mode, check in RECOGNIZERS:
        for m in re.finditer(pat, text, flags):
            if mode == "group1":
                s, e, v = m.span(1), m.group(1), m.group(1)
                s, e = s[0], s[1]
            elif mode == "tail":
                tm = re.search(r"\d[\d\s\-]*$", m.group(0))
                if not tm:
                    continue
                s, e = m.start() + tm.start(), m.start() + tm.end()
                v = tm.group(0).strip()
            else:
                s, e, v = m.start(), m.end(), m.group(0)
            if not free(s, e):
                continue
            if check == "luhn" and not luhn_ok(v):
                continue
            if check == "ipv4" and not ipv4_ok(v):
                continue
            spans.append({"start": s, "end": e, "type": typ, "value": v})
            occupied.append((s, e))
    if use_spacy:
        for s, e, v in _spacy_persons(text):
            if free(s, e) and len(v.strip()) > 2:
                spans.append({"start": s, "end": e, "type": "PERSON", "value": v})
                occupied.append((s, e))
    spans.sort(key=lambda x: x["start"])
    return spans


class Vault:
    """value -> token, reversible, RAM only. Same value -> same token."""

    def __init__(self):
        self.fwd, self.rev, self.n = {}, {}, {}

    def token(self, typ, value):
        key = (typ, value)
        if key in self.fwd:
            return self.fwd[key]
        self.n[typ] = self.n.get(typ, 0) + 1
        tok = f"[{typ}_{self.n[typ]}]"
        self.fwd[key] = tok
        self.rev[tok] = value
        return tok

    def rehydrate(self, text):
        if not isinstance(text, str) or "[" not in text:
            return text
        return TOKEN_RE.sub(lambda m: self.rev.get(m.group(0), m.group(0)), text)


VAULT = Vault()


def redact(text, vault=None, use_spacy=False):
    """Local detection + reversible tokenization. Returns (text, spans, counts)."""
    vault = vault or VAULT
    spans = detect(text, use_spacy=use_spacy)
    out, counts = text, {}
    for sp in sorted(spans, key=lambda x: -x["start"]):
        tok = vault.token(sp["type"], sp["value"])
        out = out[:sp["start"]] + tok + out[sp["end"]:]
        counts[sp["type"]] = counts.get(sp["type"], 0) + 1
    return out, spans, counts


def egress_guard(text):
    """Independent stricter second pass. Token-shaped [X_N] chunks are
    never touched (split keeps them whole — equivalent to a negative
    lookahead for '[')."""
    parts = re.split(r"(\[[A-Z_]+_\d+\])", text or "")
    guarded, residual = [], 0
    for i, part in enumerate(parts):
        if i % 2 == 1:  # a whole [TYPE_N] token — leave it
            guarded.append(part)
            continue
        p = part
        p, n = re.subn(r"\b\d{9,}\b", "[MASKED]", p)
        residual += n
        p, n = re.subn(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+", "[MASKED]", p)
        residual += n
        p, n = re.subn(r"\b[A-Za-z0-9+/=_.\-]{32,}\b", "[MASKED]", p)
        residual += n
        if HOME and HOME in p:
            n = p.count(HOME)
            p = p.replace(HOME, "[MASKED_PATH]")
            residual += n
        p2, n = re.subn(r"(Users|home)[/\\]" + re.escape(USER), r"\1/[MASKED_USER]", p)
        residual += n
        p = p2
        guarded.append(p)
    return "".join(guarded), residual


# ---------------- sensitivity tiers ----------------
SENSITIVE_EXTS = {".pem", ".key", ".kdbx", ".pfx", ".p12"}
SENSITIVE_WORDS = {"aadhaar", "pan", "passport", "salary", "payslip", "medical",
                   "diagnos", "prescription", "bank", "statement", "password",
                   "secret", "credential", "tax", "itr", "form16", "w2"}
SENSITIVE_TYPES = {"AADHAAR", "PAN", "PASSPORT", "CARD", "ACCOUNT_NO",
                   "IFSC", "PRIVATE_KEY", "SECRET", "PASSWORD"}


def tier_of(filename, folder, pii_types, ext):
    if (ext or "").lower() in SENSITIVE_EXTS:
        return "Sensitive"
    hay = f"{filename} {folder}".lower()
    if any(w in hay for w in SENSITIVE_WORDS):
        return "Sensitive"
    if any(t in SENSITIVE_TYPES for t in (pii_types or [])):
        return "Sensitive"
    if pii_types:
        return "Internal"
    return "Public"


def vault_subfolder(filename, pii_types):
    """Sensitive routing from BOTH filename and entity types."""
    hay, types = (filename or "").lower(), set(pii_types or [])
    cred = types & {"SECRET", "PASSWORD", "PRIVATE_KEY"} or any(
        w in hay for w in ("password", "secret", "credential", "api", "key", ".pem", ".key"))
    if cred:
        return "Credentials"
    if types & {"AADHAAR", "PAN", "PASSPORT", "PERSON"} or any(
            w in hay for w in ("aadhaar", "pan", "passport", "visa", "license", "photo", "id")):
        return "Identity"
    if "IFSC" in types or "ACCOUNT_NO" in types or "CARD" in types or any(
            w in hay for w in ("bank", "statement", "invoice", "bill", "tax", "salary", "account", "finance")):
        return "Finance"
    if any(w in hay for w in ("medical", "diagnos", "prescription", "hospital", "lab", "health")):
        return "Medical"
    return "Identity"


# ---------------- the ONE gateway ----------------
def _post_json(url, payload, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def call_llm(provider, model, prompt, timeout=120):
    s = config.SETTINGS
    if provider == "anthropic":
        j = _post_json("https://api.anthropic.com/v1/messages",
                       {"model": model or "claude-sonnet-4-20250514", "max_tokens": 2048,
                        "system": "Reply with JSON only. No prose.",
                        "messages": [{"role": "user", "content": prompt}]},
                       {"x-api-key": s["api_key"], "anthropic-version": "2023-06-01"}, timeout)
        return "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
    if provider == "openai":
        base = (s["base_url"] or "https://api.openai.com/v1").rstrip("/")
        j = _post_json(f"{base}/chat/completions",
                       {"model": model or "gpt-4o-mini",
                        "messages": [{"role": "system", "content": "Reply with JSON only. No prose."},
                                     {"role": "user", "content": prompt}],
                        "temperature": 0.2}, {"Authorization": f"Bearer {s['api_key']}"}, timeout)
        return j["choices"][0]["message"]["content"]
    if provider == "ollama":
        base = (s.get("ollama_url") or "http://127.0.0.1:11434").rstrip("/")
        j = _post_json(f"{base}/api/chat",
                       {"model": s.get("ollama_model") or "llama3.1", "stream": False,
                        "format": "json",
                        "messages": [{"role": "system", "content": "Reply with JSON only."},
                                     {"role": "user", "content": prompt}]}, {}, timeout)
        return j["message"]["content"]
    raise ValueError(f"unknown provider {provider}")


def gateway(*, purpose, original, files_sent=0, files_withheld=0,
            prompt, local_fn=None, provider=None, model=None, timeout=120):
    """Redact -> Reason -> Rehydrate. Logs EVERY call to the ledger.

    original: raw local text (stored capped). prompt: redacted payload text
    (ids like f1/f2, redacted snippets). Returns dict with ok/egress/data.
    """
    s = config.SETTINGS
    provider = "local-rules" if s["offline"] else (provider or s["provider"])
    redacted, spans, counts = redact(original)
    guarded, residual = egress_guard(redacted)
    sent_bytes = len(guarded.encode()) if provider != "local-rules" else 0
    entities = {"spans": spans, "counts": counts}

    def log(ok, egress, data_sent, err=""):
        db.log_ledger(purpose, provider, model or s.get("model", ""), egress,
                      original, data_sent, entities, sent_bytes,
                      files_sent, files_withheld, residual, ok, err)

    try:
        if provider == "local-rules":
            data = local_fn() if local_fn else {"note": "no local handler"}
            log(True, False, "")
            return {"ok": True, "egress": False, "data": data,
                    "entities": entities, "residual": residual}
        raw = call_llm(provider, model or s.get("model", ""), prompt, timeout)
        data = json.loads(raw)          # parse FIRST ...
        data = rehydrate(data)          # ... then rehydrate per field
        log(True, True, guarded)
        return {"ok": True, "egress": True, "data": data,
                "entities": entities, "residual": residual}
    except Exception as e:  # noqa: BLE001 - ledger must capture all failures
        log(False, provider != "local-rules", guarded if provider != "local-rules" else "", str(e))
        return {"ok": False, "error": str(e), "entities": entities}


def rehydrate(obj):
    if isinstance(obj, str):
        return VAULT.rehydrate(obj)
    if isinstance(obj, list):
        return [rehydrate(x) for x in obj]
    if isinstance(obj, dict):
        return {k: rehydrate(v) for k, v in obj.items()}
    return obj
