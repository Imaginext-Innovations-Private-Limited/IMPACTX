"""Explainer chat, GST-shaped arithmetic gaps, speech backends, and real public bill lines."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kk.chat import detect_intent, reply
from kk.compose.render import fmt_figure, plain
from kk.voice import tts

ROOT = Path(__file__).resolve().parents[1]
BILLS = ROOT / "tests/fixtures/sample_bills"


def _run(auditor, name):
    d = json.loads((BILLS / f"{name}.json").read_text(encoding="utf-8"))
    return auditor.audit_structured(d["bill"], d["answers"])


@pytest.mark.parametrize("lang,question,intent", [
    ("en", "What should I do now?", "next"), ("hi", "क्या मुझे पैसे वापस मिलेंगे?", "remedy"),
    ("kn", "ಏನನ್ನು ಪರಿಶೀಲಿಸಲು ಆಗಲಿಲ್ಲ?", "coverage"), ("gu", "GST કેમ ઉમેરાય છે?", "gst"),
    ("ta", "இது சரி என்று எனக்கு எப்படித் தெரியும்?", "trust"), ("te", "ఏ ఛార్జీలకు అనుమతి లేదు?", "overcharge"),
])
def test_intents_in_six_languages(lang, question, intent):
    assert detect_intent(question) == intent


def test_every_answer_number_is_a_figure(auditor):
    s = _run(auditor, "bill1_cardiac_cash")
    for lang in ("en", "hi", "kn", "gu", "ta", "te"):
        for intent in ("summary", "overcharge", "remedy", "coverage", "gst", "trust", "amber"):
            r = reply(s.result, None, lang, auditor.kb, intent=intent, ai=False)
            for p in r["answer"]:
                for seg in p:
                    if "fig" in seg:
                        assert seg["t"] == fmt_figure(s.result.figures[seg["fig"]])
            assert r["speech_lines"] and r["suggestions"]


def test_line_question_and_chip(auditor):
    s = _run(auditor, "bill1_cardiac_cash")
    r = reply(s.result, "why is the stent overcharged?", "en", auditor.kb, ai=False)
    text = " ".join(plain(p) for p in r["answer"])
    assert r["intent"] == "line" and "₹16,854.67" in text and "Drug Eluting" in text
    chip = next(c for c in r["suggestions"] if c["id"].startswith("line:"))
    r2 = reply(s.result, None, "ta", auditor.kb, intent=chip["id"], ai=False)
    assert r2["lang"] == "ta" and r2["answer"]


def test_next_steps_use_official_numbers(auditor):
    s = _run(auditor, "bill1_cardiac_cash")
    text = " ".join(plain(p) for p in reply(s.result, "what should I do", "en", auditor.kb, ai=False)["answer"])
    assert "1800-111-255" in text and "1915" in text


def test_refuses_medical_and_legal(auditor):
    s = _run(auditor, "bill1_cardiac_cash")
    assert reply(s.result, "should I take aspirin?", "en", auditor.kb, ai=False)["intent"] == "refused"


def test_model_rewording_must_pass_the_verifier(auditor):
    s = _run(auditor, "bill1_cardiac_cash")
    part = s.result.hospital_fig            # the remedy answer shows the hospital part, so it must stay
    good = lambda p: f"You can ask the hospital to refund [total:{part}]. Ask at the billing desk first."
    r = reply(s.result, "will I get money back", "en", auditor.kb, ai=True, llm=good)
    assert r["source"] == "llm" and "₹20,469.34" in plain(r["answer"][0])
    bad = lambda p: "You will surely get 25000 rupees back."
    assert reply(s.result, "will I get money back", "en", auditor.kb, ai=True, llm=bad)["source"] == "rules"


def test_chat_api_and_audio(auditor):
    from kk.api import app
    c = TestClient(app)
    d = json.loads((BILLS / "bill2_knee_pmjay.json").read_text(encoding="utf-8"))
    sid = c.post("/api/audit-structured", json={"bill": d["bill"], "answers": d["answers"]}).json()["id"]
    assert c.get(f"/api/audit/{sid}/chat?lang=te").json()["suggestions"]
    r = c.post(f"/api/audit/{sid}/chat", json={"message": "क्या मुझे पैसे वापस मिलेंगे?", "lang": "hi", "ai": False}).json()
    assert r["intent"] == "remedy" and r["n"] == 0
    joined = " ".join(plain(p) for p in r["answer"])
    assert "₹1,11,698.00" in joined and "₹9,543.56" in joined
    if tts.backend("hi"):
        a = c.get(f"/api/audit/{sid}/chat/0/audio")
        assert a.status_code == 200 and len(a.content) > 5000
    assert c.get(f"/api/audit/{sid}/chat/9/audio").status_code == 404


# ---------------------------------------------------------------- arithmetic on real-bill patterns
def test_gst_shaped_gap_is_a_question_not_an_overcharge(auditor):
    from tests.conftest import bill
    lines = [{"description": "Inj Pantoprazole 40mg", "section": "pharmacy", "qty": "2", "rate": "100", "amount": "224"},   # +12%
             {"description": "PTCA Guide Wire", "section": "consumables", "qty": "2", "rate": "3500", "amount": "7500"}]
    s = auditor.audit_structured(bill(lines), {"payer": "cash", "state": "other"})
    by = {f.line_id: f for f in s.result.findings if f.rule_id == "ARI-QTYRATE"}
    l1, l2 = s.bill.lines[0].id, s.bill.lines[1].id
    assert by[l1].verdict.value == "amber" and by[l1].message_key == "ari_qtyrate_tax"
    assert by[l2].verdict.value == "red"


def test_rate_column_holding_the_line_total_is_not_flagged(auditor):
    from tests.conftest import bill
    lines = [{"description": "K Wire 1.8mm", "section": "implant", "qty": "4", "rate": "1520", "amount": "1520"}]
    s = auditor.audit_structured(bill(lines), {"payer": "cash", "state": "other"})
    assert not [f for f in s.result.findings if f.rule_id == "ARI-QTYRATE"]


def test_real_public_lines_are_not_matched_as_capped_items():
    out = subprocess.run([sys.executable, str(ROOT / "scripts/eval_public_lines.py"), "--sample"],
                         capture_output=True, text=True, check=True).stdout
    assert "0 of 19 lines" in out and "more_than_qty_x_rate" not in out


# ---------------------------------------------------------------- speech backends
def test_backend_order_and_fallback(monkeypatch):
    monkeypatch.setenv("KK_TTS", "auto")
    monkeypatch.delenv("KK_BHASHINI_USER_ID", raising=False)
    monkeypatch.setenv("KK_TTS_ONLINE", "0")   # the online voice is tested in test_voice_online.py
    monkeypatch.setattr(tts, "_neural_ready", lambda lang: lang in ("en", "hi", "gu"))
    monkeypatch.setattr(tts.shutil, "which", lambda name: "/usr/bin/espeak-ng")
    assert tts.backends("hi")[0] == "neural" and tts.quality("hi") == "natural"
    assert tts.backends("ta") == ["espeak"] and tts.quality("ta") == "basic"
    monkeypatch.setenv("KK_TTS", "off")
    assert tts.backends("hi") == [] and tts.quality("hi") == "none"


def test_neural_falls_back_when_it_fails(monkeypatch):
    monkeypatch.setenv("KK_TTS", "auto")
    monkeypatch.setattr(tts, "backends", lambda lang: ["neural", "espeak"])
    def broken(*a, **k):
        raise tts.TTSUnavailable("model missing")
    monkeypatch.setattr(tts, "_neural", broken)
    if not tts.shutil.which("espeak-ng"):
        pytest.skip("espeak-ng not installed")
    audio, media = tts.synthesize(["नमस्ते।"], "hi")
    assert len(audio) > 1000