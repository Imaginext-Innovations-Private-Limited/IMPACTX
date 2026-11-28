"""Proof card, phone-call scripts and one-tap send data."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
import io

from kk.api import app
from kk.compose.verifier import verify
from kk.proofcard import mask
from kk.service import Auditor
from kk.voice.callscript import build_calls

ROOT = Path(__file__).resolve().parents[1]
BILLS = ROOT / "tests/fixtures/sample_bills"
c = TestClient(app)
LANGS = ["en", "hi", "kn", "gu", "ta", "te"]


def _case(name):
    return json.loads((BILLS / f"{name}.json").read_text(encoding="utf-8"))


def _session(name):
    d = _case(name)
    a = Auditor()
    return a, a.audit_structured(d["bill"], d["answers"])


@pytest.mark.parametrize("lang", LANGS)
def test_proof_card_png_every_language(lang):
    sid = c.post("/api/samples/bill1").json()["id"]
    r = c.get(f"/api/audit/{sid}/proof-card.png?lang={lang}")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    im = Image.open(io.BytesIO(r.content))
    assert im.width == 1080 and 900 < im.height <= 1350


def test_proof_card_specific_finding_and_masking():
    sid = c.post("/api/samples/bill2").json()["id"]
    v = c.get(f"/api/audit/{sid}").json()
    ent = next(f for f in v["findings"] if f["rule_id"] == "ENT-COVERED")
    assert c.get(f"/api/audit/{sid}/proof-card.png?fid={ent['excess_fig']}").status_code == 200
    assert mask("Sample Heart Hospital") == "S••••• H•••• H••••••"
    assert mask(None) == "•••"


def test_proof_card_404_when_nothing_red():
    bill = {"header": {"hospital_name": "X", "admission_date": "2026-11-01", "discharge_date": "2026-11-02", "total": "100.00"},
            "lines": [{"description": "Consultation", "qty": "1", "rate": "100.00", "amount": "100.00"}]}
    sid = c.post("/api/audit-structured", json={"bill": bill, "answers": {"payer": "cash"}}).json()["id"]
    assert c.get(f"/api/audit/{sid}/proof-card.png").status_code == 404


@pytest.mark.parametrize("lang", LANGS)
def test_call_scripts_use_only_verified_figures(lang):
    a, s = _session("bill2_knee_pmjay")
    calls = build_calls(s.result, lang)
    assert {x["who"] for x in calls} == {"hospital", "scheme"}
    scheme = next(x for x in calls if x["who"] == "scheme")
    assert scheme["phone"] == "14555"
    for call in calls:
        # text without bill item names and without figure slots must hold no number at all
        bare = "".join("".join(seg["t"] for seg in sent if "fig" not in seg and not seg.get("item"))
                       for sent in call["sentences"])
        assert verify(bare, {}, lang).ok, (lang, bare)
        figs = [seg["fig"] for sent in call["sentences"] for seg in sent if "fig" in seg]
        assert figs and all(f in s.result.figures for f in figs)
        assert call["speech_lines"] and all(l.strip() for l in call["speech_lines"])


def test_call_script_amounts_match_findings():
    a, s = _session("bill1_cardiac_cash")
    [call] = build_calls(s.result, "en")
    shown = "".join("".join(seg["t"] for seg in sent) for sent in call["sentences"])
    for amount in ("₹58,000.00", "₹41,145.33", "₹16,854.67", "₹20,469.34"):
        assert amount in shown
    assert "fifty-eight thousand rupees" in " ".join(call["speech_lines"])


def test_call_api_and_audio():
    sid = c.post("/api/samples/bill1").json()["id"]
    calls = c.get(f"/api/audit/{sid}/calls?lang=hi").json()
    assert [x["who"] for x in calls] == ["hospital"]
    r = c.get(f"/api/audit/{sid}/calls/hospital/audio?lang=hi")
    assert r.status_code == 200 and len(r.content) > 1000
    assert c.get(f"/api/audit/{sid}/calls/scheme/audio").status_code == 404


def test_letters_carry_subject_for_one_tap_send():
    sid = c.post("/api/samples/bill1").json()["id"]
    for l in c.get(f"/api/audit/{sid}/letters?lang=ta").json():
        assert set(l["subjects"]) == {"ta", "en"} and all(l["subjects"].values())


def test_confirm_panel_line_crop_shows_the_number_columns():
    a = Auditor()
    s = a.audit_files([str(ROOT / "tests/fixtures/demo/bill3_stained_photo.jpg")], {"payer": "cash", "state": "karnataka"})
    png = a.line_crop_png(s, "L2")
    im = Image.open(io.BytesIO(png))
    assert im.width < 6 * im.height * 2 and im.width > 300
    assert a.line_crop_png(s, "L99") is None
