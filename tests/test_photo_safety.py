"""A number read from a photo never becomes an accusation without the family confirming it."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kk.api import app
from kk.extraction import needs_confirmation, validate
from kk.figures import FigureStore
from kk.models import Bill, BillLine, Evidence, Origin, Role
from kk import proofcard
from kk.service import Auditor

ROOT = Path(__file__).resolve().parents[1]


def _bill(conf):
    figs = FigureStore()
    ev = Evidence(note="test")
    line = BillLine(id="L1", description="Drug Eluting Stent",
                    qty_fig=figs.add("1", "count", Role.QUANTITY, Origin.BILL, ev, confidence=conf),
                    rate_fig=figs.add("0.00", "INR", Role.UNIT_RATE, Origin.BILL, ev, confidence=conf),
                    amount_fig=figs.add("52000.00", "INR", Role.BILLED_AMOUNT, Origin.BILL, ev, confidence=conf))
    return Bill(id="b", lines=[line]), figs


def test_confident_misread_from_a_photo_is_asked_not_accused():
    bill, figs = _bill(0.99)            # OCR was sure, and wrong: a stain read as 0.00
    validate(bill, figs)
    assert "photo_arith_unverified" in bill.lines[0].flags
    assert needs_confirmation(bill) == ["L1"]


def test_exact_text_mismatch_stands_as_read():
    bill, figs = _bill(1.0)             # PDF text layer or typed: the mismatch is what the bill says
    validate(bill, figs)
    assert "arith_mismatch" in bill.lines[0].flags
    assert needs_confirmation(bill) == []


def test_stained_photo_gives_no_red_until_confirmed():
    a = Auditor()
    s = a.audit_files([str(ROOT / "tests/fixtures/demo/bill3_stained_photo.jpg")], {"payer": "cash", "state": "karnataka"})
    assert "L2" in a.view(s, "en")["needs_confirmation"]
    reds = [f for f in s.result.findings if f.verdict.value == "red" and f.line_id == "L2"]
    assert reds == []
    s = a.confirm(s.id, {"L2": {"rate": "52000.00"}}, [l for l in a.view(s, "en")["needs_confirmation"] if l != "L2"])
    assert a.view(s, "en")["needs_confirmation"] == []


def test_proof_card_json_and_english_fallback_without_shaping(monkeypatch):
    c = TestClient(app)
    sid = c.post("/api/samples/bill1").json()["id"]
    d = c.get(f"/api/audit/{sid}/proof-card.json?lang=te").json()
    assert d["excess"] == "₹16,854.67" and d["qr"].startswith("data:image/png;base64,")
    assert d["rows"][1]["sub"] == "₹39,186.03 + 5% GST"
    monkeypatch.setattr(proofcard, "can_shape", lambda: False)
    a = Auditor()
    case = json.loads((ROOT / "tests/fixtures/sample_bills/bill1_cardiac_cash.json").read_text(encoding="utf-8"))
    s = a.audit_structured(case["bill"], case["answers"])
    assert proofcard.render(a, s, "hi")[:8] == b"\x89PNG\r\n\x1a\n"


def test_coffee_stained_photo_of_bill1_matches_the_pdf_once_confirmed():
    """tests/fixtures/demo/bill1_stained_photo.jpg: bill 1 photographed with a coffee stain over
    the stent amounts (made by scripts/stain_photo.py). Run-together OCR words are split, so
    both stents still match their caps; the photo's arithmetic mismatch is asked about first."""
    from decimal import Decimal
    a = Auditor()
    s = a.audit_files([str(ROOT / "tests/fixtures/demo/bill1_stained_photo.jpg")], {"payer": "cash", "state": "karnataka"})
    v = a.view(s, "en")
    stents = [l for l in v["lines"] if "Stent" in l["description"]]
    assert len(stents) == 2 and all(l["verdict"] == "red" for l in stents)
    gw = next(l for l in s.bill.lines if "Guide Wire" in l.description)
    assert v["needs_confirmation"] == [gw.id]
    assert s.figs.value(v["recoverable_fig"]) == Decimal("19969.34")      # the held ₹500 is not counted yet
    assert not any("Advance" in l["description"] for l in v["lines"])
    s = a.confirm(s.id, {}, [gw.id])
    v = a.view(s, "en")
    assert s.figs.value(v["recoverable_fig"]) == Decimal("20469.34")      # same as the PDF
    assert s.figs.value(v["schemes"]["best_fig"]) == Decimal("180785.00")  # same as the PDF
