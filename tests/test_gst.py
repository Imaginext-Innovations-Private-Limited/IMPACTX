"""TAX-GST: GST charged where Indian GST law exempts health care.

Inputs are small hand-built bills that exercise each branch; they are not evaluation data.
Expected amounts come from the official limit (Rs 5000 a day) and rate (5%) in gst_health.csv.
"""

from decimal import Decimal

from conftest import bill

from kk.models import Verdict


def gst_findings(s, verdict=None):
    return [f for f in s.result.findings if f.rule_id == "TAX-GST" and (verdict is None or f.verdict == verdict)]


def val(s, fid):
    return s.figs.value(fid)


def test_gst_on_doctor_and_procedure_is_red(auditor):
    s = auditor.audit_structured(bill([
        {"description": "Surgeon fee", "section": "professional", "qty": "1", "rate": "20000",
         "gst_rate": "18", "gst_amount": "3600", "amount": "23600"},
        {"description": "OT charges", "section": "procedure", "qty": "1", "rate": "10000", "amount": "11800",
         "gst_rate": "18"},
    ]), {"payer": "cash"})
    reds = gst_findings(s, Verdict.RED)
    assert [f.message_key for f in reds] == ["tax_gst_service", "tax_gst_service"]
    assert [val(s, f.excess_fig) for f in reds] == [Decimal("3600"), Decimal("1800")]
    assert val(s, s.result.recoverable_fig) == Decimal("5400")
    # the hospital decides it: tax is not a scheme entitlement
    assert val(s, s.result.hospital_fig) == Decimal("5400")


def test_room_at_or_below_limit_is_exempt(auditor):
    s = auditor.audit_structured(bill([
        {"description": "Private room rent", "section": "room", "qty": "3", "rate": "4500", "gst_rate": "5",
         "gst_amount": "675", "amount": "14175"}]), {"payer": "cash"})
    [f] = gst_findings(s, Verdict.RED)
    assert f.message_key == "tax_gst_room_low"
    assert val(s, f.slots["limit"]) == Decimal("5000")
    assert val(s, f.excess_fig) == Decimal("675")


def test_icu_is_exempt_whatever_it_costs(auditor):
    s = auditor.audit_structured(bill([
        {"description": "ICU bed charges", "section": "room", "qty": "2", "rate": "12000", "gst_rate": "5",
         "gst_amount": "1200", "amount": "25200"}]), {"payer": "cash"})
    [f] = gst_findings(s, Verdict.RED)
    assert f.message_key == "tax_gst_icu" and val(s, f.excess_fig) == Decimal("1200")


def test_room_above_limit_allows_five_percent(auditor):
    ok = auditor.audit_structured(bill([
        {"description": "Deluxe room", "section": "room", "qty": "2", "rate": "6000", "gst_rate": "5",
         "gst_amount": "600", "amount": "12600"}]), {"payer": "cash"})
    [f] = gst_findings(ok)
    assert f.verdict == Verdict.GREEN and f.message_key == "tax_gst_room_ok"
    assert val(ok, f.slots["allowed"]) == Decimal("600")

    high = auditor.audit_structured(bill([
        {"description": "Deluxe room", "section": "room", "qty": "2", "rate": "6000", "gst_rate": "12",
         "gst_amount": "1440", "amount": "13440"}]), {"payer": "cash"})
    [f] = gst_findings(high, Verdict.RED)
    assert f.message_key == "tax_gst_room_high"
    assert val(high, f.excess_fig) == Decimal("840")          # 1440 charged − 600 allowed


def test_rooms_were_exempt_before_july_2022(auditor):
    s = auditor.audit_structured(bill([
        {"description": "Deluxe room", "section": "room", "qty": "2", "rate": "6000", "gst_amount": "600",
         "amount": "12600"}], admission="2022-07-01", discharge="2022-07-03"), {"payer": "cash"})
    [f] = gst_findings(s, Verdict.RED)
    assert f.message_key == "tax_gst_room_before" and val(s, f.excess_fig) == Decimal("600")


def test_patient_diet_is_exempt_but_attendant_food_is_not_flagged(auditor):
    s = auditor.audit_structured(bill([
        {"description": "Patient diet", "qty": "3", "rate": "300", "gst_amount": "45", "amount": "945"},
        {"description": "Attendant food", "qty": "3", "rate": "300", "gst_amount": "45", "amount": "945"},
    ]), {"payer": "cash"})
    [f] = gst_findings(s)
    assert f.message_key == "tax_gst_food" and f.line_id == "L1"


def test_medicine_with_gst_added_is_amber_never_a_claimed_amount(auditor):
    s = auditor.audit_structured(bill([
        {"description": "Inj Ceftriaxone 1g", "section": "pharmacy", "qty": "4", "rate": "100",
         "gst_rate": "5", "gst_amount": "20", "amount": "420"}]), {"payer": "cash"})
    [f] = gst_findings(s)
    assert f.verdict == Verdict.AMBER and f.message_key == "tax_gst_goods_inpatient" and f.excess_fig is None
    assert s.result.recoverable_fig is None


def test_gst_inside_the_price_is_not_called_added(auditor):
    # rate shown, but amount = quantity × rate: GST is part of the price (e.g. MRP), not added on top
    s = auditor.audit_structured(bill([
        {"description": "Inj Ceftriaxone 1g", "section": "pharmacy", "qty": "4", "rate": "105",
         "gst_rate": "5", "amount": "420"}]), {"payer": "cash"})
    assert not gst_findings(s)


def test_cosmetic_surgery_is_grey(auditor):
    s = auditor.audit_structured(bill([
        {"description": "Cosmetic rhinoplasty surgery", "section": "procedure", "qty": "1", "rate": "80000",
         "gst_amount": "14400", "amount": "94400"}]), {"payer": "cash"})
    [f] = gst_findings(s)
    assert f.verdict == Verdict.GREY and f.message_key == "grey_tax_cosmetic"


def test_separate_tax_lines_on_inpatient_bill(auditor):
    lines = [
        {"description": "Room rent (twin sharing)", "section": "room", "qty": "3", "rate": "3000", "amount": "9000"},
        {"description": "Consultation charges", "section": "professional", "qty": "3", "rate": "1000", "amount": "3000"},
        {"description": "CGST 9%", "amount": "1080"},
        {"description": "SGST 9%", "amount": "1080"},
    ]
    s = auditor.audit_structured(bill(lines), {"payer": "cash"})
    [f] = gst_findings(s, Verdict.RED)
    assert f.message_key == "tax_gst_bill_line_none"
    assert val(s, f.slots["tax"]) == Decimal("2160") and val(s, f.excess_fig) == Decimal("2160")

    # with a room above the limit, 5% of that room is allowed
    lines[0] = {"description": "Suite room", "section": "room", "qty": "3", "rate": "8000", "amount": "24000"}
    s = auditor.audit_structured(bill(lines), {"payer": "cash"})
    [f] = gst_findings(s, Verdict.RED)
    assert f.message_key == "tax_gst_bill_line"
    assert val(s, f.slots["allowed"]) == Decimal("1200") and val(s, f.excess_fig) == Decimal("960")

    # a non-medical item that may be taxable turns it into a question
    s = auditor.audit_structured(bill(lines + [{"description": "Telephone charges", "qty": "1", "rate": "200",
                                                  "amount": "200"}]), {"payer": "cash"})
    [f] = gst_findings(s)
    assert f.verdict == Verdict.AMBER and f.message_key == "tax_gst_bill_line_mixed"


def test_gstin_header_line_is_not_a_tax_line():
    from kk.models import BillLine
    from kk.rules.tax import is_tax_line
    assert not is_tax_line(BillLine(id="L1", description="GSTIN: 29ABCDE1234F1Z5"))
    assert is_tax_line(BillLine(id="L1", description="CGST @ 9%"))
    assert is_tax_line(BillLine(id="L1", description="GST 18%"))


def test_every_gst_figure_traces_to_an_official_source(auditor):
    s = auditor.audit_structured(bill([
        {"description": "Private room rent", "section": "room", "qty": "3", "rate": "4500", "gst_amount": "675",
         "amount": "14175"}]), {"payer": "cash"})
    [f] = gst_findings(s, Verdict.RED)
    lim = s.figs.get(f.slots["limit"])
    assert lim.origin.value == "rule_data" and lim.evidence.source_id == "gst_n04_2022_room"
    assert auditor.kb.source_field("gst_n04_2022_room", "effective") == "2022-07-18"
    view = auditor.view(s, "kn")
    card = next(x for x in view["findings"] if x["rule_id"] == "TAX-GST")
    assert card["title"] == "ಆಸ್ಪತ್ರೆ ಚಿಕಿತ್ಸೆಯ ಮೇಲೆ GST"
    assert any(b["source_id"] == "gst_circular32_2018" for b in card["basis"])
