"""Price-cap rules: NPPA ceilings (stents, knee implants, scheduled medicines) and MRP."""

from __future__ import annotations

import re
from decimal import Decimal

from ..kb import Row, Rule
from ..models import BillLine, Finding, Role, Verdict
from ..money import q
from .base import PAISE_TOLERANCE, RC, billed_total, grey, make
from .classify import knee_candidates, stent_kind


def _cap_check(rc: RC, rule: Rule, line: BillLine, ceiling_row: Row, gst_category: str,
               item_text: str, msg: str, extra_conditions: list[str] | None = None) -> list[Finding]:
    """Shared ceiling check: billed (incl. GST) vs quantity x ceiling x (1 + GST)."""
    figs, d = rc.figs, rc.service_date
    gst_row = rc.kb.gst_rate(gst_category, d)
    if gst_row is None:
        return [grey(rule, "no_gst_rate_for_date", line, {"item": item_text, "date": d.isoformat()})]
    if line.qty_fig is None:
        return [grey(rule, "need_quantity", line, {"item": item_text})]
    billed, billed_inputs, billed_formula = billed_total(line, figs)
    if billed is None:
        return [grey(rule, "need_amount", line, {"item": item_text})]

    ceil_id = figs.from_rule(ceiling_row.dec("ceiling_ex_gst"), "INR", Role.CEILING_EX_GST, ceiling_row.id,
                             ceiling_row.data["source_id"], ceiling_row.data["source_ref"])
    gst_id = figs.from_rule(gst_row.dec("rate_percent"), "percent", Role.GST_RATE, gst_row.id,
                            gst_row.data["source_id"], gst_row.data["source_ref"])
    if len(billed_inputs) == 1:
        billed_id = billed_inputs[0]
    else:
        billed_id = figs.computed(billed, "INR", Role.BILLED_AMOUNT, billed_formula, billed_inputs)
    qty = figs.value(line.qty_fig)
    allowed = q(qty * figs.value(ceil_id) * (1 + figs.value(gst_id) / Decimal(100)))
    allowed_id = figs.computed(allowed, "INR", Role.ALLOWED_AMOUNT,
                               "quantity × ceiling × (1 + GST rate ÷ 100)", [line.qty_fig, ceil_id, gst_id])
    basis = rc.kb.source_field(ceiling_row.data["source_id"], "tax_quote")
    if basis:   # why GST is added on top of this ceiling, with the official wording
        figs.get(allowed_id).evidence.note = basis
    slots = {"billed": billed_id, "qty": line.qty_fig, "ceiling": ceil_id, "gst": gst_id, "allowed": allowed_id}
    text = {"item": item_text, "valid_from": ceiling_row.valid_from.isoformat()}
    out: list[Finding] = []

    printed_gst = figs.value(line.gst_rate_fig)
    if printed_gst is not None and printed_gst != figs.value(gst_id):
        out.append(make(rule, Verdict.AMBER, "gst_rate_differs", line,
                        slots={"printed_gst": line.gst_rate_fig, "gst": gst_id}, text_slots=text))

    excess = billed - allowed
    if excess > PAISE_TOLERANCE:
        ex_id = figs.computed(q(excess), "INR", Role.EXCESS, "billed − allowed", [billed_id, allowed_id])
        slots["excess"] = ex_id
        out.append(make(rule, Verdict.RED, msg, line, slots, text, excess_fig=ex_id,
                        conditions=extra_conditions))
    else:
        out.append(make(rule, Verdict.GREEN, msg + "_ok", line, slots, text, conditions=extra_conditions))
    return out


def stent(rc: RC, rule: Rule) -> list[Finding]:
    out: list[Finding] = []
    for line in rc.bill.lines:
        kind = stent_kind(line.description, rc.kb)
        if kind is None:
            continue
        if rc.line_needs_confirmation(line):
            out.append(grey(rule, "confirm_line", line, {"item": line.description}))
            continue
        if rc.service_date is None:
            out.append(grey(rule, "need_service_date", line, {"item": line.description}))
            continue
        conditions = []
        if kind == "stent_unknown":
            # type not printed: use the higher (DES) ceiling so the finding can only understate
            kind, conditions = "stent_des", ["cond_stent_type_assumed_des"]
        row = rc.kb.stent_ceiling(kind, rc.service_date)
        if row is None:
            out.append(grey(rule, "no_rule_data_for_date", line,
                            {"item": line.description, "date": rc.service_date.isoformat()}))
            continue
        out.extend(_cap_check(rc, rule, line, row, "medical_device", line.description, "prc_stent", conditions))
    return out


def knee(rc: RC, rule: Rule) -> list[Finding]:
    out: list[Finding] = []
    for line in rc.bill.lines:
        cand = knee_candidates(line.description)
        if cand is None:
            continue
        system, comps, mats = cand
        if len(comps) != 1:
            out.append(grey(rule, "knee_components_not_itemised", line, {"item": line.description}))
            continue
        if rc.line_needs_confirmation(line):
            out.append(grey(rule, "confirm_line", line, {"item": line.description}))
            continue
        if rc.service_date is None:
            out.append(grey(rule, "need_service_date", line, {"item": line.description}))
            continue
        rows = [r for r in rc.kb.knee_rows(rc.service_date)
                if r.data["system"] == system and r.data["component"] == comps[0]]
        if mats:
            narrowed = [r for r in rows if r.data["material"] in mats or r.data["material"] == "any"]
            rows = narrowed or rows
        if not rows:
            out.append(grey(rule, "no_rule_data_for_date", line,
                            {"item": line.description, "date": rc.service_date.isoformat()}))
            continue
        row = max(rows, key=lambda r: r.dec("ceiling_ex_gst"))   # highest candidate ceiling
        cond = [] if (len(rows) == 1 or len({r.data['ceiling_ex_gst'] for r in rows}) == 1) \
            else ["cond_material_assumed_highest"]
        out.extend(_cap_check(rc, rule, line, row, "medical_device", line.description, "prc_knee", cond))
    return out


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9.]+", " ", s.lower()).strip()


# Common bill abbreviations for scheduled formulations. Words only: no number comes from here.
MED_ALIASES = [
    (r"normal saline|n\.?s\.?(?= *\d)", "sodium chloride 0.9%"),
    (r"ringer'?s? lactate|r\.?l\.?(?= *\d)", "ringer lactate"),
    (r"pcm", "paracetamol"),
    (r"aspirin", "acetylsalicylic acid"),
]
FORMS = {"tablet": r"\btab(?:let)?s?\b", "capsule": r"\bcap(?:sule)?s?\b",
         "injection": r"\binj(?:ection)?s?\b|\binfusion\b|\biv\b",
         "syrup": r"\bsyp\b|\bsyrup\b|\bsuspension\b|\boral liquid\b"}
_STRENGTH = re.compile(r"\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu|%)")
_VOLUME = re.compile(r"\d+(?:\.\d+)?\s*ml")


def _med_text(desc: str) -> str:
    """Lower-case bill text with aliases expanded; keeps '.', '%' and '/' so strengths survive."""
    t = " " + re.sub(r"[^a-z0-9.%/']+", " ", desc.lower()) + " "
    for pat, full in MED_ALIASES:
        t = re.sub(rf"(?<![a-z])(?:{pat})(?![a-z])", full, t)
    return re.sub(r"\bnon ?- ?glass\b|\bnon glass\b", "nonglass", t)


def _flat(s: str) -> str:
    return re.sub(r"\s+", "", s.lower())


def _form(text: str) -> str | None:
    for name, pat in FORMS.items():
        if re.search(pat, text.lower()):
            return name
    return None


def _pack_vols(unit: str) -> set[str]:
    """Pack volumes named in a row's unit; a plain '1 ml' is a per-ml price, not a pack."""
    if re.fullmatch(r"\s*1\s*ml\s*", unit.lower()):
        return set()
    return {_flat(v) for v in _VOLUME.findall(unit.lower())}


def _glass(text: str) -> str | None:
    t = re.sub(r"non ?- ?glass", "nonglass", text.lower())
    if "nonglass" in t:
        return "nonglass"
    return "glass" if re.search(r"\bglass\b", t) else None


def scheduled_candidates(desc: str, rows: list[Row]) -> tuple[list[Row], bool]:
    """Official rows this bill line can be, and whether the pack was ambiguous.

    A row must match the generic name, every strength printed in the row, and the dosage
    form when the bill shows one. Pack size and glass / non-glass narrow it further. If the
    bill names a pack volume that no row has, no ceiling applies to that pack (NPPA fixes
    unlisted packs separately), so nothing is returned.
    """
    t = _med_text(desc)
    flat = _flat(t)
    line_form = _form(t)
    cands = []
    for r in rows:
        name = " " + r.data["formulation"].lower() + " "
        if name.strip() not in t:
            continue
        if not all(_flat(x) in flat for x in _STRENGTH.findall(r.data["dosage_form_strength"].lower())):
            continue
        row_form = _form(r.data["dosage_form_strength"])
        if line_form and row_form and line_form != row_form:
            continue
        cands.append(r)
    if not cands:
        return [], False
    line_vols = {_flat(v) for v in _VOLUME.findall(t)}
    with_vol = [r for r in cands if _pack_vols(r.data["unit"])]
    if with_vol and line_vols:
        cands = [r for r in with_vol if _pack_vols(r.data["unit"]) & line_vols]
        if not cands:
            return [], False
    g = _glass(t)
    if g:
        same = [r for r in cands if _glass(r.data["unit"]) in (g, None)]
        cands = same or cands
    ceilings = {r.data["ceiling_ex_gst"] for r in cands}
    return cands, len(ceilings) > 1


def scheduled_medicine(rc: RC, rule: Rule) -> list[Finding]:
    """Match generic name, strength, form and pack to an NPPA scheduled formulation.

    Red is possible only when the user has confirmed that quantities on this bill are
    counted in dosage units (answers['medicine_qty_in_dosage_units'] = True). When the
    bill does not say which pack was used, the highest matching ceiling is used, which can
    only lower a claimed excess, and the finding says so.
    """
    d = rc.service_date
    if d is None or not rc.kb.has_data("nppa_scheduled_ceilings"):
        return []
    rows = rc.kb.scheduled_rows(d)
    out: list[Finding] = []
    for line in rc.bill.lines:
        if line.section not in (None, "pharmacy"):
            continue
        cands, ambiguous = scheduled_candidates(line.description, rows)
        if not cands:
            continue
        if rc.line_needs_confirmation(line):   # a hard-to-read number is asked about first
            out.append(grey(rule, "confirm_line", line, {"item": line.description}))
            continue
        best = max(cands, key=lambda r: r.dec("ceiling_ex_gst"))
        if not rc.answers.get("medicine_qty_in_dosage_units"):
            out.append(grey(rule, "confirm_medicine_units", line,
                            {"item": line.description, "unit": best.data["unit"]}))
            continue
        extra = ["cond_pack_assumed_highest"] if ambiguous else None
        out.extend(_cap_check(rc, rule, line, best, "medicine", line.description, "prc_sched", extra))
    return out


def mrp(rc: RC, rule: Rule) -> list[Finding]:
    """Charged above the printed MRP (MRP is inclusive of all taxes)."""
    figs = rc.figs
    out: list[Finding] = []
    for line in rc.bill.lines:
        if line.mrp_fig is None or line.qty_fig is None:
            continue
        if rc.line_needs_confirmation(line):
            out.append(grey(rule, "confirm_line", line, {"item": line.description}))
            continue
        billed, inputs, formula = billed_total(line, figs)
        if billed is None:
            continue
        qty = figs.value(line.qty_fig)
        cap = q(qty * figs.value(line.mrp_fig))
        cap_id = figs.computed(cap, "INR", Role.ALLOWED_AMOUNT, "quantity × MRP", [line.qty_fig, line.mrp_fig])
        billed_id = inputs[0] if len(inputs) == 1 else figs.computed(billed, "INR", Role.BILLED_AMOUNT, formula, inputs)
        slots = {"billed": billed_id, "qty": line.qty_fig, "mrp": line.mrp_fig, "allowed": cap_id}
        if billed - cap > PAISE_TOLERANCE:
            ex = figs.computed(q(billed - cap), "INR", Role.EXCESS, "billed − quantity × MRP", [billed_id, cap_id])
            slots["excess"] = ex
            out.append(make(rule, Verdict.RED, "prc_mrp", line, slots, {"item": line.description}, excess_fig=ex))
    return out
