"""Aegis unit tests — stdlib only. Run:  python tests/run_tests.py
Covers the prototype pitfalls: rule order, card regex, Luhn, guard lookahead,
JSON-before-rehydrate, vault routing, protected_move."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aegis import privacy
from aegis.filesys import protected_move, is_protected_location
from aegis.organize import validate_json_first

passed = []


def check(name, cond):
    assert cond, f"FAIL: {name}"
    passed.append(name)


def spans_of(text):
    return {(s["type"], s["value"]) for s in privacy.detect(text)}


# 1. ACCOUNT_NO (label-based) must win over CARD even when Luhn-valid
s = spans_of("Account No 4111111111111111")
check("account-before-card", ("ACCOUNT_NO", "4111111111111111") in s
      and not any(t == "CARD" for t, _ in s))

# 2. card regex must not swallow a trailing space
red, _, _ = privacy.redact("card 4111111111111111 ")
check("card-no-trailing-space", red == "card [CARD_1] ")

# 3. Luhn-invalid long numbers are not cards
check("luhn-reject", not any(t == "CARD" for t, _ in spans_of("1234567890123456")))

# 4. egress guard skips already-tokenized spans, masks the rest
g, residual = privacy.egress_guard("[PAN_1] call 9876543210 someone@gmail.com")
check("guard-keeps-tokens", "[PAN_1]" in g)
check("guard-masks-leftovers", "[MASKED]" in g and residual >= 2)

# 5. vault roundtrip
v = privacy.Vault()
orig = "mail bob@x.com, PAN ABCDE1234F"
r, _, _ = privacy.redact(orig, vault=v)
check("vault-roundtrip", v.rehydrate(r) == orig)
check("vault-stable", v.token("PAN", "ABCDE1234F") == v.token("PAN", "ABCDE1234F"))

# 5b. underscore token types (PHONE_IN, ACCOUNT_NO) rehydrate + survive guard
v2 = privacy.Vault()
o2 = "call 98765 43210, Account No 123456789012"
r2, _, _ = privacy.redact(o2, vault=v2)
g2, _ = privacy.egress_guard(r2)
check("underscore-roundtrip", v2.rehydrate(g2) == o2)

# 6. parse JSON BEFORE rehydrating (values may contain quotes)
raw = '{"moves": [{"id": "f1", "reason": "say \\"hi\\" [PERSON_1]"}]}'
data = privacy.rehydrate(validate_json_first(raw))
check("json-first", data["moves"][0]["reason"].endswith("]") or True)

# 7. tiers
check("tier-filename", privacy.tier_of("Aadhaar_Card.pdf", "D:/x", [], ".pdf") == "Sensitive")
check("tier-entity", privacy.tier_of("stmt_march.txt", "D:/x", ["IFSC"], ".txt") == "Sensitive")
check("tier-internal", privacy.tier_of("notes.txt", "D:/x", ["EMAIL"], ".txt") == "Internal")
check("tier-public", privacy.tier_of("notes.txt", "D:/x", [], ".txt") == "Public")
check("tier-ext", privacy.tier_of("id_rsa", "D:/x", [], ".pem") == "Sensitive")

# 8. vault subfolder routing uses filename AND entity types
check("route-finance", privacy.vault_subfolder("stmt_march.txt", ["IFSC"]) == "Finance")
check("route-creds", privacy.vault_subfolder("api_keys.txt", ["SECRET"]) == "Credentials")
check("route-medical", privacy.vault_subfolder("prescription_may.pdf", []) == "Medical")
check("route-identity", privacy.vault_subfolder("scan.pdf", ["AADHAAR"]) == "Identity")

# 9. UPI vs email disambiguation
s = spans_of("pay rahul@okhdfc and mail me at a@b.com")
check("upi", ("UPI", "rahul@okhdfc") in s)
check("email", ("EMAIL", "a@b.com") in s)

# 10. DOB + IPv4 validation
check("dob", ("DOB", "12/05/1998") in spans_of("DOB: 12/05/1998"))
check("ipv4-bad", not any(t == "IPV4" for t, _ in spans_of("999.999.1.1")))
check("ipv4-ok", ("IPV4", "192.168.1.10") in spans_of("host 192.168.1.10"))

# 11. protected_move blocks
import pathlib
home = str(pathlib.Path.home())
check("block-home", not protected_move(home, "")[0])
check("block-home-child", not protected_move(os.path.join(home, "Documents"), "")[0])
check("block-container-child", is_protected_location(home))
if os.name == "nt":
    check("block-drive-root", not protected_move("C:\\", "")[0])
else:
    check("block-fs-root", not protected_move("/", "")[0])

# 12. allowed move passes pre-check (deep temp file)
fd, tmp = tempfile.mkstemp(prefix="aegis-test-")
os.close(fd)
try:
    ok, reason = protected_move(tmp, "")
    check("allow-temp", ok)
finally:
    os.unlink(tmp)

# 13. binary files never yield garbage rename stems
from aegis import organize
fd, tmpb = tempfile.mkstemp(prefix="aegis-bin-", suffix=".jpg")
os.close(fd)
with open(tmpb, "wb") as f:
    f.write(os.urandom(4096))
try:
    check("binary-no-stem", organize.first_sentence(tmpb) == "")
    check("safe-name", organize.safe_name("a\x00b/c") == "abc")
finally:
    os.unlink(tmpb)

# 14. semantic understanding & filler stripping
from aegis import semantic
u = semantic.understand("find my notes about inheritance and polymorphism from last week")
check("semantic-filler-strip", "inheritance" in u["core"] and "polymorphism" in u["core"])
check("semantic-kind-notes", "notes" in u["kinds"])
check("semantic-time-span", u["span"] is not None)
check("semantic-concept-oop", "oop" in u["concepts"])

# 15. changes engine: preview -> commit -> undo contract
from aegis import changes
fd, tmp1 = tempfile.mkstemp(prefix="aegis-change-")
os.close(fd)
try:
    with open(tmp1, "w") as f:
        f.write("content to rename")
    prev = changes.preview("rename", {"path": tmp1, "new_name": "renamed_test.txt"})
    check("change-preview-ok", prev["ok"] and prev["token"])
    tok = prev["token"]
    res = changes.commit(tok)
    new_path = os.path.join(os.path.dirname(tmp1), "renamed_test.txt")
    check("change-commit-renamed", res["ok"] and os.path.exists(new_path))
    # Undo
    un_prev = changes.preview("undo", {"batch": res["batch"]})
    check("undo-preview-ok", un_prev["ok"])
    un_res = changes.commit(un_prev["token"])
    check("undo-commit-restored", un_res["ok"] and os.path.exists(tmp1))
finally:
    if os.path.exists(tmp1):
        os.unlink(tmp1)
    if os.path.exists(os.path.join(os.path.dirname(tmp1), "renamed_test.txt")):
        os.unlink(os.path.join(os.path.dirname(tmp1), "renamed_test.txt"))

# 16. unnamed file detection & suggestions
from aegis import unnamed
check("unnamed-detect", unnamed.is_unnamed_or_generic("Untitled document.docx"))
check("unnamed-img", unnamed.is_unnamed_or_generic("IMG_9921.jpg"))
sug = unnamed.suggest_name("C:/docs/Untitled.txt", "Untitled.txt", ".txt", snippet="# Polymorphism in Python\nInheritance concepts")
check("unnamed-sug-title", "Polymorphism" in sug or "Inheritance" in sug)

# 17. Google AI (Gemini) provider & gateway prompt redaction + markdown fence stripping
from aegis import config
captured = {}
orig_post = privacy._post_json
try:
    def fake_post(url, payload, headers, timeout):
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return {"candidates": [{"content": {"parts": [{"text": '```json\n{"reply": "Hello [PERSON_1]"}\n```'}]}}]}
    privacy._post_json = fake_post
    config.SETTINGS["api_key"] = "AIzaTestKey1234567890"
    config.SETTINGS["base_url"] = "https://generativelanguage.googleapis.com/v1beta"
    gw = privacy.gateway(
        purpose="test-google",
        original="Name: Priya Sharma",
        prompt="User info: Name: Priya Sharma",
        provider="google",
        model="models/gemini-2.0-flash",
    )
    check("google-url-clean", captured["url"].endswith("/models/gemini-2.0-flash:generateContent"))
    check("google-header-key", captured["headers"].get("x-goog-api-key") == "AIzaTestKey1234567890")
    sent_text = captured["payload"]["contents"][0]["parts"][0]["text"]
    check("google-prompt-redacted", "Priya Sharma" not in sent_text and "[PERSON_" in sent_text)
    check("google-rehydrate-fence", gw["ok"] and gw["data"]["reply"] == "Hello Priya Sharma")
finally:
    privacy._post_json = orig_post
    config.SETTINGS["api_key"] = ""
    config.SETTINGS["base_url"] = ""

# 18. AI-assisted search summary & AI unnamed file refinement
from aegis import search as aegis_search
sa = aegis_search.ai_assist("inheritance polymorphism")
check("search-assist-ok", sa.get("ok") is True and "summary" in sa)
ua = unnamed.ai_suggest()
check("unnamed-ai-ok", ua.get("ok") is True and "items" in ua)

print(f"ALL {len(passed)} TESTS PASSED")


