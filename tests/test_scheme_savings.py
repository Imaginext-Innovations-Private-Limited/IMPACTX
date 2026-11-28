"""Scheme savings (kk/schemes.py): what a government scheme could have paid on a cash bill.

Awareness only. These tests check that every state is listed, every cover cites a source,
the arithmetic follows the stated formula, all six languages render without gaps, and the
amount is never added to what the family can challenge.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from kk import schemes as sch
from kk.compose.render import CATALOG, LANGS, plain
from kk.money import q

ROOT = Path(__file__).resolve().parents[1]
BILLS = ROOT / "tests/fixtures/sample_bills"
DATA = yaml.safe_load((ROOT / "data/schemes.yaml").read_text(encoding="utf-8"))
SOURCES = yaml.safe_load((ROOT / "data/sources.yaml").read_text(encoding="utf-8"))
ROWS = DATA["central"] + [r for rows in DATA["states"].values() for r in rows]


def _cash_session(auditor, name="bill2_knee_pmjay", state="karnataka"):
    d = json.loads((BILLS / f"{name}.json").read_text(encoding="utf-8"))
    answers = {**d["answers"], "payer": "cash", "state": state}
    return auditor.audit_files([str(BILLS / f"{name}.pdf")], answers)


def test_every_state_and_ut_is_listed():
    assert len(sch.STATES) == 36
    assert set(DATA["states"]) == {k for k, _ in sch.STATES}


def test_every_cover_cites_a_source_with_a_link():
    for r in ROWS:
        src = SOURCES[r["source"]]
        assert src["urls"] and src["date"] and src["title"], r["id"]
        if r["kind"] == "no_ceiling":
            assert r["cover"] is None
        else:
            assert isinstance(r["cover"], int) and r["cover"] > 0, r["id"]


def test_every_code_has_wording_in_six_languages():
    keys = set()
    for r in ROWS:
        keys |= {f"sav_who_{c}" for c in r["who"]}
        if r.get("where", "empanelled") != "empanelled":
            keys.add(f"sav_where_{r['where']}")
        if r.get("note"):
            keys.add(f"sav_note_{r['note']}")
    for lang in LANGS:
        missing = [k for k in keys if k not in CATALOG[lang]]
        assert not missing, (lang, missing)


def test_saving_is_the_smaller_of_covered_and_cover(auditor):
    s = _cash_session(auditor)
    panel, proofs = auditor.schemes(s, "karnataka", "en")
    res = s.schemes["karnataka"]
    figs = s.result.figures
    covered = figs[res["covered"]].value
    assert covered > 0
    for r in res["state_rows"] + res["central"]:
        saving = figs[r["saving"]].value
        if r["kind"] == "no_ceiling":
            assert saving == covered
        elif r["kind"] == "co_pay":   # Karnataka APL: 30% of the package, up to 1.5 lakh
            assert saving == min(q(covered * Decimal(30) / 100), Decimal(150000))
        else:
            assert saving == min(covered, figs[r["cover"]].value)
        assert r["saving"] in proofs and proofs[r["saving"]]["formula"]["inputs"]
        if r["cover"]:
            assert proofs[r["cover"]]["rule"]["source_url"]


def test_savings_never_change_what_the_family_can_challenge(auditor):
    s = _cash_session(auditor)
    before = (s.result.recoverable_fig, s.result.hospital_fig, s.result.scheme_fig)
    values = [s.figs.value(f) for f in before]
    for state in ("karnataka", "rajasthan", "tamil_nadu", "ladakh"):
        auditor.schemes(s, state, "en")
    assert (s.result.recoverable_fig, s.result.hospital_fig, s.result.scheme_fig) == before
    assert [s.figs.value(f) for f in before] == values
    # no challenge total is built from a potential saving
    chain, queue = set(), [f for f in before if f]
    while queue:
        fid = queue.pop()
        if fid not in chain:
            chain.add(fid)
            queue.extend(s.result.figures[fid].evidence.inputs or [])
    assert not any(s.result.figures[f].role.value == "potential_saving" for f in chain)


def test_headline_names_the_biggest_general_scheme(auditor):
    s = _cash_session(auditor, "bill1_cardiac_cash", "rajasthan")
    panel, _ = auditor.schemes(s, "rajasthan", "en")
    res = s.schemes["rajasthan"]
    assert res["best"]["id"] == "rj_maa"   # state scheme named first on a tie with PM-JAY
    assert "Mukhyamantri Ayushman Arogya" in plain(panel["best"])


@pytest.mark.parametrize("lang", LANGS)
def test_panel_renders_fully_in_every_language(auditor, lang):
    s = _cash_session(auditor)
    for state in ("tamil_nadu", "goa", "ladakh", ""):
        panel, proofs = auditor.schemes(s, state, lang)
        texts = [panel["intro"], panel["conds"], panel["not_counted"], panel["have_card"]]
        for r in panel["state_rows"] + panel["central"]:
            texts += [r["line"], *r["who"]] + [x for x in (r["where"], r["note"]) if x]
        for segs in texts:
            assert "…" not in plain(segs), (lang, state, plain(segs))
            for seg in segs:
                if "fig" in seg:
                    assert seg["fig"] in proofs
        if state == "ladakh":
            assert panel["no_state_scheme"] and not panel["state_rows"]
        if state == "":
            assert panel["choose_state"] and panel["central"]


def test_not_shown_when_a_scheme_card_was_used(auditor):
    s = _cash_session(auditor)
    auditor.set_answers(s.id, {"payer": "pmjay"})
    panel, proofs = auditor.schemes(s, "karnataka", "en")
    assert panel == {"applies": False} and proofs == {}
    assert auditor.view(s, "en")["schemes"] == {"applies": False}


def test_api_lists_states_and_returns_any_state():
    from kk.api import app
    c = TestClient(app)
    assert len(c.get("/api/states").json()) == 36
    r = c.post("/api/audit-structured?lang=en", json={
        "bill": {"header": {"hospital_name": "Test", "admission_date": "2026-11-18", "discharge_date": "2026-11-20"},
                 "lines": [{"description": "DES stent", "qty": "1", "rate": "58000", "amount": "58000"}]},
        "answers": {"payer": "cash", "state": "karnataka"}})
    v = r.json()
    assert v["schemes"]["applies"] and v["schemes"]["state"] == "karnataka"
    r = c.get(f"/api/audit/{v['id']}/schemes?state=punjab&lang=hi").json()
    assert r["schemes"]["state_rows"][0]["id"] == "pb_mmsy"
    best = r["schemes"]["best_fig"]
    assert r["proofs"][best]["display"] == "₹58,000.00"
    # the challenge total in the main view is unchanged
    assert c.get(f"/api/audit/{v['id']}?lang=en").json()["recoverable_fig"] == v["recoverable_fig"]
