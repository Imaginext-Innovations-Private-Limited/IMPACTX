"""Kannada, Tamil and Telugu get a natural server voice through edge-tts.

The real service needs internet, so these tests put a stand-in `edge_tts` module in place and
check the wiring: which backend is chosen, which voice is asked for, and the fallbacks.
"""

import sys
import types

import pytest

from kk.voice import tts


class _FakeCommunicate:
    calls = []

    def __init__(self, text, voice, rate="+0%"):
        _FakeCommunicate.calls.append((text, voice, rate))

    async def stream(self):
        yield {"type": "WordBoundary"}
        yield {"type": "audio", "data": b"ID3fake-mp3-"}
        yield {"type": "audio", "data": b"bytes"}


@pytest.fixture()
def fake_edge(monkeypatch):
    mod = types.ModuleType("edge_tts")
    mod.Communicate = _FakeCommunicate
    monkeypatch.setitem(sys.modules, "edge_tts", mod)
    monkeypatch.setenv("KK_TTS", "auto")
    monkeypatch.delenv("KK_TTS_ONLINE", raising=False)
    monkeypatch.delenv("KK_BHASHINI_USER_ID", raising=False)
    _FakeCommunicate.calls.clear()
    return mod


@pytest.mark.parametrize("lang,voice", [("kn", "kn-IN-SapnaNeural"), ("ta", "ta-IN-PallaviNeural"),
                                        ("te", "te-IN-ShrutiNeural")])
def test_kannada_tamil_telugu_speak_with_a_natural_voice(fake_edge, lang, voice):
    assert tts.backends(lang)[0] == "edge"
    assert tts.quality(lang) == "natural"
    audio, media = tts.synthesize(["ಮೊದಲ ವಾಕ್ಯ.", "ಎರಡನೇ ವಾಕ್ಯ."], lang)
    assert media == "audio/mpeg" and audio == b"ID3fake-mp3-bytes"
    text, used, rate = _FakeCommunicate.calls[-1]
    assert used == voice and "\n" in text and rate == f"{tts.EDGE_PACE:+d}%"


def test_online_voice_can_be_switched_off(fake_edge, monkeypatch):
    monkeypatch.setenv("KK_TTS_ONLINE", "0")
    assert "edge" not in tts.backends("ta")


def test_failed_online_voice_falls_through(fake_edge, monkeypatch):
    class Broken(_FakeCommunicate):
        async def stream(self):
            raise OSError("no internet")
            yield  # pragma: no cover
    fake_edge.Communicate = Broken
    monkeypatch.setattr(tts, "backends", lambda lang: ["edge"])
    with pytest.raises(tts.TTSUnavailable, match="online voice failed"):
        tts.synthesize("வணக்கம்.", "ta")


def test_every_language_has_an_online_voice():
    assert set(tts.EDGE_VOICE) == set(tts.LANGS)
