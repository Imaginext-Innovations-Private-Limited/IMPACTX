import shutil
from datetime import date
from decimal import Decimal

import pytest

from kk.kb import DataError, KnowledgeBase


def test_real_reference_values(kb):
    des = kb.stent_ceiling("stent_des", date(2026, 11, 20))
    assert des.dec("ceiling_ex_gst") == Decimal("39186.03")
    assert kb.stent_ceiling("stent_bms", date(2026, 11, 20)).dec("ceiling_ex_gst") == Decimal("10762.15")
    assert kb.gst_rate("medical_device", date(2026, 11, 20)).dec("rate_percent") == Decimal("5")
    assert len(kb.knee_rows(date(2026, 11, 20))) == 15


def test_rules_are_date_aware(kb):
    assert kb.stent_ceiling("stent_des", date(2026, 3, 31)) is None      # 2025 notification not loaded
    assert kb.gst_rate("medical_device", date(2025, 9, 21)) is None       # before GST 2.0
    assert kb.knee_rows(date(2027, 1, 16)) == []                          # past the last extension


def test_every_row_and_rule_has_a_source(kb):
    for rows in kb.tables.values():
        for r in rows:
            assert r.data["source_id"] in kb.sources and r.data["source_ref"].strip()
    for rule in kb.rules:
        assert all(s in kb.sources for s in rule.sources)


def test_unsourced_row_is_refused(tmp_path, kb):
    d = tmp_path / "data"
    shutil.copytree(kb.dir, d)
    p = d / "reference" / "stent_ceilings.csv"
    p.write_text(p.read_text() + "STENT-X,stent_des,Fake,1.00,1 unit,2026-04-01,,unknown_source,row\n")
    with pytest.raises(DataError):
        KnowledgeBase(d)


def test_row_without_reference_is_refused(tmp_path, kb):
    d = tmp_path / "data"
    shutil.copytree(kb.dir, d)
    p = d / "reference" / "stent_ceilings.csv"
    p.write_text(p.read_text() + "STENT-Y,stent_des,Fake,1.00,1 unit,2026-04-01,,nppa_stent_2026,\n")
    with pytest.raises(DataError):
        KnowledgeBase(d)
