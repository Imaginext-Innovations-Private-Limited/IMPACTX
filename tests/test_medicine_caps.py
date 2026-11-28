"""Scheduled-medicine ceilings from NPPA S.O. 1581(E), loaded through the import / review step.

The staged rows are real official ceilings; the bill using them is a constructed test bill.
"""

import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from kk.compose.verifier import verify
from kk.extraction.ocr import cross_check_digits
from kk.kb import KnowledgeBase
from kk.kb.importers import approve
from kk.models import BBox, Verdict, Word
from kk.service import Auditor

ROOT = Path(__file__).resolve().parents[1]
STAGED = ROOT / "data" / "staged" / "nppa_so1581_2026_scheduled.csv"
CASE = json.loads((ROOT / "tests/fixtures/medicine_bill/medicines_cash.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def approved_kb(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    shutil.copytree(ROOT / "data", d, dirs_exist_ok=True)
    kb = KnowledgeBase(d)
    assert not next(r for r in kb.readiness()["rules"] if r["rule"] == "PRC-SCHED")["ready"]
    n = approve(d / "staged" / STAGED.name, "nppa_scheduled_ceilings", "test reviewer", kb)
    assert n == 20
    return KnowledgeBase(d)


def test_shipped_table_is_empty_and_readiness_says_so():
    kb = KnowledgeBase()
    rd = kb.readiness()
    sched = next(r for r in rd["rules"] if r["rule"] == "PRC-SCHED")
    assert not sched["ready"] and sched["missing"] == ["nppa_scheduled_ceilings"]
    assert STAGED.name in rd["staged_awaiting_review"]
    # the PM-JAY rules do not depend on the HBP table
    assert all(r["ready"] for r in rd["rules"] if r["rule"].startswith("ENT-"))


def test_approval_makes_the_rule_ready_and_logs_the_reviewer(approved_kb):
    sched = next(r for r in approved_kb.readiness()["rules"] if r["rule"] == "PRC-SCHED")
    assert sched["ready"] and sched["needs"]["nppa_scheduled_ceilings"] == 20
    log = (approved_kb.dir / "review_log.csv").read_text(encoding="utf-8")
    assert "test reviewer" in log and STAGED.name in log


def test_medicine_bill_hand_worked(approved_kb):
    s = Auditor(approved_kb).audit_structured(CASE["bill"], CASE["answers"])
    figs, lines = s.figs, {l.id: l for l in s.bill.lines}
    reds = [f for f in s.result.findings if f.rule_id == "PRC-SCHED" and f.verdict == Verdict.RED]
    got = {lines[f.line_id].description: figs.value(f.excess_fig) for f in reds}
    for key, ex in CASE["expected"]["excess"].items():
        [v] = [v for d, v in got.items() if key.lower() in d.lower()]
        assert v == Decimal(ex), key
    assert len(reds) == 4
    assert figs.value(s.result.recoverable_fig) == Decimal(CASE["expected"]["recoverable"])
    # pack not stated -> highest ceiling, and the finding says so
    [ns] = [f for f in reds if "Normal Saline" in lines[f.line_id].description]
    assert "cond_pack_assumed_highest" in ns.conditions
    # every allowed amount carries the official GST wording
    allowed = [figs.get(f.slots["allowed"]) for f in reds]
    assert all("exclusive of Goods and Services Tax" in (a.evidence.note or "") for a in allowed)
    # tablets are not matched to the capsule row; unlisted medicines are not checked
    flagged = {lines[f.line_id].description for f in s.result.findings if f.rule_id == "PRC-SCHED"}
    assert not any("Diclofenac" in d or "Pantoprazole" in d for d in flagged)


def test_units_not_confirmed_gives_questions_not_accusations(approved_kb):
    answers = dict(CASE["answers"], medicine_qty_in_dosage_units=None)
    s = Auditor(approved_kb).audit_structured(CASE["bill"], answers)
    sched = [f for f in s.result.findings if f.rule_id == "PRC-SCHED"]
    assert sched and all(f.verdict == Verdict.GREY for f in sched)


@pytest.mark.parametrize("lang,bad", [
    ("ta", "நீங்கள் ௫௦௦ ரூபாய் திரும்பப் பெறலாம்."),        # Tamil digits
    ("ta", "நீங்கள் ஐந்து ஆயிரம் ரூபாய் பெறலாம்."),          # Tamil number words
    ("te", "మీరు ౫౦౦ రూపాయలు తిరిగి పొందవచ్చు."),           # Telugu digits
    ("te", "మీరు ఐదు వేలు రూపాయలు పొందవచ్చు."),            # Telugu number words
    ("ta", "நீங்கள் 500 பெறலாம்."), ("te", "మీరు ₹500 పొందవచ్చు."),
])
def test_verifier_rejects_numbers_in_tamil_and_telugu(lang, bad):
    assert not verify(bad, {}, lang).ok


def test_ocr_engines_disagreeing_lowers_confidence():
    box = BBox(page=1, x0=10, y0=10, x1=60, y1=20)
    a = [Word(id="w0", text="58000.00", bbox=box, conf=0.99)]
    same = cross_check_digits(a, [Word(id="s0", text="58000.00", bbox=box, conf=0.9)])
    differ = cross_check_digits(a, [Word(id="s0", text="38000.00", bbox=box, conf=0.9)])
    assert same[0].conf >= 0.95 and differ[0].conf <= 0.5
