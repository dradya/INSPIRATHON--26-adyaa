"""Aegis acceptance smoke test against a live server.
Run:  python tests/smoke.py  (server must be up: python app.py --port 8001)
Uses a temp fixture only — never touches real user files.
"""
import json
import os
import sys
import tempfile
import time
import urllib.request

BASE = os.environ.get("AEGIS_BASE", "http://127.0.0.1:8001")
passed = []


def check(name, cond, extra=""):
    assert cond, f"FAIL: {name} {extra}"
    passed.append(name)
    print(f"  ok: {name}")


def call(method, path, body=None, headers=None):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", **(headers or {})},
        method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, {}


import urllib.error  # noqa: E402


def fixture():
    # NOTE: not %TEMP% — the dup finder deliberately ignores AppData/Temp.
    root = tempfile.mkdtemp(prefix="aegis-smoke-", dir=os.path.expanduser("~"))
    docs = os.path.join(root, "docs")
    dl = os.path.join(root, "downloads")
    os.makedirs(docs)
    os.makedirs(dl)
    old = time.time() - 100 * 86400  # ~last semester
    f1 = os.path.join(docs, "rent_agreement.txt")
    with open(f1, "w") as f:
        f.write("RENT AGREEMENT\nTenant: Rahul Verma\nAccount No 123456789012\n"
                "Rent Rs 12000 per month. Signed March.")
    os.utime(f1, (old, old))
    bank = os.path.join(docs, "bank_details.txt")
    with open(bank, "w") as f:
        f.write("HDFC Bank\nIFSC HDFC0001234\nAccount No 50100234567890\n")
    dup_a = os.path.join(dl, "notes.txt")
    dup_b = os.path.join(dl, "notes - Copy.txt")
    for p in (dup_a, dup_b):
        with open(p, "w") as f:
            f.write("same content " * 500)
    with open(os.path.join(dl, "IMG_1234.jpg"), "wb") as f:
        f.write(os.urandom(2048))
    with open(os.path.join(dl, "Untitled.txt"), "w") as f:
        f.write("Project kickoff meeting notes. Decide the stack by Friday.")
    return root, docs, dl


print("== 7. hostile Host header ==")
code, _ = call("GET", "/api/health", headers={"Host": "evil.com"})
check("evil-host-403", code == 403, f"got {code}")

print("== scan fixture ==")
root, docs, dl = fixture()
print("   fixture:", root)
code, r = call("POST", "/api/scan", {"paths": [root]})
check("scan-started", code == 200 and r.get("started", True))
for _ in range(60):
    _, p = call("GET", "/api/scan/progress")
    if not p.get("running"):
        break
    time.sleep(2)
check("scan-done", not p.get("running"), str(p))

print("== 1. search real files ==")
_, r = call("GET", "/api/search?q=" + urllib.parse.quote("rent agreement last semester"))
names = [x["name"] for x in r.get("results", [])]
check("search-finds-rent", "rent_agreement.txt" in names, str(names))
check("time-boost-on", r.get("time_boost") is True)
_, r = call("GET", "/api/search?q=" + urllib.parse.quote("kickoff meeting"))
check("search-content", any("Untitled" in x["name"] for x in r.get("results", [])))

print("== 2. organize plan (local-rules, nothing leaves) ==")
_, plan = call("POST", "/api/organize/plan", {"base": dl})
check("plan-ok", plan.get("ok"), str(plan)[:300])
check("plan-local", plan.get("source") == "local-rules")
check("plan-no-egress", plan.get("ledger", {}).get("egress") is False)
_, led = call("GET", "/api/ledger?limit=5")
check("ledger-logged", any(x["purpose"] == "organize-plan" for x in led.get("rows", [])))

print("== 3. apply + undo ==")
first = plan["moves"][0]
_, ap = call("POST", "/api/organize/apply",
             {"batch": plan["batch"], "selected": [first["id"]]})
check("apply-ok", ap.get("applied", [{}])[0].get("ok"))
check("apply-moved", os.path.exists(ap["applied"][0]["dest"])
      and not os.path.exists(first["old"]))
_, un = call("POST", "/api/organize/undo", {"batch": plan["batch"]})
check("undo-ok", un.get("undone", [{}])[0].get("ok"))
check("undo-restored", os.path.exists(first["old"]))

print("== 4. duplicates + quarantine + undo ==")
call("POST", "/api/dups/start")
for _ in range(60):
    _, d = call("GET", "/api/dups/status")
    if not d.get("running"):
        break
    time.sleep(2)
check("dups-found", len(d.get("groups", [])) >= 1, str(d.get("groups"))[:200])
victim = os.path.join(dl, "notes - Copy.txt")
_, qq = call("POST", "/api/quarantine", {"paths": [victim]})
check("quarantined", qq["moved"][0]["ok"] and not os.path.exists(victim))
_, qu = call("POST", "/api/quarantine/undo", {"batch": qq["batch"]})
check("quar-restored", qu["restored"][0]["ok"] and os.path.exists(victim))

print("== 6. offline mode = zero egress ==")
call("POST", "/api/offline", {"on": True})
_, plan2 = call("POST", "/api/organize/plan", {"base": dl})
_, led2 = call("GET", "/api/ledger?limit=3")
last = led2["rows"][0]
check("offline-no-egress", last["egress"] == 0 and last["bytes_sent"] == 0)
call("POST", "/api/offline", {"on": False})

print("== redact tester ==")
_, rt = call("POST", "/api/redact-test", {"text": "My PAN is ABCDE1234F, call 98765 43210"})
check("redact-pan", rt["counts"].get("PAN") == 1, str(rt["counts"]))
check("roundtrip", rt["roundtrip_ok"] is True)

print(f"\nALL {len(passed)} SMOKE TESTS PASSED on real files in {root}")
import shutil
shutil.rmtree(root, ignore_errors=True)
print("fixture cleaned up")
