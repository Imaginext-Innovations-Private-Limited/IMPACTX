"""Arithmetic checks that can be proven from the bill itself."""

from __future__ import annotations

from decimal import Decimal

from ..kb import Rule
from ..models import Finding, Role, Verdict
from ..money import q
from .base import RC, grey, make

TOL = Decimal("1.00")
STANDARD_GST = (Decimal(5), Decimal(12), Decimal(18), Decimal(28))   # rates a line total may silently include


def qty_rate(rc: RC, rule: Rule) -> list[Finding]:
    figs = rc.figs
    out: list[Finding] = []
    for line in rc.bill.lines:
        qty, rate, amt = figs.value(line.qty_fig), figs.value(line.rate_fig), figs.value(line.amount_fig)
        if qty is None or rate is None or amt is None:
            continue
        if rc.line_needs_confirmation(line):
            if "arith_mismatch" in line.flags:
                # a misread digit must not become an accusation: ask the user first
                out.append(grey(rule, "confirm_line", line, {"item": line.description}))
            continue
        inputs = [line.qty_fig, line.rate_fig]
        expected = qty * rate
        formula = "quantity × rate"
        gst_amt, gst_rate = figs.value(line.gst_amount_fig), figs.value(line.gst_rate_fig)
        if gst_amt is not None and abs(expected + gst_amt - amt) <= abs(expected - amt):
            expected += gst_amt
            inputs.append(line.gst_amount_fig)
            formula = "quantity × rate + GST amount"
        elif gst_rate is not None and abs(expected * (1 + gst_rate / 100) - amt) < abs(expected - amt):
            expected = expected * (1 + gst_rate / 100)
            inputs.append(line.gst_rate_fig)
            formula = "quantity × rate × (1 + GST rate ÷ 100)"
        if amt - expected > TOL and len(inputs) == 2:
            # Real bills often print the rate before tax and the amount after it, with no GST column.
            # If the gap is exactly a standard GST rate, it is a question to ask, not a proven overcharge.
            for g in STANDARD_GST:
                if abs(amt - expected * (1 + g / 100)) <= max(TOL, amt * Decimal("0.002")):
                    exp_id = figs.computed(q(expected), "INR", Role.EXPECTED_AMOUNT, formula, inputs)
                    ex_id = figs.computed(q(amt - expected), "INR", Role.EXCESS, "billed − expected",
                                          [line.amount_fig, exp_id])
                    out.append(make(rule, Verdict.AMBER, "ari_qtyrate_tax", line,
                                    {"qty": line.qty_fig, "rate": line.rate_fig, "expected": exp_id,
                                     "billed": line.amount_fig}, {"item": line.description}, excess_fig=ex_id))
                    break
            else:
                g = None
            if g is not None and out and out[-1].message_key == "ari_qtyrate_tax" and out[-1].line_id == line.id:
                continue
        if amt - expected > TOL:
            exp_id = figs.computed(q(expected), "INR", Role.EXPECTED_AMOUNT, formula, inputs)
            ex_id = figs.computed(q(amt - expected), "INR", Role.EXCESS, "billed − expected",
                                  [line.amount_fig, exp_id])
            out.append(make(rule, Verdict.RED, "ari_qtyrate", line,
                            {"qty": line.qty_fig, "rate": line.rate_fig, "expected": exp_id,
                             "billed": line.amount_fig, "excess": ex_id},
                            {"item": line.description}, excess_fig=ex_id))
    return out


def total(rc: RC, rule: Rule) -> list[Finding]:
    figs, bill = rc.figs, rc.bill
    if bill.header.total_fig is None or not bill.lines:
        return []
    ids = [l.amount_fig for l in bill.lines if l.amount_fig]
    s = sum((figs.value(i) for i in ids), Decimal(0))
    printed = figs.value(bill.header.total_fig)
    if printed - s > TOL:
        sum_id = figs.computed(q(s), "INR", Role.EXPECTED_AMOUNT, "sum of line amounts", ids)
        diff_id = figs.computed(q(printed - s), "INR", Role.EXCESS, "printed total − sum of lines",
                                [bill.header.total_fig, sum_id])
        return [make(rule, Verdict.AMBER, "ari_total", None,
                     {"total": bill.header.total_fig, "expected": sum_id, "excess": diff_id}, excess_fig=diff_id)]
    return []
