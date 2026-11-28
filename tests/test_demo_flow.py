"""The stage demo: number guard, official basis on PM-JAY findings, and the confirm flow."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kk.api import app
from kk.grievance import letters
from kk.service import Auditor

ROOT = Path(__file__).resolve().parents[1]
BILLS = ROOT / "tests/fixtures/sample_bills"
c = TestClient(app)


def _sid(name):
    d = json.loads((BILLS / f"{name}.json").read_text(encoding="utf-8"))
    return c.post("/api/audit-structured", json={"bill": d["bill"], "answers": d["answers"]}).json()["id"]


@pytest.fixture(scope="module")
def sid1():
    return _sid("bill1_cardiac_cash")


@pytest.mark.parametrize("lang,text,code", [
    ("en", "The hospital overcharged you ₹25,000 for the stent.", "digit"),
    ("en", "You were charged twenty thousand too much.", "words"),
    ("hi", "अस्पताल ने आपसे पच्चीस हज़ार रुपये ज़्यादा लिए।", "words"),
    ("ta", "மருத்துவமனை உங்களிடம் ௨௫ ஆயிரம் அதிகம் வசூலித்தது.", "digit"),
    ("te", "ఆసుపత్రి ₹ ఎక్కువ తీసుకుంది.", "currency"),
    ("en", "Refund [excess:F999] now.", "unknown_slot"),
])
def test_guard_blocks(sid1, lang, text, code):
    r = c.post(f"/api/audit/{sid1}/guard", json={"text": text, "lang": lang}).json()
    assert not r["ok"] and code in r["codes"]


def test_guard_passes_a_slot_and_fills_it_from_proof(sid1):
    slot = c.get(f"/api/audit/{sid1}/guard").json()["slot"]
    assert slot and slot.startswith("[")
    for lang, text in (("en", f"The hospital charged {slot} more than the rule allows."),
                       ("hi", f"अस्पताल ने नियम से {slot} ज़्यादा लिया।")):
        r = c.post(f"/api/audit/{sid1}/guard", json={"text": text, "lang": lang}).json()
        assert r["ok"], r
        filled = "".join(s["t"] for s in r["segments"])
        assert "₹" in filled and "[" not in filled
    # a slot used as the wrong kind of amount is refused
    fid = slot.split(":")[1].rstrip("]")
    r = c.post(f"/api/audit/{sid1}/guard", json={"text": f"Total ceiling [ceiling:{fid}].", "lang": "en"}).json()
    assert not r["ok"] and "wrong_role" in r["codes"]


def test_pmjay_findings_quote_the_official_basis():
    sid = _sid("bill2_knee_pmjay")
    v = c.get(f"/api/audit/{sid}?lang=hi").json()
    ent = [f for f in v["findings"] if f["rule_id"].startswith("ENT-") and f["verdict"] == "red"]
    assert ent
    for f in ent:
        quotes = " ".join(b["quote"] for b in f["basis"])
        assert "benefit package includes the entire cost of treatment" in quotes
        assert any("Operation Manual" in b["title"] for b in f["basis"])
    a = Auditor()
    d = json.loads((BILLS / "bill2_knee_pmjay.json").read_text(encoding="utf-8"))
    s = a.audit_structured(d["bill"], d["answers"])
    ls = letters(s.result, "kn", a.kb.dir)
    scheme = [l for l in ls if l["channel"] == "scheme_grievance"][0]
    assert "entire cost of treatment" in scheme["letters"]["kn"] and "ಆಧಾರ" in scheme["letters"]["kn"]


def test_stained_photo_asks_to_confirm_then_clears():
    d = json.loads((BILLS / "bill3_interim_photo.json").read_text(encoding="utf-8"))
    a = Auditor()
    s = a.audit_files([str(ROOT / "tests/fixtures/demo/bill3_stained_photo.jpg")], d["answers"])
    v = a.view(s, "en")
    assert "L2" in v["needs_confirmation"]
    s = a.confirm(s.id, {"L2": {"rate": "52000.00"}}, [l for l in v["needs_confirmation"] if l != "L2"])
    v = a.view(s, "en")
    assert v["needs_confirmation"] == []
    clean = a.audit_files([str(BILLS / "bill3_interim_photo.jpg")], d["answers"])
    assert s.figs.value(s.result.recoverable_fig) == clean.figs.value(clean.result.recoverable_fig)


def test_one_click_samples():
    v = c.post("/api/samples/bill1?lang=kn").json()
    assert v["language"] == "kn" and v["id"]
    assert c.post("/api/samples/nope").status_code == 404
