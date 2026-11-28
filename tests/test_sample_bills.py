"""End-to-end checks on the three fictional TEST bills in tests/fixtures/sample_bills/.

Each bill runs twice: from the document (PDF text layer, or OCR for the phone photo) and
from the typed-in version. Both must give exactly the hand-worked expected results.
These fixtures test the code; they are never reported as real-world accuracy.
"""

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from kk.models import Verdict

FIX = Path(__file__).parent / "fixtures" / "sample_bills"
CASES = sorted(FIX.glob("bill*.json"))


def _check(session, expected):
    r = session.result
    figs = session.figs
    lines = {l.id: l for l in session.bill.lines}
    problems = []
    for exp in expected["findings"]:
        cands = [f for f in r.findings if f.rule_id == exp["rule_id"] and f.verdict == Verdict(exp["verdict"])]
        if "match" in exp:
            cands = [f for f in cands if f.line_id and re.search(exp["match"], lines[f.line_id].description, re.I)]
        if "excess" in exp:
            cands = [f for f in cands if f.excess_fig and figs.value(f.excess_fig) == Decimal(exp["excess"])]
        if not cands:
            problems.append(f"missing {exp}")
    for rid in expected.get("not_expected", []):
        hits = [f for f in r.findings if f.rule_id == rid]
        if hits:
            problems.append(f"unexpected {rid}: {[(f.verdict.value, f.message_key) for f in hits]}")
    rec = figs.value(r.recoverable_fig) if r.recoverable_fig else None
    if (Decimal(expected["recoverable"]) if expected["recoverable"] else None) != rec:
        problems.append(f"recoverable {rec} != {expected['recoverable']}")
    amb = figs.value(r.amber_total_fig) if r.amber_total_fig else None
    if (Decimal(expected["amber_total"]) if expected["amber_total"] else None) != amb:
        problems.append(f"amber total {amb} != {expected['amber_total']}")
    return problems


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_typed_in_version(case, auditor):
    info = json.loads(case.read_text())
    s = auditor.audit_structured(info["bill"], info["answers"])
    assert _check(s, info["expected"]) == []


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_document_version(case, auditor):
    info = json.loads(case.read_text())
    s = auditor.audit_files([str(FIX / info["file"])], info["answers"])
    # a photo may have hard-to-read digits: accept them as read, the way a user would after checking
    if s.result and any(l.flags for l in s.bill.lines):
        s = auditor.confirm(s.id, {}, [l.id for l in s.bill.lines if "low_ocr_confidence" in l.flags
                                       or "ambiguous_columns" in l.flags])
    assert _check(s, info["expected"]) == []
