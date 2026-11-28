"""TEST BILL 4: handwritten nursing-home bill for a caesarean delivery, photographed.

Made by tests/fixtures/handwritten/make_handwritten.py (fictional, stamped TEST BILL).
Checks that a handwritten photo is read line by line, that no line is silently lost or glued
to another, that every repaired or unreadable number is asked about before any rule uses it,
and that once the family confirms, the results match the hand-worked figures.
"""

import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from kk.extraction.ocr import fix_lookalikes
from kk.kb import KnowledgeBase
from kk.kb.importers import approve
from kk.models import BBox, Word
from kk.service import Auditor

ROOT = Path(__file__).resolve().parents[1]
BILL = ROOT / "tests/fixtures/handwritten/bill4_csection_handwritten.jpg"
CASE = json.loads(BILL.with_suffix(".json").read_text(encoding="utf-8"))
ANSWERS = {**CASE["answers"], "medicine_qty_in_dosage_units": True}


def _w(t):
    return Word(id="w0", text=t, conf=0.95, bbox=BBox(page=1, x0=0, y0=0, x1=10, y1=10))


def test_lookalike_digits_are_repaired_and_marked_doubtful():
    for raw, want in [("2S,000/-", "25,000/-"), ("I,S00", "1,500"), ("6,0001", "6,000/-"), ("8.000", "8,000"),
                      ("2,S0o/-", "2,500/-"), ("so0ml", "500ml"), ("Somg", "50mg"), ("lg", "1g"),
                      ("25,0001-", "25,000/-"), ("9001-", "900/-"), ("54,7801-", "54,780/-")]:  # RapidOCR 1.4
        w = fix_lookalikes([_w(raw)])[0]
        assert w.text == want, raw
        if not want.endswith(("ml", "mg", "g")):
            assert w.conf <= 0.6           # a repaired amount is always asked about
    for keep in ("Sutures", "LSCS", "Ceftriaxone", "720/-", "Inj"):
        assert fix_lookalikes([_w(keep)])[0].text == keep


def _confirm_all(a, s):
    """What a careful family does at the confirm step: look at each doubtful line's crop, type
    what the handwriting does not show, fix any digit the reader got wrong, and accept the rest.

    Misreads differ between OCR versions (RapidOCR 1.2 reads Ceftriaxone's rate as 85, 1.4 as
    "S8"), so the true values come from the bill as written (the fixture JSON), never from a guess.
    """
    import difflib
    truth = CASE["bill"]["lines"]
    assert len(s.bill.lines) == len(truth)
    ids = {l.description: l.id for l in s.bill.lines}
    lid = lambda k: next(v for d, v in ids.items() if k in d)
    v = a.view(s, "en")
    # where the handwriting was not read at all
    corr = {lid("Nursing"): {"qty": "3", "rate": "500", "amount": "1500"},
            lid("Diclofenac"): {"qty": "10", "rate": "5", "amount": "50"},
            lid("Room"): {"qty": "5"}}
    # where a digit was misread: the family corrects it from the photo
    for line, real in zip(s.bill.lines, truth):
        assert difflib.SequenceMatcher(None, line.description.lower()[:12],
                                       real["description"].lower()[:12]).ratio() > 0.5, (line.description, real)
        if line.id not in v["needs_confirmation"]:
            continue
        for k, fid in (("qty", line.qty_fig), ("rate", line.rate_fig), ("amount", line.amount_fig)):
            if fid is not None and real.get(k) is not None and s.figs.value(fid) != Decimal(real[k]):
                corr.setdefault(line.id, {})[k] = real[k]
    return a.confirm(s.id, corr, v["needs_confirmation"])


def test_every_handwritten_line_is_read_or_asked_about():
    a = Auditor()
    s = a.audit_files([str(BILL)], ANSWERS)
    assert len(s.bill.lines) == CASE["expected"]["lines_read"] == len(CASE["bill"]["lines"])
    nursing = next(l for l in s.bill.lines if "Nursing" in l.description)
    assert "amount_unreadable" in nursing.flags and nursing.amount_fig is None
    v = a.view(s, "en")
    assert nursing.id in v["needs_confirmation"]
    # nothing doubtful is called "not allowed" before the family confirms it
    doubtful = set(v["needs_confirmation"])
    assert not any(f["verdict"] == "red" and f.get("line_id") in doubtful for f in v["findings"])


def test_after_confirming_with_shipped_data():
    a = Auditor()
    s = _confirm_all(a, a.audit_files([str(BILL)], ANSWERS))
    v = a.view(s, "en")
    want = CASE["expected"]["recoverable_after_confirming"]["shipped_data"]
    assert s.figs.value(v["recoverable_fig"]) == Decimal(want)        # Ceftriaxone 6 x 85 written as 610
    assert any(f["rule_id"] == "CONV-ROOMDAYS" and f["verdict"] == "amber" for f in v["findings"])
    assert s.figs.value(v["schemes"]["best_fig"]) == Decimal("54780.00")   # the whole bill, once confirmed


@pytest.fixture(scope="module")
def approved_kb(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    shutil.copytree(ROOT / "data", d, dirs_exist_ok=True)
    approve(d / "staged" / "nppa_so1581_2026_scheduled.csv", "nppa_scheduled_ceilings", "test reviewer",
            KnowledgeBase(d))
    return KnowledgeBase(d)


def test_after_confirming_with_nppa_medicine_caps(approved_kb):
    a = Auditor(approved_kb)
    s = _confirm_all(a, a.audit_files([str(BILL)], ANSWERS))
    v = a.view(s, "en")
    exp = CASE["expected"]
    assert s.figs.value(v["recoverable_fig"]) == Decimal(
        exp["recoverable_after_confirming"]["with_nppa_so1581_rows_approved_and_units_confirmed"])
    reds = {f["rule_id"] for f in v["findings"] if f["verdict"] == "red"}
    assert {"PRC-SCHED", "ARI-QTYRATE"} <= reds