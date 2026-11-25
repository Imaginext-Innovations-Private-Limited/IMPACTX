"""v1.5: every language must have spoken audio that plays in ANY browser (no browser voices, no key)."""
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scamshield import voice
from scamshield.languages import LANGUAGE_NAMES, LEVELS
from scamshield.main import app

ROOT = Path(__file__).resolve().parents[1]
BASIC = ROOT / "static" / "voices-basic"
client = TestClient(app)


def _combos():
    spec = importlib.util.spec_from_file_location("gen_basic", ROOT / "tools" / "generate_basic_voices.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.combos()


def _is_mp3(data: bytes) -> bool:
    return len(data) > 2000 and (data.startswith(b"ID3") or (data[0] == 0xFF and data[1] & 0xE0 == 0xE0))


def test_catalogue_covers_all_languages_levels_and_topics():
    combos = _combos()
    assert len(combos) == len(LANGUAGE_NAMES) * (len(LEVELS) + len(voice.TOPICS) - 1)
    assert {c[0] for c in combos} == set(LANGUAGE_NAMES)


@pytest.mark.parametrize("language,level,topic", _combos())
def test_basic_clip_exists_and_is_valid_mp3(language, level, topic):
    path = BASIC / language / f"{level}-{topic}.mp3"
    assert path.is_file(), f"missing {path}"
    assert _is_mp3(path.read_bytes())


@pytest.mark.parametrize("language", sorted(LANGUAGE_NAMES))
@pytest.mark.parametrize("level", LEVELS)
def test_every_level_has_a_general_clip_for_any_topic_fallback(language, level):
    # The app falls back to <level>-generic when a topic clip is absent (e.g. caution + topic).
    assert (BASIC / language / f"{level}-generic.mp3").is_file()


def test_basic_clips_are_served_over_http_as_audio():
    for lang in ("or", "mr", "bn"):
        r = client.get(f"/static/voices-basic/{lang}/high-generic.mp3")
        assert r.status_code == 200 and _is_mp3(r.content)


def test_bundled_indic_fonts_exist_and_are_referenced():
    css = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")
    for script in ("devanagari", "bengali", "oriya", "telugu", "kannada"):
        for weight in (400, 700):
            f = ROOT / "static" / "fonts" / f"noto-sans-{script}-{weight}.woff2"
            assert f.is_file() and f.stat().st_size > 5000
            assert f"noto-sans-{script}-{weight}.woff2" in css
    r = client.get("/static/fonts/noto-sans-oriya-400.woff2")
    assert r.status_code == 200 and r.content[:4] == b"wOF2"


def test_app_js_falls_back_to_basic_clips_and_survives_missing_browser_voice():
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    assert "/static/voices-basic/" in js and "findBasicClip" in js
    assert "utterance.onstart" in js  # watchdog for silent browser voices


def test_basic_clips_never_contain_user_text():
    # Scripts come only from the fixed catalogue.
    for lang, level, topic in _combos():
        text = voice.voice_text(lang, level, topic)
        assert "http" not in text and "@" not in text
