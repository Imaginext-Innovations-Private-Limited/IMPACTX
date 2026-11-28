"""Scheme entitlement rules (PM-JAY and state schemes built on it).

Source: NHA Adhikar Patra - free medicines, drugs, implants and food during treatment;
up to 3 days pre- and 15 days post-hospitalisation diagnostics and medicines; general ward.
HBP 2022 packages are bundled and all-inclusive except mapped implant cost (also paid by the scheme).
"""

from __future__ import annotations

import re
from datetime import timedelta
from decimal import Decimal

from ..context import is_scheme_payer
from ..kb import Rule
from ..models import Finding, Role, Verdict
from ..money import q
from .base import RC, billed_total, grey, make

PRE_DAYS, POST_DAYS = 3, 15
UPGRADE = re.compile(r"(?i)\b(private|deluxe|suite|single|semi[\s\-]*private|twin\s*sharing)\b.*\b(room|ward|bed)\b|"
                     r"\broom\s+upgrade\b")
NON_MEDICAL = re.compile(r"(?i)\b(attendant|visitor|telephone|toiletr\w*|personal|tv|television|laundry|"
                         r"courier|photocop\w*|parking)\b")


def _scheme_preconditions(rc: RC, rule: Rule) -> list[Finding] | None:
    """Returns findings that stop the rule (grey or not-applicable), or None to continue."""
    scheme = is_scheme_payer(rc.ctx)
    if scheme is None:
        return [grey(rule, "need_payer")]
    if not scheme:
        return []
    emp = rc.ctx.hospital_empanelled_on_service_date
    if not emp.known:
        return [grey(rule, "need_empanelment")]
    if emp.value is False:
        return [make(rule, Verdict.INFO, "ent_not_empanelled", None)]
    return None


def covered_items(rc: RC, rule: Rule) -> list[Finding]:
    stop = _scheme_preconditions(rc, rule)
    if stop is not None:
        return stop
    if not rc.ctx.scheme_booked.known:
        return [grey(rule, "need_scheme_booking")]
    if rc.ctx.scheme_booked.value is False:
        return []   # handled by cash_denial
    paid = rc.answers.get("patient_paid")
    if paid is None:
        return [grey(rule, "need_patient_paid")]
    if not paid:
        return []
    conditions = ["cond_card_status_from_user"]
    if rc.ctx.scheme_limit_exhausted.value is True:
        return [make(rule, Verdict.INFO, "ent_limit_exhausted", None)]
    if not rc.ctx.scheme_limit_exhausted.known:
        conditions.append("cond_limit_not_exhausted")
    h = rc.bill.header
    out: list[Finding] = []
    for line in rc.bill.lines:
        if rc.line_needs_confirmation(line):
            out.append(grey(rule, "confirm_line", line, {"item": line.description}))
            continue
        if line.item_date and h.admission_date and h.discharge_date:
            if not (h.admission_date - timedelta(days=PRE_DAYS) <= line.item_date
                    <= h.discharge_date + timedelta(days=POST_DAYS)):
                continue   # outside the package window: not covered by the scheme
        billed, inputs, formula = billed_total(line, rc.figs)
        if billed is None:
            continue
        bid = inputs[0] if len(inputs) == 1 else rc.figs.computed(billed, "INR", Role.BILLED_AMOUNT, formula, inputs)
        if UPGRADE.search(line.description) or NON_MEDICAL.search(line.description):
            out.append(make(rule, Verdict.AMBER, "ent_maybe_not_covered", line, {"billed": bid},
                            {"item": line.description}))
            continue
        ex = rc.figs.computed(q(billed), "INR", Role.EXCESS, "whole billed amount (covered by package)", [bid])
        out.append(make(rule, Verdict.RED, "ent_covered", line, {"billed": bid, "excess": ex},
                        {"item": line.description}, excess_fig=ex, conditions=conditions))
    return out


def cash_denial(rc: RC, rule: Rule) -> list[Finding]:
    stop = _scheme_preconditions(rc, rule)
    if stop is not None:
        return [f for f in stop if f.verdict != Verdict.GREY]   # covered_items already asks
    if rc.ctx.scheme_booked.value is not False:
        return []
    figs = rc.figs
    total_id = rc.bill.header.total_fig
    if total_id is None:
        ids = [l.amount_fig for l in rc.bill.lines if l.amount_fig]
        if not ids:
            return [make(rule, Verdict.RED, "ent_cash_denial", None, conditions=["cond_card_status_from_user"])]
        total_id = figs.computed(q(sum((figs.value(i) for i in ids), Decimal(0))), "INR", Role.TOTAL,
                                 "sum of line amounts", ids)
    ex = figs.computed(figs.value(total_id), "INR", Role.EXCESS, "amount charged to a scheme beneficiary", [total_id])
    return [make(rule, Verdict.RED, "ent_cash_denial", None, {"total": total_id, "excess": ex},
                 excess_fig=ex, conditions=["cond_card_status_from_user"])]
