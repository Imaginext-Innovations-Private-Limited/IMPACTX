"""Complaint tracker: due dates, time limits and the next step, each traced to its source."""

from datetime import date

import pytest
from conftest import bill
from fastapi.testclient import TestClient

from kk.compose.render import plain
from kk.tracker import add_months, ics


@pytest.fixture()
def session(auditor):
    return auditor.audit_structured(bill([{"description": "DES stent", "section": "implant", "qty": "1",
                                           "rate": "60000", "amount": "60000"}],
                                         admission="2026-10-18", discharge="2026-10-20"), {"payer": "cash"})


def steps(panel):
    return {s["id"]: s for s in panel["steps"]}


def test_insurer_ladder_counts_the_two_week_rule_then_opens_the_ombudsman(auditor, session):
    panel, proofs = auditor.tracker(session, "insurer", {"insurer_gro": {"sent_on": "2026-11-01"}},
                                    today="2026-11-28")
    st = steps(panel)
    assert st["insurer_gro"]["status"] == "overdue"
    assert "2026-11-15" in plain(st["insurer_gro"]["lines"][1])          # sent + 14 days
    assert st["bima_bharosa"]["status"] == "next" and panel["next"] == "bima_bharosa"
    # Ombudsman: one month after the letter, then one year to file
    assert st["ombudsman"]["status"] == "later"
    text = " ".join(plain(x) for x in st["ombudsman"]["lines"])
    assert "2026-12-01" in text and "2027-12-01" in text
    # consumer case: two years from the discharge date by default
    assert "2028-10-20" in plain(st["consumer"]["lines"][0])
    # every day count is official data, except declared suggestions
    for p in proofs.values():
        assert p["origin"] == "rule_data"
    assert {p["rule"]["source_id"] for p in proofs.values()} >= {"irdai_grievance_tat", "ombudsman_rules_2017",
                                                                  "cpa_2019_s69", "kk_suggested_waits"}


def test_rejection_opens_the_ombudsman_at_once_and_starts_its_year(auditor, session):
    panel, _ = auditor.tracker(session, "insurer", {"insurer_gro": {"sent_on": "2026-11-01", "reply_on": "2026-11-05",
                                                                    "outcome": "not_solved"}}, today="2026-11-06")
    st = steps(panel)
    assert st["insurer_gro"]["status"] == "rejected"
    assert st["ombudsman"]["status"] == "next"
    assert "2027-11-05" in " ".join(plain(x) for x in st["ombudsman"]["lines"])


def test_solved_step_closes_the_rest(auditor, session):
    panel, _ = auditor.tracker(session, "hospital_desk", {"hosp_desk": {"sent_on": "2026-11-20", "reply_on": "2026-11-22",
                                                                        "outcome": "solved"}}, today="2026-11-28")
    st = steps(panel)
    assert st["hosp_desk"]["status"] == "resolved"
    assert all(st[k]["status"] == "not_needed" for k in ("hosp_gro", "nch", "consumer"))
    assert panel["next"] is None and panel["calendar"] == []


def test_suggested_waits_are_labelled_as_suggestions(auditor, session):
    panel, _ = auditor.tracker(session, "nppa", {"hosp_desk": {"sent_on": "2026-11-25"}}, today="2026-11-28", lang="ta")
    st = steps(panel)
    assert st["hosp_desk"]["status"] == "waiting"
    assert "பரிந்துரைக்கிறோம்" in plain(st["hosp_desk"]["lines"][1])      # "we suggest"
    assert any(b["suggestion"] for b in st["hosp_desk"]["basis"])
    assert panel["calendar"][0]["date"] == "2026-12-02"


def test_pmjay_grievance_uses_the_nha_timelines(auditor, session):
    ev = {"pmjay_cgrms": {"sent_on": "2026-11-01"}, "pmjay_dgrc": {"sent_on": "2026-11-16", "reply_on": "2026-11-20",
                                                                   "outcome": "not_solved"}}
    panel, proofs = auditor.tracker(session, "scheme_grievance", ev, today="2026-11-28")
    st = steps(panel)
    assert st["pmjay_sgrc"]["status"] == "next"
    assert "2026-12-20" in " ".join(plain(x) for x in st["pmjay_sgrc"]["lines"])   # appeal within 30 days
    assert any(p["rule"]["source_id"] == "pmjay_grievance_2021" for p in proofs.values())


def test_consumer_limit_passed_is_flagged(auditor, session):
    panel, _ = auditor.tracker(session, "consumer", {}, cause_on="2023-01-10", today="2026-11-28")
    assert steps(panel)["consumer"]["status"] in ("expired", "later")
    panel, _ = auditor.tracker(session, "consumer", {"nch": {"sent_on": "2026-01-01"}}, cause_on="2023-01-10",
                               today="2026-11-28")
    assert steps(panel)["consumer"]["status"] == "expired"


def test_calendar_file_is_valid_icalendar_in_any_language(auditor, session):
    panel, _ = auditor.tracker(session, "insurer", {"insurer_gro": {"sent_on": "2026-11-20"}}, today="2026-11-28",
                               lang="te")
    cal = panel["ics"]
    assert cal.startswith("BEGIN:VCALENDAR\r\n") and cal.endswith("END:VCALENDAR\r\n")
    assert "DTSTART;VALUE=DATE:20261204" in cal                       # 20 Nov + 14 days
    assert all(len(line.encode("utf-8")) <= 75 for line in cal.split("\r\n"))
    unfolded = cal.replace("\r\n ", "")
    assert "జవాబు గడువు" in unfolded


def test_ics_escapes_and_folds():
    out = ics([{"date": date(2026, 1, 2), "summary": "a, b; c", "description": "x" * 200}], "n")
    assert "SUMMARY:a\\, b\\; c" in out
    assert all(len(line.encode()) <= 75 for line in out.split("\r\n"))


def test_month_arithmetic_keeps_month_ends():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2024, 2, 29), 12) == date(2025, 2, 28)


def test_api_rejects_bad_input(auditor, session):
    from kk import api
    api.auditor.sessions[session.id] = session
    c = TestClient(api.app)
    ok = c.post(f"/api/audit/{session.id}/tracker", json={"channel": "insurer", "events": {}, "lang": "hi"})
    assert ok.status_code == 200 and ok.json()["tracker"]["title"] == "शिकायत ट्रैकर"
    assert c.post(f"/api/audit/{session.id}/tracker", json={"channel": "nowhere"}).status_code == 422
    assert c.post(f"/api/audit/{session.id}/tracker",
                  json={"channel": "insurer", "events": {"insurer_gro": {"sent_on": "28/11/2026"}}}).status_code == 422
    bad = c.post(f"/api/audit/{session.id}/tracker",
                 json={"channel": "insurer", "events": {"insurer_gro": {"sent_on": "2026-11-10", "reply_on": "2026-11-01"}}})
    assert bad.status_code == 422
    r = c.post(f"/api/audit/{session.id}/tracker.ics", json={"channel": "insurer",
                                                             "events": {"insurer_gro": {"sent_on": "2026-11-20"}}})
    assert r.headers["content-type"].startswith("text/calendar") and "BEGIN:VEVENT" in r.text
