"""Context resolver: settle the facts that decide which rules apply.

A fact that cannot be settled stays unknown, and every rule that needs it
returns 'cannot verify' (grey) instead of guessing.
"""

from __future__ import annotations

from datetime import date

from .kb import KnowledgeBase
from .models import Bill, Context, Fact, Payer


def resolve(bill: Bill, kb: KnowledgeBase, answers: dict | None = None) -> Context:
    a = answers or {}
    ctx = Context(language=a.get("language", "en"))

    # date of service: discharge date, else admission date, else the user's answer
    d = bill.header.discharge_date or bill.header.admission_date
    if a.get("service_date"):
        ctx.service_date = Fact(value=date.fromisoformat(a["service_date"]), source="user")
    elif d:
        ctx.service_date = Fact(value=d, source="bill")

    if a.get("state"):
        ctx.state = Fact(value=a["state"].lower(), source="user")

    # payer
    payer = a.get("payer")
    if payer:
        ctx.payer = Fact(value=Payer(payer), source="user")
        if Payer(payer) == Payer.CASH and bill.header.scheme_markers:
            ctx.payer.note = "bill_shows_scheme_markers"

    # was the case booked under the scheme?
    if bill.header.scheme_markers:
        ctx.scheme_booked = Fact(value=True, source="bill", note=",".join(bill.header.scheme_markers))
    elif a.get("scheme_booked") is not None:
        ctx.scheme_booked = Fact(value=bool(a["scheme_booked"]), source="user")

    if a.get("scheme_limit_exhausted") is not None:
        ctx.scheme_limit_exhausted = Fact(value=bool(a["scheme_limit_exhausted"]), source="user")

    # hospital and empanelment on the date of service
    name = a.get("hospital_name") or bill.header.hospital_name
    if name:
        ctx.hospital_id = Fact(value=name, source="user" if a.get("hospital_name") else "bill")
    if a.get("hospital_empanelled") is not None:
        ctx.hospital_empanelled_on_service_date = Fact(value=bool(a["hospital_empanelled"]), source="user",
                                                       note="stated by user")
    elif ctx.service_date.known and kb.has_data("empanelled_hospitals"):
        row = None
        for key in (bill.header.gstin, name):
            if key:
                row = kb.hospital_status(key, ctx.service_date.value)
                if row:
                    break
        if row:
            ctx.hospital_empanelled_on_service_date = Fact(
                value=row.data["status"] == "empanelled", source="empanelment_list",
                note=f"{row.id} ({row.data['status']})")

    if a.get("city_tier"):
        ctx.city_tier = Fact(value=a["city_tier"], source="user")
    if a.get("package_code"):
        ctx.package_code = Fact(value=a["package_code"], source="user")
    return ctx


def is_scheme_payer(ctx: Context) -> bool | None:
    if not ctx.payer.known:
        return None
    return ctx.payer.value in (Payer.PMJAY, Payer.STATE_SCHEME)
