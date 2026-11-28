"""Line-to-rule crosswalk and coverage: what each bill line was matched to, and why.

The crosswalk is the honest answer to "which lines were really checked?". A line is
  rule     matched to an official price limit (NPPA ceiling or printed MRP) or a scheme rule
  pending  matched, but cannot be decided yet (unclear digits, no rule data for the date ...)
  basic    no official limit applies or none is loaded; only arithmetic, duplicates, dates
Every reason is a message key with text slots, rendered in the user's language. Counts and the
share of the bill amount are computed figures, like every other number.
"""

from __future__ import annotations

from decimal import Decimal

from ..figures import FigureStore
from ..models import Bill, Finding, Role, Verdict
from ..money import q
from .classify import knee_candidates, knee_match_text, stent_match

PRICE_RULES = {"PRC-STENT", "PRC-KNEE", "PRC-SCHED", "PRC-MRP"}
SCHEME_RULES = {"ENT-COVERED"}


def _row_of(f: Finding, figs: FigureStore) -> tuple[str | None, str | None]:
    for key in ("ceiling", "mrp"):
        fid = f.slots.get(key)
        if fid and fid in figs:
            ev = figs.get(fid).evidence
            return ev.rule_row, ev.source_id
    return None, None


def build_crosswalk(bill: Bill, findings: list[Finding], figs: FigureStore, kb) -> tuple[dict, dict]:
    by_line: dict[str, list[Finding]] = {}
    for f in findings:
        if f.line_id:
            by_line.setdefault(f.line_id, []).append(f)
    cash_denial = next((f for f in findings if f.rule_id == "ENT-CASH-DENIAL" and f.verdict == Verdict.RED), None)
    out: dict[str, dict] = {}
    for line in bill.lines:
        fs = by_line.get(line.id, [])
        matches = []
        if cash_denial is not None:   # a bill-level scheme rule covers every line
            matches.append({"rule_id": cash_denial.rule_id, "row_id": None, "source_id": None, "verdict": "red",
                            "reason": "match_cash_denial", "text": {}})
        for f in fs:
            if f.rule_id not in PRICE_RULES | SCHEME_RULES:
                continue
            row, src = _row_of(f, figs)
            m = {"rule_id": f.rule_id, "row_id": row, "source_id": src, "verdict": f.verdict.value}
            if f.rule_id == "PRC-STENT":
                sm = stent_match(line.description, kb) or {}
                m["reason"] = {"stent_brand": "match_stent_brand", "stent_word": "match_stent_word"}.get(
                    "stent_" + sm.get("how", ""), "match_stent_type")
                m["text"] = {"matched": sm.get("matched", ""), "label": sm.get("brand_label", "")}
            elif f.rule_id == "PRC-KNEE":
                m["reason"], m["text"] = "match_knee", {"matched": knee_match_text(line.description) or ""}
            elif f.rule_id == "PRC-SCHED":
                r = next((x for x in kb.tables["nppa_scheduled_ceilings"] if x.id == row), None)
                m["reason"], m["text"] = "match_sched", {"matched": r.data["formulation"] if r else ""}
            elif f.rule_id == "PRC-MRP":
                m["reason"], m["text"] = "match_mrp", {}
            else:
                m["reason"], m["text"] = "match_scheme", {}
            matches.append(m)
        decided = [m for m in matches if m["verdict"] in ("red", "green", "amber")]
        if decided:
            status = "rule"
        elif matches:
            status = "pending"
        else:
            status = "basic"
        basic = ["dup"]
        if line.qty_fig and line.rate_fig:
            basic.append("arith")
        if line.item_date:
            basic.append("date")
        if line.section == "room":
            basic.append("room_days")
        reason = None
        if status == "basic":
            if stent_match(line.description, kb) or knee_candidates(line.description):
                reason = "nomatch_unread"
            elif line.section == "pharmacy":
                reason = "nomatch_medicine"
            elif line.section == "room":
                reason = "nomatch_room"
            else:
                reason = "nomatch_generic"
        elif status == "pending":
            reason = "nomatch_pending"
        out[line.id] = {"status": status, "matches": matches, "basic_checks": basic, "reason": reason}

    def count(status: str, formula: str):
        ids = [l.id for l in bill.lines if out[l.id]["status"] == status]
        inputs = [l.amount_fig for l in bill.lines if out[l.id]["status"] == status and l.amount_fig]
        return figs.computed(Decimal(len(ids)), "count", Role.COUNT, formula, inputs)

    cov = {
        "lines": figs.computed(Decimal(len(bill.lines)), "count", Role.COUNT, "number of bill lines",
                               [l.amount_fig for l in bill.lines if l.amount_fig]),
        "rule": count("rule", "lines matched to a price limit or scheme rule"),
        "pending": count("pending", "lines matched but not yet decidable"),
        "basic": count("basic", "lines with only arithmetic, duplicate and date checks"),
    }
    amounts = [(l, figs.value(l.amount_fig)) for l in bill.lines if l.amount_fig and figs.value(l.amount_fig)]
    total = sum((v for _, v in amounts), Decimal(0))
    if total > 0:
        ruled = [l.amount_fig for l, _ in amounts if out[l.id]["status"] == "rule"]
        share = q(sum((figs.value(i) for i in ruled), Decimal(0)) * 100 / total)
        cov["share"] = figs.computed(share, "percent", Role.BENCHMARK,
                                     "amount on rule-matched lines ÷ amount on all lines × 100",
                                     ruled + [l.amount_fig for l, _ in amounts if l.amount_fig not in ruled])
    return out, cov
