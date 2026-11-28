"""Insurance deduction check against IRDAI's standard lists.

Deductions are typed as a family would copy them from a settlement letter; the lists come from the
IRDAI master circular (data/reference/irdai_lists.csv).
"""

from decimal import Decimal

import pytest
from conftest import bill
from fastapi.testclient import TestClient

from kk import insurance
from kk.compose.render import plain


@pytest.fixture()
def session(auditor):
    return auditor.audit_structured(bill([
        {"description": "Surgical gloves", "section": "consumables", "qty": "10", "rate": "20", "amount": "200"},
        {"description": "ICU charges", "section": "room", "qty": "2", "rate": "8000", "amount": "16000"},
        {"description": "Inj Meropenem 1g", "section": "pharmacy", "qty": "6", "rate": "1500", "amount": "9000"},
    ]), {"payer": "private_insurance"})


def test_irdai_lists_are_complete_and_sourced(kb):
    rows = kb.tables["irdai_lists"]
    counts = {k: sum(r.data["list"] == k for r in rows) for k in ("I", "II", "III", "IV")}
    assert counts == {"I": 68, "II": 37, "III": 23, "IV": 18}
    assert {r.data["source_id"] for r in rows} == {"irdai_mc_standardization_2020"}


@pytest.mark.parametrize("text,lst", [("Gloves", "I"), ("Laundry", "I"), ("Telephone charges", "I"),
                                      ("Air conditioner charges", "II"), ("Admission kit", "II"),
                                      ("Housekeeping", "II"), ("Pulse oximeter", "II"), ("Gauze", "III"),
                                      ("X-ray film", "III"), ("Registration fee", "IV"), ("Urine bag", "IV"),
                                      ("Face mask", "II"), ("Oxygen mask", "I")])
def test_common_settlement_wording_finds_the_right_list(kb, text, lst):
    assert insurance.match(kb, text)["list"] == lst


@pytest.mark.parametrize("text", ["Omez 20 mg caps", "Inj Meropenem 1g", "DES stent", "Patient diet", "Surgeon fee"])
def test_medicines_implants_and_treatment_are_not_on_the_lists(kb, text):
    assert insurance.match(kb, text) is None


def test_check_sorts_each_cut_and_totals_without_double_counting(auditor, session):
    panel, proofs = auditor.insurance(session, [
        {"line_id": "L1", "amount": "200", "reason": "non payable"},
        {"item": "ICU", "line_id": "L2", "amount": "4000", "reason": "proportionate deduction as per room rent"},
        {"line_id": "L3", "amount": "9500", "reason": "not justified"},
        {"item": "Admission kit", "amount": "500", "reason": "non medical expenses"},
    ], cashless=True)
    kinds = [r["kind"] for r in panel["rows"]]
    assert kinds == ["optional", "question", "question", "subsumed"]
    assert "ICU" in plain(panel["rows"][1]["lines"][0]) and "in full" in plain(panel["rows"][1]["lines"][0])
    assert "more than" in plain(panel["rows"][2]["lines"][1])          # cut above the billed amount
    assert plain(panel["rows"][3]["listed"]) == "IRDAI list II, item 27: Admission kit"
    val = lambda seg: next(Decimal(x["t"].replace("₹", "").replace(",", "")) for x in seg if "fig" in x)
    assert val(panel["total"]) == Decimal("14200")
    assert val(panel["hospital"]) == Decimal("500")
    assert val(panel["insurer"]) == Decimal("13500")
    assert val(panel["optional"]) == Decimal("200")
    assert "14" in plain(panel["next"])                               # IRDAI two-week resolution time
    origins = {p["origin"] for p in proofs.values()}
    assert "user_confirmed" in origins and "rule_data" in origins


def test_reimbursement_claim_does_not_tell_the_hospital_to_remove(auditor, session):
    panel, _ = auditor.insurance(session, [{"item": "Admission kit", "amount": "500"}], cashless=False, lang="gu")
    assert panel["hospital"] is None
    assert "નેટવર્ક બહારની" in plain(panel["rows"][0]["lines"][1])


def test_proportionate_cut_on_medicine(auditor, session):
    panel, _ = auditor.insurance(session, [{"line_id": "L3", "amount": "3000", "reason": "Room rent capping"}])
    assert panel["rows"][0]["kind"] == "question"
    assert "medicines" in plain(panel["rows"][0]["lines"][0])


def test_bad_input_is_refused(auditor, session):
    with pytest.raises(ValueError):
        auditor.insurance(session, [{"item": "Gloves", "amount": "-5"}])
    with pytest.raises(ValueError):
        auditor.insurance(session, [{"item": "Gloves", "amount": "abc"}])
    with pytest.raises(ValueError):
        auditor.insurance(session, [{"line_id": "L99", "amount": "5"}])
    from kk import api
    api.auditor.sessions[session.id] = session
    c = TestClient(api.app)
    assert c.post(f"/api/audit/{session.id}/insurance", json={"deductions": []}).status_code == 422
    r = c.post(f"/api/audit/{session.id}/insurance",
               json={"deductions": [{"item": "Gloves", "amount": "250"}], "lang": "kn"})
    assert r.status_code == 200 and r.json()["insurance"]["title"] == "ವಿಮಾ ಕಡಿತಗಳು"
