"""Billing-convention checks. Always amber: worth a question, never an accusation."""

from __future__ import annotations

import re
from collections import defaultdict
from decimal import Decimal

from ..kb import Rule
from ..models import Evidence, Finding, Origin, Role, Verdict
from .base import RC, make

ROOM = re.compile(r"(?i)\b(room|bed|ward|icu|iccu|nicu|hdu|accommodation)\b")


def duplicates(rc: RC, rule: Rule) -> list[Finding]:
    figs = rc.figs
    groups: dict[tuple, list] = defaultdict(list)
    for line in rc.bill.lines:
        key = (re.sub(r"\W+", " ", line.description.lower()).strip(), figs.value(line.amount_fig),
               line.item_date, line.batch)
        groups[key].append(line)
    out = []
    for (desc, amt, _d, _b), lines in groups.items():
        if len(lines) > 1 and amt is not None:
            for dup in lines[1:]:
                out.append(make(rule, Verdict.AMBER, "conv_duplicate", dup, {"billed": dup.amount_fig},
                                {"item": dup.description, "first_line": lines[0].id}, excess_fig=dup.amount_fig))
    return out


def room_days(rc: RC, rule: Rule) -> list[Finding]:
    h, figs = rc.bill.header, rc.figs
    if not (h.admission_date and h.discharge_date):
        return []
    nights = (h.discharge_date - h.admission_date).days
    room_lines = [l for l in rc.bill.lines if (l.section == "room" or ROOM.search(l.description)) and l.qty_fig]
    if not room_lines:
        return []
    days = sum((figs.value(l.qty_fig) for l in room_lines), Decimal(0))
    # many hospitals count both the admission and discharge day, so nights + 1 is normal
    if days > nights + 1:
        days_id = figs.computed(days, "days", Role.DAYS, "sum of room-line quantities",
                                [l.qty_fig for l in room_lines])
        nights_id = figs.add(nights, "days", Role.NIGHTS, Origin.COMPUTED,
                             Evidence(formula="discharge date − admission date",
                                      note=f"{h.admission_date.isoformat()} to {h.discharge_date.isoformat()}"),
                             money=False)
        return [make(rule, Verdict.AMBER, "conv_roomdays", room_lines[0], {"days": days_id, "nights": nights_id})]
    return []


def outside_stay(rc: RC, rule: Rule) -> list[Finding]:
    h = rc.bill.header
    if not (h.admission_date and h.discharge_date):
        return []
    out = []
    for line in rc.bill.lines:
        if line.item_date and not (h.admission_date <= line.item_date <= h.discharge_date):
            out.append(make(rule, Verdict.AMBER, "conv_outside_stay", line, {},
                            {"item": line.description, "date": line.item_date.isoformat()}))
    return out
