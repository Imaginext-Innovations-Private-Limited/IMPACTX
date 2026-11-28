"""Run the rule registry over a bill and aggregate without double counting."""

from __future__ import annotations

from decimal import Decimal

from ..figures import FigureStore
from ..kb import KnowledgeBase
from ..models import AuditResult, Bill, Context, Finding, Role, Verdict
from ..money import q
from . import arithmetic, convention, entitlement, format, price, state, tax
from .base import RC

CHECKS = {
    "price.stent": price.stent,
    "price.knee": price.knee,
    "price.scheduled_medicine": price.scheduled_medicine,
    "price.mrp": price.mrp,
    "entitlement.covered_items": entitlement.covered_items,
    "entitlement.cash_denial": entitlement.cash_denial,
    "arithmetic.qty_rate": arithmetic.qty_rate,
    "arithmetic.total": arithmetic.total,
    "convention.duplicates": convention.duplicates,
    "convention.room_days": convention.room_days,
    "convention.outside_stay": convention.outside_stay,
    "format.missing_elements": format.missing_elements,
    "format.not_itemised": format.not_itemised,
    "state.karnataka_disclosure": state.karnataka_disclosure,
    "tax.gst": tax.gst,
}

SEVERITY = {Verdict.RED: 4, Verdict.GREY: 3, Verdict.AMBER: 2, Verdict.GREEN: 1, Verdict.INFO: 0}


def run(bill: Bill, ctx: Context, kb: KnowledgeBase, figs: FigureStore, answers: dict | None = None) -> AuditResult:
    rc = RC(kb=kb, bill=bill, ctx=ctx, figs=figs, answers=answers or {})
    findings: list[Finding] = []
    for rule in kb.rules:
        if rule.status == "expired":
            continue
        fn = CHECKS.get(rule.check)
        if fn is None:
            raise KeyError(f"rule {rule.id} names unknown check {rule.check}")
        findings.extend(fn(rc, rule))

    recoverable_id, amber_id = _aggregate(findings, figs)
    hospital_id, scheme_id, fallback_id = _by_remedy(findings, figs, recoverable_id)
    from .crosswalk import build_crosswalk
    xwalk, coverage = build_crosswalk(bill, findings, figs, kb)
    return AuditResult(bill=bill, context=ctx, findings=findings, figures=figs.all(),
                       recoverable_fig=recoverable_id, hospital_fig=hospital_id, scheme_fig=scheme_id,
                       fallback_fig=fallback_id, amber_total_fig=amber_id, crosswalk=xwalk,
                       coverage=coverage, data_versions=kb.versions)


SCHEME_FAMILIES = {"entitlement"}


def _by_remedy(findings: list[Finding], figs: FigureStore, rec_id: str | None):
    """Split the challengeable total by who decides it.

    hospital: lines whose largest red claim is a price cap, MRP or arithmetic error. The hospital
              can correct the bill and refund; NPPA enforces price caps.
    scheme:   lines whose largest red claim is scheme entitlement, or a bill-level cash denial.
              This is a grievance; the State Health Agency decides any reimbursement.
    fallback: for the scheme lines, the price-cap claims that stand even if the grievance fails.
    hospital + scheme = the challengeable total, so nothing is counted twice.
    """
    if rec_id is None:
        return None, None, None
    rec = figs.get(rec_id)
    reds = [f for f in findings if f.verdict == Verdict.RED and f.excess_fig]
    if rec.evidence.formula and rec.evidence.formula.startswith("largest bill-level"):
        sid = figs.computed(rec.value, "INR", Role.TOTAL, "bill-level scheme claim (cash denial)", [rec_id])
        return None, sid, None
    best: dict[str, Finding] = {}
    for f in reds:
        if f.line_id and (f.line_id not in best or figs.value(f.excess_fig) > figs.value(best[f.line_id].excess_fig)):
            best[f.line_id] = f
    hosp = [f.excess_fig for f in best.values() if f.family not in SCHEME_FAMILIES]
    sch = [f.excess_fig for f in best.values() if f.family in SCHEME_FAMILIES]
    fb = []
    for lid, f in best.items():
        if f.family in SCHEME_FAMILIES:
            alt = [g for g in reds if g.line_id == lid and g.family not in SCHEME_FAMILIES]
            if alt:
                fb.append(max(alt, key=lambda g: figs.value(g.excess_fig)).excess_fig)

    def total(ids, formula):
        if not ids:
            return None
        ids = sorted(ids, key=lambda i: int(i[1:]))
        return figs.computed(q(sum((figs.value(i) for i in ids), Decimal(0))), "INR", Role.TOTAL, formula, ids)

    return (total(hosp, "sum of price-cap, MRP and arithmetic claims (largest claim per line)"),
            total(sch, "sum of scheme-entitlement claims (largest claim per line)"),
            total(fb, "price-cap claims on the scheme lines, which stand even without the scheme"))


def _aggregate(findings: list[Finding], figs: FigureStore) -> tuple[str | None, str | None]:
    """Recoverable = per line, the largest red claim (never the sum of overlapping claims);
    bill-level red claims (e.g. a beneficiary charged as cash) replace the line sum if larger."""
    per_line: dict[str, str] = {}
    bill_level: list[str] = []
    for f in findings:
        if f.verdict != Verdict.RED or not f.excess_fig:
            continue
        if f.line_id is None:
            bill_level.append(f.excess_fig)
        elif f.line_id not in per_line or figs.value(f.excess_fig) > figs.value(per_line[f.line_id]):
            per_line[f.line_id] = f.excess_fig
    rec_id = None
    if per_line or bill_level:
        line_ids = sorted(per_line.values(), key=lambda i: int(i[1:]))
        line_sum = sum((figs.value(i) for i in line_ids), Decimal(0))
        best_bill = max(bill_level, key=lambda i: figs.value(i), default=None)
        if best_bill is not None and figs.value(best_bill) >= line_sum:
            rec_id = figs.computed(figs.value(best_bill), "INR", Role.TOTAL,
                                   "largest bill-level claim (replaces line claims)", [best_bill])
        else:
            rec_id = figs.computed(q(line_sum), "INR", Role.TOTAL,
                                   "sum over lines of the largest red claim per line", line_ids)
    amber_ids = []
    seen_lines = set(per_line)
    for f in findings:
        if f.verdict == Verdict.AMBER and f.excess_fig and f.line_id not in seen_lines:
            amber_ids.append(f.excess_fig)
            if f.line_id:
                seen_lines.add(f.line_id)
    amber_id = None
    if amber_ids:
        amber_id = figs.computed(q(sum((figs.value(i) for i in amber_ids), Decimal(0))), "INR", Role.TOTAL,
                                 "sum of amber amounts on lines without a red finding", amber_ids)
    return rec_id, amber_id


def line_verdicts(result: AuditResult) -> dict[str, Verdict]:
    out: dict[str, Verdict] = {}
    for f in result.findings:
        if f.line_id and (f.line_id not in out or SEVERITY[f.verdict] > SEVERITY[out[f.line_id]]):
            out[f.line_id] = f.verdict
    for l in result.bill.lines:
        out.setdefault(l.id, Verdict.GREEN)
    return out
