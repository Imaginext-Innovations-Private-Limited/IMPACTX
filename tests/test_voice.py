"""Spoken summary: same figures as the screen, in six languages, with no number from anywhere else."""

import json
import re
import shutil
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kk.compose.render import fmt_figure
from kk.voice import build, english_words, spoken_amount

BILLS = Path(__file__).resolve().parent / "fixtures/sample_bills"
LANGS = ["en", "hi", "kn", "gu", "ta", "te"]
NAMES = ["bill1_cardiac_cash", "bill2_knee_pmjay", "bill3_interim_photo"]


def _run(auditor, name):
    d = json.loads((BILLS / f"{name}.json").read_text(encoding="utf-8"))
    return auditor.audit_structured(d["bill"], d["answers"])


def test_indian_number_words():
    assert english_words(111698) == "one lakh eleven thousand six hundred and ninety-eight"
    assert english_words(26200000) == "two crore sixty-two lakh"
    assert spoken_amount(Decimal("20469.34"), "en") == \
        "twenty thousand four hundred and sixty-nine rupees and thirty-four paise"
    assert spoken_amount(Decimal("20469.34"), "hi") == "20469 रुपये 34 पैसे"
    assert spoken_amount(Decimal("262000"), "ta") == "262000 ரூபாய்"
    assert spoken_amount(Decimal("500.00"), "te") == "500 రూపాయలు"


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("lang", LANGS)
def test_speech_numbers_come_only_from_figures(auditor, name, lang):
    s = _run(auditor, name)
    v = build(s.result, lang, ai=False)
    assert v["source"] == "template"
    assert len(v["speech_lines"]) == len(v["sentences"])
    for sent in v["sentences"]:
        for seg in sent:
            if "fig" in seg:
                assert seg["t"] == fmt_figure(s.result.figures[seg["fig"]])   # caption = screen
            else:
                assert not re.search(r"\d", seg["say"]), seg   # item sizes like 3.0x28 are not spoken


def test_model_text_is_used_only_when_it_passes_the_verifier(auditor):
    s = _run(auditor, "bill1_cardiac_cash")
    rec = s.result.recoverable_fig
    good = lambda prompt: f"Your bill can be challenged for [total:{rec}]. Ask the hospital to correct it."
    v = build(s.result, "en", ai=True, llm=good)
    assert v["source"] == "llm" and "twenty thousand four hundred and sixty-nine rupees" in v["speech"]
    bad = lambda prompt: "You can get back 20469 rupees."
    assert build(s.result, "en", ai=True, llm=bad)["source"] == "template"


def test_voice_api(auditor):
    from kk.api import app
    c = TestClient(app)
    d = json.loads((BILLS / "bill1_cardiac_cash.json").read_text(encoding="utf-8"))
    sid = c.post("/api/audit-structured", json={"bill": d["bill"], "answers": d["answers"]}).json()["id"]
    r = c.get(f"/api/audit/{sid}/voice?lang=ta&ai=0").json()
    assert r["lang"] == "ta" and r["sentences"] and "server_audio" in r
    assert c.get(f"/api/audit/{sid}/voice?lang=fr").status_code == 400
    if shutil.which("espeak-ng"):
        a = c.get(f"/api/audit/{sid}/voice.audio?lang=te&ai=0")
        assert a.status_code == 200 and a.headers["content-type"] in ("audio/mpeg", "audio/wav") and len(a.content) > 10000
