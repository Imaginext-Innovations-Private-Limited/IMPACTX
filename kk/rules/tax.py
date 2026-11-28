"""GST charged where it should not be (rule TAX-GST).

What the law says, and how each part is used (data/reference/gst_health.csv, data/sources.yaml):

* Health care services by a clinical establishment are exempt: doctors, nursing, procedures, tests,
  and food advised for an admitted patient (CBIC Circular 32/06/2018-GST, Sl. No. 5; Sl. No. 74 of
  Notification 12/2017-CT(Rate)). GST added to such a line is red: the whole GST is the excess.
* From 18.07.2022 a room other than ICU/CCU/ICCU/NICU costing more than Rs 5000 a day per person is
  taxable at 5% (Notifications 03/2022 and 04/2022-CT(Rate)). GST on an ICU room, or on a room at or
  below the limit, is red; GST above 5% on a costlier room is red for the part above 5%.
* Medicines, consumables and implants given to an admitted patient are usually treated as part of
  the exempt composite supply (several Advance Rulings), but no binding circular says so for
  medicines, and GST is often only printed inside the MRP. So GST added on top of such a line is
  amber, a question for the hospital, never a claimed amount.
* Cosmetic or plastic surgery and hair transplants are outside the exemption unless they restore
  anatomy or function: grey. A unit whose ICU status is unclear (HDU, step-down): grey.
* A separate tax line (CGST, SGST, GST) on an in-patient bill is red for the part above what the
  rooms allow, unless the bill also has non-medical items (attendant food, phone, TV) that may be
  taxable: then amber.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from ..kb import Rule
from ..models import BillLine, Evidence, Finding, Origin, Role, Verdict
from ..money import q
from .base import RC, grey, make

TOL = Decimal("1.00")
TAX_LINE_RE = re.compile(r"(?i)^\s*(c\s*gst|s\s*gst|i\s*gst|ut\s*gst|gst|goods\s+and\s+services\s+tax|"
                         r"service\s+tax|tax)\b(?!\s*in)")
GSTIN_RE = re.compile(r"(?i)gstin|gst\s*no|gst\s*reg")
ROOM_RE = re.compile(r"(?i)\b(room|bed\s*charges?|bed\s*rent|ward|accommodation|suite|cabin|icu|iccu|ccu|nicu|"
                     r"picu|micu|sicu|cicu)\b")
ICU_RE = re.compile(r"(?i)\b(icu|iccu|ccu|nicu|picu|micu|sicu|cicu|intensive\s+care|critical\s+care|"
                    r"cardiac\s+care\s+unit)\b")
UNCLEAR_UNIT_RE = re.compile(r"(?i)\b(hdu|high\s+dependency|step[\s-]*down|semi[\s-]*icu|isolation)\b")
COSMETIC_RE = re.compile(r"(?i)\b(cosmetic|aesthetic|hair\s+transplant|hair\s+restoration|liposuction|botox|"
                         r"filler|rhinoplasty|abdominoplasty|tummy\s+tuck|breast\s+augmentation|plastic\s+surgery)\b")
FOOD_RE = re.compile(r"(?i)\b(diet|food|meal|meals|nutrition|canteen|breakfast|lunch|dinner)\b")
NON_PATIENT_RE = re.compile(r"(?i)\b(attendant|visitor|guest|relative|companion)\b")
NON_MEDICAL_RE = re.compile(r"(?i)\b(attendant|visitor|guest|telephone|phone|television|tv|laundry|internet|wifi|"
                            r"courier|photocop\w*|parking|toiletr\w*|mineral\s+water|baby\s+food|beauty)\b")
SERVICE_SECTIONS = {"procedure", "professional", "diagnostics", "package"}
SERVICE_RE = re.compile(r"(?i)\b(consult\w*|visit|surgeon|surgery|anaesth\w*|anesth\w*|ot\b|operation|theatre|"
                        r"nursing|investigation|lab|laboratory|x-?ray|scan|mri|ct\b|ultrasound|usg|ecg|echo|"
                        r"procedure|physiotherapy|dialysis|dressing|monitoring|doctor|professional|"
                        r"radiology|pathology|blood\s+test|culture|biopsy|delivery|labour|package)\b")
GOODS_SECTIONS = {"pharmacy", "consumables", "implant"}


def is_tax_line(line: BillLine) -> bool:
    d = line.description.strip()
    return bool(TAX_LINE_RE.match(d)) and not GSTIN_RE.search(d)


def _kind(line: BillLine) -> str:
    d = line.description
    if COSMETIC_RE.search(d):
        return "cosmetic"
    if line.section == "room" or ROOM_RE.search(d):
        if ICU_RE.search(d):
            return "icu"
        if UNCLEAR_UNIT_RE.search(d):
            return "unclear_unit"
        return "room"
    if FOOD_RE.search(d):
        return "food_other" if NON_PATIENT_RE.search(d) else "food_patient"
    if NON_MEDICAL_RE.search(d):
        return "non_medical"
    if line.section in GOODS_SECTIONS:
        return "goods"
    if line.section in SERVICE_SECTIONS or SERVICE_RE.search(d):
        return "service"
    return "other"


def _gst_charged(rc: RC, line: BillLine) -> tuple[str | None, str | None]:
    """(GST amount figure, base amount figure) when GST was added to this line, else (None, None).

    GST counts as added when a GST amount is printed, or when quantity × rate × (1 + printed rate)
    equals the amount. A GST rate printed while the amount equals quantity × rate is GST inside the
    price, not added: (None, None) and the caller may ask about it.
    """
    figs = rc.figs
    qty, rate, amt = figs.value(line.qty_fig), figs.value(line.rate_fig), figs.value(line.amount_fig)
    g_amt, g_rate = figs.value(line.gst_amount_fig), figs.value(line.gst_rate_fig)
    base_id = None
    if qty is not None and rate is not None:
        base_id = figs.computed(q(qty * rate), "INR", Role.EXPECTED_AMOUNT, "quantity × rate",
                                [line.qty_fig, line.rate_fig])
    if g_amt is not None and g_amt > 0:
        if base_id is None and amt is not None:
            # amount printed without quantity and rate: it either includes the GST or excludes it
            base_id = line.amount_fig
        return line.gst_amount_fig, base_id
    if g_rate is not None and g_rate > 0 and base_id is not None and amt is not None:
        base = figs.value(base_id)
        if abs(base * (1 + g_rate / 100) - amt) <= TOL and abs(base - amt) > TOL:
            gid = figs.computed(q(amt - base), "INR", Role.GST_AMOUNT, "amount − quantity × rate",
                                [line.amount_fig, base_id])
            return gid, base_id
    return None, None


def _per_day(rc: RC, line: BillLine, base_id: str | None) -> str | None:
    """Room charge per day, before GST."""
    figs = rc.figs
    if line.rate_fig is not None and line.qty_fig is not None:
        return line.rate_fig
    if base_id is not None and line.qty_fig is not None and figs.value(line.qty_fig):
        return figs.computed(q(figs.value(base_id) / figs.value(line.qty_fig)), "INR", Role.UNIT_RATE,
                             "amount before GST ÷ days", [base_id, line.qty_fig])
    return None


def _service_date(rc: RC) -> date | None:
    return rc.service_date or rc.bill.header.discharge_date or rc.bill.header.admission_date


def gst(rc: RC, rule: Rule) -> list[Finding]:
    figs, kb, bill = rc.figs, rc.kb, rc.bill
    d = _service_date(rc) or date.today()
    exempt = kb.gst_health("exempt_health_care_rate", d)
    if exempt is None:          # before GST (01.07.2017) there is nothing to check
        return []
    limit_row = kb.gst_health("room_limit_per_day", d)
    rate_row = kb.gst_health("room_rate_above_limit", d)
    inpatient = bool(bill.header.admission_date) or any(_kind(l) in ("room", "icu", "unclear_unit")
                                                       for l in bill.lines if not is_tax_line(l))
    limit_id = rate_id = None

    def limit():
        nonlocal limit_id
        if limit_id is None and limit_row is not None:
            limit_id = figs.from_rule(limit_row.dec("value"), "INR", Role.BENCHMARK, limit_row.id,
                                      limit_row.data["source_id"], limit_row.data["source_ref"])
        return limit_id

    def room_rate():
        nonlocal rate_id
        if rate_id is None and rate_row is not None:
            rate_id = figs.from_rule(rate_row.dec("value"), "percent", Role.GST_RATE, rate_row.id,
                                     rate_row.data["source_id"], rate_row.data["source_ref"])
        return rate_id

    out: list[Finding] = []
    allowed_rooms: list[str] = []          # GST the rooms may carry, for a separate tax line
    room_basis_known = True
    for line in bill.lines:
        if is_tax_line(line) or figs.value(line.amount_fig) is None:
            continue
        kind = _kind(line)
        text = {"item": line.description}
        if kind == "room" and limit_row is not None:
            # a room above the limit may carry GST at the room rate; it counts for a bill-level tax line
            per_day = _per_day(rc, line, line.amount_fig if line.gst_amount_fig else None)
            if per_day is None:
                room_basis_known = False
            elif figs.value(per_day) > limit_row.dec("value"):
                days = figs.value(line.qty_fig) or Decimal(1)
                base = q(figs.value(per_day) * days)
                inputs = [per_day] + ([line.qty_fig] if line.qty_fig else [])
                base_id = figs.computed(base, "INR", Role.EXPECTED_AMOUNT, "room rate × days", inputs)
                allowed_rooms.append(figs.computed(q(base * rate_row.dec("value") / 100), "INR",
                                                   Role.ALLOWED_AMOUNT, "room charge × GST rate ÷ 100",
                                                   [base_id, room_rate()]))
        if rc.line_needs_confirmation(line):
            continue
        gid, base_id = _gst_charged(rc, line)
        if gid is None:
            g_rate = figs.value(line.gst_rate_fig)
            if g_rate and inpatient and kind in ("service", "icu", "food_patient"):
                out.append(make(rule, Verdict.AMBER, "tax_gst_rate_only", line,
                                {"printed_gst": line.gst_rate_fig}, text))
            continue
        slots = {"gst_amount": gid, "excess": gid}
        if kind == "cosmetic":
            out.append(grey(rule, "tax_cosmetic", line, text))
        elif kind == "unclear_unit":
            out.append(grey(rule, "tax_unclear_unit", line, text))
        elif kind == "service":
            out.append(make(rule, Verdict.RED, "tax_gst_service", line, slots, text, excess_fig=gid))
        elif kind == "food_patient" and inpatient:
            out.append(make(rule, Verdict.RED, "tax_gst_food", line, slots, text, excess_fig=gid))
        elif kind == "icu":
            out.append(make(rule, Verdict.RED, "tax_gst_icu", line, slots, text, excess_fig=gid))
        elif kind == "room":
            out.extend(_room(rc, rule, line, gid, base_id, limit_row, limit, room_rate, text))
        elif kind == "goods" and inpatient:
            out.append(make(rule, Verdict.AMBER, "tax_gst_goods_inpatient", line, {"gst_amount": gid}, text))
    if inpatient:
        out.extend(_tax_lines(rc, rule, allowed_rooms, room_basis_known, limit, limit_row))
    return out


def _room(rc: RC, rule: Rule, line: BillLine, gid: str, base_id: str | None, limit_row, limit, room_rate,
          text: dict) -> list[Finding]:
    figs = rc.figs
    slots = {"gst_amount": gid, "excess": gid}
    if limit_row is None:       # before 18.07.2022 every room was exempt
        return [make(rule, Verdict.RED, "tax_gst_room_before", line, slots, text, excess_fig=gid)]
    per_day = _per_day(rc, line, base_id)
    if per_day is None:
        return [grey(rule, "tax_room_rate_unknown", line, text)]
    slots.update({"per_day": per_day, "limit": limit()})
    if figs.value(per_day) <= limit_row.dec("value"):
        return [make(rule, Verdict.RED, "tax_gst_room_low", line, slots, text, excess_fig=gid)]
    if base_id is None:
        return [grey(rule, "tax_room_rate_unknown", line, text)]
    rate_id = room_rate()
    allowed = figs.computed(q(figs.value(base_id) * figs.value(rate_id) / 100), "INR", Role.ALLOWED_AMOUNT,
                            "room charge × GST rate ÷ 100", [base_id, rate_id])
    slots.update({"rate": rate_id, "allowed": allowed})
    excess = figs.value(gid) - figs.value(allowed)
    if excess > TOL:
        ex = figs.computed(q(excess), "INR", Role.EXCESS, "GST charged − GST allowed", [gid, allowed])
        slots["excess"] = ex
        return [make(rule, Verdict.RED, "tax_gst_room_high", line, slots, text, excess_fig=ex)]
    slots.pop("excess")
    return [make(rule, Verdict.GREEN, "tax_gst_room_ok", line, slots, text)]


def _tax_lines(rc: RC, rule: Rule, allowed_rooms: list[str], basis_known: bool, limit, limit_row) -> list[Finding]:
    """A separate CGST/SGST/GST line on an in-patient bill."""
    figs, bill = rc.figs, rc.bill
    taxes = [l for l in bill.lines if is_tax_line(l) and figs.value(l.amount_fig) and not rc.line_needs_confirmation(l)]
    if not taxes:
        return []
    per_line_gst = any(_gst_charged(rc, l)[0] for l in bill.lines if not is_tax_line(l))
    if per_line_gst:
        return []      # GST already shown on the lines; a summary line repeats it
    if not basis_known:
        return [grey(rule, "tax_room_rate_unknown", taxes[0], {"item": taxes[0].description})]
    total_tax = figs.computed(q(sum(figs.value(l.amount_fig) for l in taxes)), "INR", Role.GST_AMOUNT,
                              "sum of tax lines", [l.amount_fig for l in taxes]) if len(taxes) > 1 \
        else taxes[0].amount_fig
    if allowed_rooms:
        allowed = figs.computed(q(sum(figs.value(a) for a in allowed_rooms)), "INR", Role.ALLOWED_AMOUNT,
                                "sum of GST allowed on rooms above the limit", allowed_rooms) \
            if len(allowed_rooms) > 1 else allowed_rooms[0]
    else:
        allowed = figs.add(0, "INR", Role.ALLOWED_AMOUNT, Origin.COMPUTED,
                           Evidence(formula="no room on this bill is above the daily limit", inputs=[]))
    excess = figs.value(total_tax) - figs.value(allowed)
    if excess <= TOL:
        return []
    ex = figs.computed(q(excess), "INR", Role.EXCESS, "tax charged − GST allowed on rooms", [total_tax, allowed])
    first = taxes[0]
    text = {"item": " + ".join(l.description for l in taxes)}
    slots = {"tax": total_tax, "allowed": allowed, "excess": ex}
    if limit_row is not None:
        slots["limit"] = limit()
    key = "tax_gst_bill_line" if allowed_rooms else "tax_gst_bill_line_none"
    if limit_row is None:
        key = "tax_gst_bill_line_before"
    mixed = any(_kind(l) in ("non_medical", "food_other") for l in bill.lines if not is_tax_line(l))
    if mixed:
        return [make(rule, Verdict.AMBER, "tax_gst_bill_line_mixed", first, slots, text, excess_fig=ex)]
    return [make(rule, Verdict.RED, key, first, slots, text, excess_fig=ex)]
