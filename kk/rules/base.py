"""Shared helpers for rule checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from ..figures import FigureStore
from ..kb import KnowledgeBase, Rule
from ..models import Bill, BillLine, Channel, Context, Finding, Verdict

PAISE_TOLERANCE = Decimal("0.50")


@dataclass
class RC:
    """Everything a rule check may read."""
    kb: KnowledgeBase
    bill: Bill
    ctx: Context
    figs: FigureStore
    answers: dict = field(default_factory=dict)

    @property
    def service_date(self) -> date | None:
        return self.ctx.service_date.value if self.ctx.service_date.known else None

    def line_needs_confirmation(self, line: BillLine) -> bool:
        from ..extraction.validate import CONFIRM_FLAGS
        return not line.confirmed and any(f in line.flags for f in CONFIRM_FLAGS)


def make(rule: Rule, verdict: Verdict | str, message_key: str, line: BillLine | None = None,
         slots: dict | None = None, text_slots: dict | None = None, excess_fig: str | None = None,
         conditions: list[str] | None = None, asks: list[str] | None = None) -> Finding:
    return Finding(
        rule_id=rule.id, family=rule.family, verdict=Verdict(verdict),
        line_id=line.id if line else None,
        channel=Channel(rule.channel) if Verdict(verdict) in (Verdict.RED, Verdict.AMBER) else Channel.NONE,
        message_key=message_key, slots=slots or {}, text_slots=text_slots or {},
        excess_fig=excess_fig, legal_status=rule.status, source_ids=list(rule.sources),
        conditions=conditions or [], asks=asks or [])


def grey(rule: Rule, reason: str, line: BillLine | None = None, text_slots: dict | None = None,
         asks: list[str] | None = None) -> Finding:
    return make(rule, Verdict.GREY, f"grey_{reason}", line, text_slots=text_slots or {},
                asks=asks or [f"ask_{reason}"])


def billed_total(line: BillLine, figs: FigureStore) -> tuple[Decimal | None, list[str], str]:
    """Amount the patient was charged for a line, including GST.

    Returns (value, input figure ids, formula). If the printed amount already includes GST
    (qty x rate + gst = amount), the amount is used; if GST is printed separately and the
    amount excludes it, GST is added.
    """
    amt = figs.value(line.amount_fig)
    if amt is None:
        return None, [], ""
    qty, rate, gst = figs.value(line.qty_fig), figs.value(line.rate_fig), figs.value(line.gst_amount_fig)
    if gst is not None and qty is not None and rate is not None:
        if abs(qty * rate - amt) <= Decimal("1") and abs(qty * rate + gst - amt) > Decimal("1"):
            return amt + gst, [line.amount_fig, line.gst_amount_fig], "amount + GST amount"
    return amt, [line.amount_fig], "amount as printed"
