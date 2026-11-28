from decimal import Decimal

from conftest import bill

from kk.models import Verdict


def findings(s, rule_id=None, verdict=None):
    return [f for f in s.result.findings if (rule_id is None or f.rule_id == rule_id)
            and (verdict is None or f.verdict == verdict)]


def val(s, fid):
    return s.figs.value(fid)


def test_stent_above_ceiling_uses_five_percent_gst(auditor):
    s = auditor.audit_structured(bill([{"description": "Drug Eluting Stent (Everolimus) 3.0x28", "section": "implant",
                                        "qty": "1", "rate": "58000", "amount": "58000"}]), {"payer": "cash"})
    [f] = findings(s, "PRC-STENT", Verdict.RED)
    assert val(s, f.slots["allowed"]) == Decimal("41145.33")
    assert val(s, f.excess_fig) == Decimal("16854.67")
    assert val(s, s.result.recoverable_fig) == Decimal("16854.67")


def test_stent_within_ceiling_is_green(auditor):
    s = auditor.audit_structured(bill([{"description": "DES stent", "qty": "1", "rate": "41145", "amount": "41145"}]),
                                 {"payer": "cash"})
    assert findings(s, "PRC-STENT", Verdict.GREEN)
    assert s.result.recoverable_fig is None


def test_unknown_stent_type_uses_higher_ceiling_and_says_so(auditor):
    s = auditor.audit_structured(bill([{"description": "Coronary stent 3x18", "qty": "1", "rate": "45000",
                                        "amount": "45000"}]), {"payer": "cash"})
    [f] = findings(s, "PRC-STENT", Verdict.RED)
    assert "cond_stent_type_assumed_des" in f.conditions
    assert val(s, f.excess_fig) == Decimal("3854.67")


def test_non_coronary_stent_is_ignored(auditor):
    s = auditor.audit_structured(bill([{"description": "DJ stent 6Fr", "qty": "1", "rate": "9000", "amount": "9000"}]),
                                 {"payer": "cash"})
    assert not findings(s, "PRC-STENT")


def test_no_rule_data_for_old_date_is_grey(auditor):
    s = auditor.audit_structured(bill([{"description": "DES stent", "qty": "1", "rate": "90000", "amount": "90000"}],
                                      admission="2026-03-01", discharge="2026-03-03"), {"payer": "cash"})
    [f] = findings(s, "PRC-STENT")
    assert f.verdict == Verdict.GREY and f.message_key == "grey_no_rule_data_for_date"


def test_knee_unknown_material_uses_highest_ceiling(auditor):
    s = auditor.audit_structured(bill([{"description": "Femoral component, primary knee", "qty": "1",
                                        "rate": "60000", "amount": "60000"}]), {"payer": "cash"})
    [f] = findings(s, "PRC-KNEE", Verdict.RED)
    assert val(s, f.slots["ceiling"]) == Decimal("51562.94")
    assert "cond_material_assumed_highest" in f.conditions
    assert val(s, f.excess_fig) == Decimal("60000") - Decimal("54141.09")


def test_knee_lump_sum_is_grey(auditor):
    s = auditor.audit_structured(bill([{"description": "Knee implant set", "qty": "1", "rate": "150000",
                                        "amount": "150000"}]), {"payer": "cash"})
    [f] = findings(s, "PRC-KNEE")
    assert f.verdict == Verdict.GREY


def test_mrp_and_arithmetic(auditor):
    s = auditor.audit_structured(bill([
        {"description": "Inj Ceftriaxone 1g", "section": "pharmacy", "qty": "2", "rate": "80", "mrp": "70", "amount": "160"},
        {"description": "IV set", "section": "consumables", "qty": "3", "rate": "100", "amount": "350"},
    ]), {"payer": "cash"})
    [mrp] = findings(s, "PRC-MRP", Verdict.RED)
    assert val(s, mrp.excess_fig) == Decimal("20.00")
    [ari] = findings(s, "ARI-QTYRATE", Verdict.RED)
    assert val(s, ari.excess_fig) == Decimal("50.00")
    assert val(s, s.result.recoverable_fig) == Decimal("70.00")


def test_no_double_counting_on_one_line(auditor):
    # stent above the ceiling AND quantity x rate wrong on the same line: largest claim only
    s = auditor.audit_structured(bill([{"description": "DES stent", "qty": "1", "rate": "50000", "amount": "58000"}]),
                                 {"payer": "cash"})
    reds = findings(s, verdict=Verdict.RED)
    assert {f.rule_id for f in reds} == {"PRC-STENT", "ARI-QTYRATE"}
    assert val(s, s.result.recoverable_fig) == Decimal("16854.67")


def test_scheme_beneficiary_charged_for_covered_items(auditor):
    lines = [{"description": "DES stent", "qty": "1", "rate": "30000", "amount": "30000"},
             {"description": "Pharmacy charges", "section": "pharmacy", "qty": "1", "rate": "4000", "amount": "4000"},
             {"description": "Deluxe room upgrade", "qty": "1", "rate": "3000", "amount": "3000"}]
    s = auditor.audit_structured(bill(lines, scheme_markers=["PMJAY"]),
                                 {"payer": "pmjay", "hospital_empanelled": True, "patient_paid": True})
    reds = findings(s, "ENT-COVERED", Verdict.RED)
    assert len(reds) == 2
    assert findings(s, "ENT-COVERED", Verdict.AMBER)            # room upgrade is a question, not a claim
    assert val(s, s.result.recoverable_fig) == Decimal("34000.00")


def test_scheme_rules_grey_without_answers(auditor):
    s = auditor.audit_structured(bill([{"description": "Pharmacy", "qty": "1", "rate": "10", "amount": "10"}]),
                                 {"payer": "pmjay"})
    [f] = findings(s, "ENT-COVERED")
    assert f.verdict == Verdict.GREY and f.message_key == "grey_need_empanelment"


def test_cash_denial(auditor):
    s = auditor.audit_structured(bill([{"description": "Angioplasty package", "qty": "1", "rate": "180000",
                                        "amount": "180000"}], total="180000"),
                                 {"payer": "pmjay", "hospital_empanelled": True, "scheme_booked": False})
    [f] = findings(s, "ENT-CASH-DENIAL", Verdict.RED)
    assert val(s, s.result.recoverable_fig) == Decimal("180000.00")


def test_room_days_are_amber_and_tolerate_one_extra_day(auditor):
    ok = auditor.audit_structured(bill([{"description": "Room rent general ward", "section": "room", "qty": "3",
                                         "rate": "2000", "amount": "6000"}]), {"payer": "cash"})
    assert not findings(ok, "CONV-ROOMDAYS")
    s = auditor.audit_structured(bill([{"description": "Room rent general ward", "section": "room", "qty": "5",
                                        "rate": "2000", "amount": "10000"}]), {"payer": "cash"})
    [f] = findings(s, "CONV-ROOMDAYS")
    assert f.verdict == Verdict.AMBER and s.result.recoverable_fig is None


def test_duplicates_are_amber(auditor):
    line = {"description": "CBC test", "qty": "1", "rate": "400", "amount": "400", "date": "2026-11-19"}
    s = auditor.audit_structured(bill([line, dict(line)]), {"payer": "cash"})
    [f] = findings(s, "CONV-DUPLICATE")
    assert f.verdict == Verdict.AMBER
    assert val(s, s.result.amber_total_fig) == Decimal("400.00")


def test_every_finding_number_has_provenance(auditor):
    s = auditor.audit_structured(bill([{"description": "DES stent", "qty": "1", "rate": "58000", "amount": "58000"}]),
                                 {"payer": "cash"})
    for f in s.result.findings:
        for fid in f.slots.values():
            fig = s.result.figures[fid]
            ev = fig.evidence
            assert ev.bill_tokens or ev.bbox or ev.rule_row or ev.formula or ev.note
            for i in ev.inputs:
                assert i in s.result.figures
