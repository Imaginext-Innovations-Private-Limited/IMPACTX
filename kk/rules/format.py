"""Bill format (IS 19493:2025, voluntary) and the right to an itemised bill."""

from __future__ import annotations

from ..kb import Rule
from ..models import Evidence, Finding, Origin, Role, Verdict
from .base import RC, make

PRODUCT_SECTIONS = {"pharmacy", "consumables", "implant"}


def missing_elements(rc: RC, rule: Rule) -> list[Finding]:
    missing_qty_rate, missing_batch = [], []
    for line in rc.bill.lines:
        if line.qty_fig is None or line.rate_fig is None:
            missing_qty_rate.append(line)
        if line.section in PRODUCT_SECTIONS and not (line.batch and line.expiry):
            missing_batch.append(line)
    out = []
    for key, lines in (("fmt_missing_qty_rate", missing_qty_rate), ("fmt_missing_batch_expiry", missing_batch)):
        if lines:
            cnt = rc.figs.add(len(lines), "count", Role.COUNT, Origin.COMPUTED,
                              Evidence(formula="count of lines", note=",".join(l.id for l in lines)), money=False)
            out.append(make(rule, Verdict.AMBER, key, None, {"count": cnt},
                            {"lines": ", ".join(l.id for l in lines)}))
    return out


def not_itemised(rc: RC, rule: Rule) -> list[Finding]:
    if rc.bill.itemised:
        return []
    return [make(rule, Verdict.AMBER, "rgt_itemised", None, asks=["ask_itemised_bill"])]
