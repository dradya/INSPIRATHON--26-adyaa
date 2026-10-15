"""Local meaning engine. 100% on-device, no model download, no network.

Three ideas make keyword-free search work:
  1. Query understanding  - strip conversational filler ("find my ... about"),
     detect the file KIND the user means ("notes", "photos", "slides") and
     time phrases ("last week", "in 2023", "yesterday").
  2. Concept clusters      - curated topic families. A word activates its
     family, so "inheritance polymorphism" reaches a file that only says
     "subclass ... override ... abstract class".
  3. Concept-aware vectors - every token also emits its concept ids into a
     hashed vector, so related words share dimensions and cosine similarity
     measures topical overlap, not just spelling.
"""
import calendar
import hashlib
import re
import time

import numpy as np

EMBEDDER = "aegis-sem-v2"
DIM = 768

STOP = set("""
a an the and or but if then else of to in on at by for with from into onto over under
about above below between through during before after again further once here there
is am are was were be been being have has had having do does did doing will would
shall should can could may might must i me my mine myself we our ours you your yours
he him his she her hers it its they them their what which who whom whose this that
these those all any both each few more most other some such no nor not only own same
so than too very just also any anything something everything find search look looking
show give get open where wheres locate fetch pull bring want need please file files
thing things stuff related regarding concerning re around kind sort type one ones
remember dont don't cant can't recall forgot forget named called name somewhere
lately recently recent old older new newer latest copy version had wrote written made
""".split())

FILLER = re.compile(
    r"^(?:hey|hi|ok|okay|please|can you|could you|would you|help me|i want to|"
    r"i need to|i'm looking for|im looking for|i am looking for|where did i put|"
    r"where is|where are|where's|show me|find me|find|search for|search|look for|"
    r"get me|open|locate|pull up|bring up)\s+", re.I)

# kind words -> extension family (boost, never a hard filter)
KINDS = {
    "notes": {".txt", ".md", ".docx", ".doc", ".pdf", ".rtf", ".odt", ".one", ".pptx"},
    "document": {".pdf", ".docx", ".doc", ".txt", ".md", ".rtf", ".odt"},
    "pdf": {".pdf"},
    "slides": {".ppt", ".pptx", ".key", ".odp", ".pdf"},
    "sheet": {".xls", ".xlsx", ".csv", ".ods", ".numbers"},
    "image": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp", ".svg"},
    "video": {".mp4", ".mkv", ".mov", ".avi", ".webm"},
    "audio": {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac"},
    "code": {".py", ".js", ".jsx", ".ts", ".java", ".c", ".cpp", ".cs", ".go", ".rs",
             ".html", ".css", ".ipynb", ".kt", ".rb", ".php"},
    "archive": {".zip", ".rar", ".7z", ".tar", ".gz"},
}
KIND_WORDS = {
    "notes": "notes", "note": "notes", "notebook": "notes", "lecture": "notes",
    "lectures": "notes", "summary": "notes", "summaries": "notes",
    "doc": "document", "docs": "document", "document": "document",
    "documents": "document", "essay": "document", "report": "document",
    "reports": "document", "letter": "document", "assignment": "document",
    "assignments": "document", "paper": "document", "papers": "document",
    "pdf": "pdf", "pdfs": "pdf",
    "slides": "slides", "slide": "slides", "presentation": "slides",
    "presentations": "slides", "ppt": "slides", "deck": "slides",
    "spreadsheet": "sheet", "spreadsheets": "sheet", "excel": "sheet",
    "sheet": "sheet", "sheets": "sheet", "csv": "sheet", "budget": "sheet",
    "photo": "image", "photos": "image", "picture": "image", "pictures": "image",
    "pic": "image", "pics": "image", "image": "image", "images": "image",
    "screenshot": "image", "screenshots": "image", "selfie": "image",
    "wallpaper": "image",
    "video": "video", "videos": "video", "movie": "video", "movies": "video",
    "clip": "video", "recording": "video", "recordings": "video",
    "song": "audio", "songs": "audio", "music": "audio", "audio": "audio",
    "podcast": "audio", "voice": "audio",
    "code": "code", "script": "code", "scripts": "code", "program": "code",
    "source": "code",
    "zip": "archive", "archive": "archive", "backup": "archive",
}
FOLDER_WORDS = {"folder", "folders", "directory", "directories", "dir"}

# Topic families. Words are matched after stemming; multi-word keys are
# phrases checked on the raw text.
CONCEPTS = {
    "oop": "oop object oriented class classes object objects inheritance inherit inherits "
           "inherited polymorphism polymorphic encapsulation abstraction abstract "
           "interface interfaces subclass superclass override overriding overload "
           "overloading constructor destructor method methods virtual extends implements "
           "base derived instance instantiate getter setter",
    "dsa": "data structure structures algorithm algorithms array arrays linked list stack "
           "queue tree trees binary heap graph graphs hash hashing sort sorting search "
           "searching recursion dynamic programming greedy complexity bfs dfs dijkstra trie",
    "dbms": "database databases dbms sql query queries table tables normalization "
            "normal form join joins schema relational transaction acid index mysql "
            "postgres mongodb er diagram primary foreign key",
    "os": "operating system os process processes thread threads scheduling deadlock "
          "semaphore mutex memory paging virtual kernel cpu synchronization",
    "network": "network networking computer networks tcp ip udp http protocol router "
               "osi layer packet socket dns lan subnet",
    "ml": "machine learning ml ai artificial intelligence neural network deep learning "
          "model training regression classification dataset tensorflow pytorch "
          "cnn rnn transformer nlp clustering supervised unsupervised",
    "web": "web html css javascript react frontend backend api server node express "
           "website webpage django flask",
    "programming": "programming code coding python java javascript c++ cpp function "
                   "functions variable loop loops compiler syntax debugging",
    "math": "math mathematics calculus derivative derivatives integral integrals limit "
            "algebra linear matrix matrices vector vectors equation equations theorem "
            "proof geometry trigonometry",
    "stats": "statistics probability distribution mean median variance hypothesis "
             "regression sample random",
    "physics": "physics mechanics force motion energy thermodynamics quantum "
               "electricity magnetism optics wave waves velocity acceleration newton",
    "chemistry": "chemistry chemical reaction reactions organic inorganic molecule "
                 "atom atoms bond periodic acid base",
    "biology": "biology cell cells dna gene genetics evolution organism anatomy "
               "physiology protein enzyme",
    "economics": "economics economy market demand supply inflation gdp microeconomics "
                 "macroeconomics",
    "finance": "finance financial bank banking account statement invoice invoices bill "
               "bills receipt receipts payment payments salary payslip tax taxes itr "
               "expense expenses budget loan emi credit debit transaction upi gst",
    "career": "resume cv curriculum vitae cover letter job jobs internship interview "
              "offer career portfolio linkedin experience skills hiring",
    "college": "college university semester sem exam exams syllabus lecture lectures "
               "assignment assignments lab practical course coursework grade grades "
               "marksheet transcript tutorial homework study",
    "travel": "travel trip vacation holiday flight flights ticket tickets boarding pass "
              "hotel booking itinerary visa passport airport train",
    "medical": "medical health doctor hospital prescription diagnosis report reports "
               "medicine clinic lab test blood scan insurance",
    "legal": "legal contract agreement agreements lease rent rental tenant landlord "
             "affidavit court law license certificate deed",
    "housing": "rent rental lease tenant landlord apartment flat house property deposit",
    "meeting": "meeting meetings minutes agenda kickoff standup discussion action items "
               "notes plan planning roadmap",
    "project": "project projects proposal plan report documentation spec requirements "
               "design architecture milestone deadline",
    "food": "recipe recipes cooking food meal ingredients dish kitchen diet",
    "fitness": "fitness workout exercise gym running diet training yoga",
    "photo": "photo photos picture pictures camera selfie album wedding birthday",
    "music": "music song songs album playlist audio lyrics",
}

_SUFFIXES = ("ational", "ization", "fulness", "ousness", "iveness", "ations",
             "ation", "ments", "ment", "ness", "ings", "ing", "ies", "ied", "ers",
             "edly", "ed", "es", "ly", "er", "s")


def stem(w):
    w = w.lower()
    if len(w) <= 4 or w.isdigit():
        return w
    for suf in _SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            base = w[:-len(suf)]
            if suf in ("ies", "ied"):
                base += "y"
            return base
    return w


def _build_index():
    idx = {}
    for cid, words in CONCEPTS.items():
        for w in words.split():
            idx.setdefault(stem(w), set()).add(cid)
    return idx


CONCEPT_OF = _build_index()
CONCEPT_WORDS = {cid: sorted({w for w in words.split() if len(w) > 2})
                 for cid, words in CONCEPTS.items()}

TOKEN = re.compile(r"[a-z0-9][a-z0-9+#]*")


def tokens(text):
    return TOKEN.findall((text or "").lower())


def split_name(name):
    """IMG_2041 -> img 2041; myResumeFinal -> my resume final."""
    n = re.sub(r"([a-z])([A-Z])", r"\1 \2", name or "")
    return re.sub(r"[_\-.()\[\]]+", " ", n)


# ---------------- query understanding ----------------
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})


def parse_time(q):
    now = time.time()
    lt = time.localtime(now)
    day = 86400
    rules = [
        (r"\btoday\b", lambda m: (now - (lt.tm_hour * 3600 + lt.tm_min * 60), now)),
        (r"\byesterday\b", lambda m: (now - 2 * day, now - day * 0.5)),
        (r"\b(?:this|past|last)\s+week\b", lambda m: (now - 7 * day, now)),
        (r"\b(?:this|past|last)\s+month\b", lambda m: (now - 31 * day, now)),
        (r"\b(?:last|past)\s+(?:semester|sem)\b|\bpast\s+6\s+months\b",
         lambda m: (now - 183 * day, now)),
        (r"\b(?:this|past|last)\s+year\b", lambda m: (now - 365 * day, now)),
        (r"\b(?:last|past)\s+(\d{1,3})\s+(day|days|week|weeks|month|months)\b",
         lambda m: (now - int(m.group(1)) * day * {"d": 1, "w": 7, "m": 30}[m.group(2)[0]], now)),
        (r"\b(?:in|from|during)\s+((?:19|20)\d{2})\b",
         lambda m: (time.mktime((int(m.group(1)), 1, 1, 0, 0, 0, 0, 0, -1)),
                    time.mktime((int(m.group(1)) + 1, 1, 1, 0, 0, 0, 0, 0, -1)))),
    ]
    span, label = None, ""
    for pat, fn in rules:
        m = re.search(pat, q, re.I)
        if m:
            span, label = fn(m), m.group(0)
            q = q[:m.start()] + " " + q[m.end():]
            break
    if not span:
        m = re.search(r"\b(?:in|from|during)\s+(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\b", q, re.I)
        if m:
            mon = MONTHS[m.group(1).lower()]
            yr = lt.tm_year if mon <= lt.tm_mon else lt.tm_year - 1
            start = time.mktime((yr, mon, 1, 0, 0, 0, 0, 0, -1))
            end = time.mktime((yr + (mon == 12), mon % 12 + 1, 1, 0, 0, 0, 0, 0, -1))
            span, label = (start, end), m.group(0)
            q = q[:m.start()] + " " + q[m.end():]
    return q, span, label.strip()


def understand(query):
    """Natural-language query -> structured intent."""
    raw = (query or "").strip()
    q = raw
    for _ in range(3):
        q2 = FILLER.sub("", q)
        if q2 == q:
            break
        q = q2
    q, span, time_label = parse_time(q)
    toks = tokens(q)
    kinds, want_folder, core = [], False, []
    for t in toks:
        if t in FOLDER_WORDS:
            want_folder = True
            continue
        if t in KIND_WORDS:
            k = KIND_WORDS[t]
            if k not in kinds:
                kinds.append(k)
            if k in ("notes", "slides", "sheet"):
                continue  # pure kind word, not topic
            if t in ("report", "reports", "assignment", "assignments", "lecture",
                     "lectures", "budget", "screenshot", "screenshots", "project"):
                core.append(t)  # these are also topical
            continue
        if t in STOP or len(t) < 2:
            continue
        core.append(t)
    if not core and not kinds:  # query was all filler; fall back to raw words
        core = [t for t in tokens(raw) if len(t) > 1][:8]
    concepts = {}
    for t in core:
        for c in CONCEPT_OF.get(stem(t), ()):
            concepts[c] = concepts.get(c, 0) + 1
    phrase_q = " " + " ".join(tokens(q)) + " "
    for cid, words in CONCEPTS.items():
        for ph in re.findall(r"\b\w+ \w+\b", words):
            if f" {ph} " in phrase_q:
                concepts[cid] = concepts.get(cid, 0) + 1
    exts = set()
    for k in kinds:
        exts |= KINDS[k]
    return {
        "raw": raw, "text": " ".join(core), "core": core[:12],
        "stems": [stem(t) for t in core[:12]],
        "kinds": kinds, "exts": exts, "folder": want_folder,
        "span": span, "time_label": time_label,
        "concepts": sorted(concepts, key=lambda c: -concepts[c]),
    }


def expansions(intent, limit=14):
    """Related words from the activated concept families (minus the query)."""
    have = set(intent["stems"])
    out = []
    for cid in intent["concepts"][:3]:
        for w in CONCEPT_WORDS[cid]:
            s = stem(w)
            if s not in have and " " not in w and len(w) > 3:
                have.add(s)
                out.append(w)
    return out[:limit]


# ---------------- concept-aware hashed vectors ----------------
def _h(feature):
    d = hashlib.blake2b(feature.encode(), digest_size=8).digest()
    return int.from_bytes(d[:4], "little") % DIM, (1.0 if d[4] & 1 else -1.0)


_CACHE = {}


def _feat(f):
    r = _CACHE.get(f)
    if r is None:
        if len(_CACHE) > 400000:
            _CACHE.clear()
        r = _CACHE[f] = _h(f)
    return r


def embed_text(text, name=""):
    v = np.zeros(DIM, dtype=np.float32)
    counts = {}
    for t in tokens(text)[:1500]:
        if t in STOP or len(t) < 2:
            continue
        s = stem(t)
        counts[s] = counts.get(s, 0) + 1
    name_toks = [t for t in tokens(split_name(name)) if t not in STOP and len(t) > 1]
    for t in name_toks:  # filename words count triple
        s = stem(t)
        counts[s] = counts.get(s, 0) + 3
    concept_mass = {}
    for s, c in counts.items():
        w = 1.0 + np.log(c)  # sublinear tf
        i, sg = _feat("w:" + s)
        v[i] += sg * w
        for cid in CONCEPT_OF.get(s, ()):
            concept_mass[cid] = concept_mass.get(cid, 0) + w
    for t in name_toks:  # fuzzy filename match via char trigrams
        if len(t) >= 4:
            for k in range(len(t) - 2):
                i, sg = _feat("c:" + t[k:k + 3])
                v[i] += sg * 0.35
    for cid, m in concept_mass.items():
        # concept dims: several features per concept so they dominate
        # when a document is clearly about a topic
        strength = 1.6 * np.sqrt(m)
        for r in range(4):
            i, sg = _feat(f"k{r}:{cid}")
            v[i] += sg * strength
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def embed_query(intent):
    text = intent["text"] or intent["raw"]
    return embed_text(text)


def best_passage(snippet, terms, width=220):
    """Window of the snippet that covers the most query terms."""
    s = re.sub(r"\s+", " ", snippet or "").strip()
    if not s:
        return ""
    if not terms:
        return s[:width]
    low = s.lower()
    hits = []
    for t in terms:
        for m in re.finditer(re.escape(t.lower()), low):
            hits.append(m.start())
    if not hits:
        return s[:width]
    hits.sort()
    best, best_n = hits[0], 0
    for h in hits:
        n = sum(1 for x in hits if h <= x < h + width)
        if n > best_n:
            best, best_n = h, n
    start = max(0, best - 40)
    out = s[start:start + width]
    return ("…" if start else "") + out + ("…" if start + width < len(s) else "")
