"""Arithmetic and confidence checks on extracted lines.

A line whose numbers are low-confidence is flagged for the user unless its
arithmetic agrees (quantity x rate = amount), which is strong evidence that
every digit was read correctly.

A line read from a photo whose arithmetic does NOT agree is also flagged, however
confident the OCR engine was: a single misread digit (a stain read as "0.00") must
never become an accusation. The family confirms the numbers first; only then can an
arithmetic or price rule turn red. Text from a PDF's text layer (confidence 1.0) and
typed bills are exact, so their mismatches stand as read.
"""

from __future__ import annotations

from decimal import Decimal

from ..figures import FigureStore
from ..models import Bill

TOLERANCE = Decimal("1.00")   # rupee rounding on printed bills
LOW_CONF = 0.85
CONFIRM_FLAGS = ("low_ocr_confidence", "ambiguous_columns", "photo_arith_unverified")


def arithmetic_ok(bill_line, figs: FigureStore) -> bool | None:
    qty, rate, amt = (figs.value(bill_line.qty_fig), figs.value(bill_line.rate_fig),
                      figs.value(bill_line.amount_fig))
    if qty is None or rate is None or amt is None:
        return None
    base = qty * rate
    if abs(base - amt) <= TOLERANCE:
        return True
    gst_amt = figs.value(bill_line.gst_amount_fig)
    if gst_amt is not None and abs(base + gst_amt - amt) <= TOLERANCE:
        return True
    gst_rate = figs.value(bill_line.gst_rate_fig)
    if gst_rate is not None and abs(base * (1 + gst_rate / 100) - amt) <= TOLERANCE:
        return True
    return False


def validate(bill: Bill, figs: FigureStore) -> Bill:
    for line in bill.lines:
        ids = [f for f in (line.qty_fig, line.rate_fig, line.amount_fig, line.mrp_fig,
                           line.gst_rate_fig, line.gst_amount_fig) if f]
        conf = min((figs.get(f).confidence for f in ids), default=1.0)
        ok = arithmetic_ok(line, figs)
        if ok is False and "arith_mismatch" not in line.flags:
            line.flags.append("arith_mismatch")
        if conf < LOW_CONF and ok is not True and "low_ocr_confidence" not in line.flags:
            line.flags.append("low_ocr_confidence")
        if ok is False and conf < 1.0 and "photo_arith_unverified" not in line.flags:
            line.flags.append("photo_arith_unverified")
    return bill


def needs_confirmation(bill: Bill) -> list[str]:
    """Line ids the user must confirm before rules that use their numbers can give a verdict."""
    return [l.id for l in bill.lines if not l.confirmed and any(f in l.flags for f in CONFIRM_FLAGS)]
