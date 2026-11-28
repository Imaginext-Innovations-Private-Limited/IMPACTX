"""Coverage, crosswalk, remedies and GST basis: the claims the deck makes are tested here."""

import json
import re
import shutil
import string
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from kk.compose.render import CATALOG, plain
from kk.compose.verifier import verify
from kk.guard import detect_language

ROOT = Path(__file__).resolve().parents[1]
BILLS = ROOT / "tests/fixtures/sample_bills"


def _run(auditor, name):
    d = json.loads((BILLS / f"{name}.json").read_text(encoding="utf-8"))
    return auditor.audit_structured(d["bill"], d["answers"])


def _v(s, fid):
    return s.result.figures[fid].value if fid else None


# ---------------------------------------------------------------- remedies: refund vs grievance
def test_remedy_split_adds_up_and_names_who_decides(auditor):
    s1 = _run(auditor, "bill1_cardiac_cash")
    assert _v(s1, s1.result.hospital_fig) == Decimal("20469.34") and s1.result.scheme_fig is None
    s2 = _run(auditor, "bill2_knee_pmjay")
    assert s2.result.hospital_fig is None
    assert _v(s2, s2.result.scheme_fig) == Decimal("111698.00")
    assert _v(s2, s2.result.fallback_fig) == Decimal("9543.56")   # price caps alone: 7858.91 + 900.63 + 784.02
    s3 = _run(auditor, "bill3_interim_photo")
    assert _v(s3, s3.result.scheme_fig) == Decimal("262000.00")
    for s in (s1, s2, s3):
        parts = (_v(s, s.result.hospital_fig) or 0) + (_v(s, s.result.scheme_fig) or 0)
        assert parts == _v(s, s.result.recoverable_fig)


def test_scheme_amount_is_called_a_grievance_not_a_refund(auditor):
    s = _run(auditor, "bill2_knee_pmjay")
    text = " ".join(plain(x) for x in auditor.view(s, "en")["summary"])
    assert "grievance, not an automatic refund" in text and "State Health Agency decides" in text
    assert "Possible refund" not in text


# ---------------------------------------------------------------- coverage and crosswalk
def test_coverage_is_reported_not_every_line(auditor):
    s = _run(auditor, "bill1_cardiac_cash")
    c = s.result.coverage
    assert (_v(s, c["rule"]), _v(s, c["lines"]), _v(s, c["basic"])) == (3, 12, 9)
    assert _v(s, c["share"]) == Decimal("57.57")
    lines = [plain(x) for x in auditor.view(s, "en")["coverage"]]
    assert lines[0] == "Matched to an official price limit or scheme rule: 3 of 12 lines, 57.57% of the billed amount."


def test_crosswalk_explains_each_line(auditor):
    s = _run(auditor, "bill1_cardiac_cash")
    by_desc = {l.description: s.result.crosswalk[l.id] for l in s.bill.lines}
    x = by_desc["Coronary Stent Xience Alpine 3.5x18"]
    assert x["status"] == "rule" and x["matches"][0]["reason"] == "match_stent_brand"
    assert x["matches"][0]["row_id"] == "STENT-DES-2026" and x["matches"][0]["source_id"] == "nppa_stent_2026"
    assert by_desc["PTCA Guide Wire 0.014"]["status"] == "basic"
    assert by_desc["Tab Clopidogrel 75mg"]["reason"] == "nomatch_medicine"
    assert by_desc["Room Rent Twin Sharing"]["reason"] == "nomatch_room"


def test_cash_denial_covers_every_line(auditor):
    s = _run(auditor, "bill3_interim_photo")
    assert all(x["status"] == "rule" for x in s.result.crosswalk.values())


def test_crosswalk_on_hospital_published_text_never_inflates():
    sys.path.insert(0, str(ROOT / "scripts"))
    import eval_crosswalk
    r = eval_crosswalk.main()
    assert r["with"]["recognised"] == r["with"]["n"] == 67
    assert r["with"]["inflates"] == 0 and r["without"]["inflates"] == 0
    assert r["knee"]["component_ok"] == r["knee"]["n"]


# ---------------------------------------------------------------- GST basis
def test_gst_basis_is_sourced_on_every_cap(auditor):
    s = _run(auditor, "bill1_cardiac_cash")
    view = auditor.view(s, "en")
    notes = [p.get("note", "") for p in view["proofs"].values() if p["role"] == "allowed_amount"]
    assert any("exclusive of Goods and Services Tax as applicable" in n for n in notes)
    assert auditor.kb.source_field("nppa_knee_2024", "tax_basis") == "exclusive_of_gst"


# ---------------------------------------------------------------- six languages
def test_six_catalogs_have_same_keys_slots_and_no_digits():
    keys = set(CATALOG["en"])
    for lang, cat in CATALOG.items():
        assert set(cat) == keys, lang
        for k, v in cat.items():
            assert not re.search(r"\d", v), (lang, k)
            slots = {f for _, f, _, _ in string.Formatter().parse(v) if f}
            en = {f for _, f, _, _ in string.Formatter().parse(CATALOG["en"][k]) if f}
            assert slots == en, (lang, k)


def test_tamil_telugu_detection_and_verifier():
    assert detect_language("இதய அறுவை சிகிச்சை") == "ta"
    assert detect_language("గుండె ఆపరేషన్") == "te"
    assert not verify("உங்களுக்கு ௧௬ ஆயிரம்", {}, "ta").ok      # Tamil digits and a magnitude word
    assert not verify("మీకు వెయ్యి తిరిగి", {}, "te").ok
    assert verify("மருத்துவமனையிடம் கேளுங்கள்.", {}, "ta").ok


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_interface_text_complete_in_six_languages():
    js = ("global.window={};require(process.argv[1]);const I=window.KK_I18N;const en=Object.keys(I.en);"
          "console.log(JSON.stringify(Object.fromEntries(Object.keys(I).map(l=>[l,en.filter(k=>!(k in I[l]))]))))")
    out = json.loads(subprocess.run(["node", "-e", js, str(ROOT / "kk/web/i18n.js")], capture_output=True,
                                    text=True, check=True).stdout)
    assert set(out) == {"en", "hi", "kn", "gu", "ta", "te"}
    assert all(not missing for missing in out.values()), out


@pytest.mark.parametrize("lang", ["en", "hi", "kn", "gu", "ta", "te"])
def test_letters_in_every_language(auditor, lang):
    from kk.grievance import letters
    s = _run(auditor, "bill1_cardiac_cash")
    out = letters(s.result, lang, auditor.kb.dir)
    assert out and all(lang in l["letters"] for l in out)
    nppa = next(l for l in out if l["channel"] == "nppa")
    assert "₹16,854.67" in nppa["letters"][lang]
