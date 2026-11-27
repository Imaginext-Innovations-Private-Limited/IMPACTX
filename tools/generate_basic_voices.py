"""Build the BUNDLED basic offline warnings (static/voices-basic/<lang>/<level>-<topic>.mp3).

These are a last-resort fallback so a spoken warning plays in EVERY browser, on every
laptop, with no internet and no API key, including Odia and Marathi, for which browsers
rarely ship a voice. The voice is a robotic offline synthesizer (eSpeak NG). Better
saved/AI/human audio is always preferred by the app when it exists.

Only the app's fixed, prewritten warning text is spoken. Nothing user-supplied is used.

Maintainers only (not needed to run the app):
    pip install espeakng-loader      # bundles the eSpeak NG library and language data
    # ffmpeg must be on PATH (MP3 encoding)
    python tools/generate_basic_voices.py            # regenerate everything
"""
from __future__ import annotations

import argparse
import array
import ctypes
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scamshield import voice  # noqa: E402
from scamshield.languages import LEVELS  # noqa: E402

ESPEAK_VOICE = {"en": "en-gb-x-rp", "hi": "hi", "bn": "bn", "kn": "kn", "te": "te", "or": "or", "mr": "mr", "ta": "ta", "ml": "ml", "gu": "gu", "pa": "pa"}
OUT = ROOT / "static" / "voices-basic"


def combos() -> list[tuple[str, str, str]]:
    """Every (language, level, topic) the app can ask for, minus topic clips for 'caution'
    (those reuse the general caution clip)."""
    rows = []
    for lang in ESPEAK_VOICE:
        for level in LEVELS:
            rows.append((lang, level, "generic"))
        for topic in voice.TOPICS:
            if topic != "generic":
                rows.append((lang, "high", topic))
    return rows


class Engine:
    def __init__(self) -> None:
        import espeakng_loader
        self.lib = ctypes.CDLL(espeakng_loader.get_library_path())
        cb_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)
        self.lib.espeak_Initialize.restype = ctypes.c_int
        self.lib.espeak_Initialize.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        self.rate = self.lib.espeak_Initialize(1, 0, espeakng_loader.get_data_path().encode(), 0)
        self.buf = array.array("h")

        def _cb(wav, n, _events):
            if wav and n > 0:
                self.buf.extend(wav[:n])
            return 0
        self._cb = cb_type(_cb)  # keep a reference so it is not garbage collected
        self.lib.espeak_SetSynthCallback(self._cb)

    def to_wav(self, text: str, language: str, path: Path, wpm: int = 135) -> None:
        del self.buf[:]
        if self.lib.espeak_SetVoiceByName(ESPEAK_VOICE[language].encode()) != 0:
            raise RuntimeError(f"eSpeak voice missing for {language}")
        self.lib.espeak_SetParameter(1, wpm, 0)
        data = text.encode("utf-8")
        self.lib.espeak_Synth(data, len(data) + 1, 0, 0, 0, 1, None, None)
        self.lib.espeak_Synchronize()
        if len(self.buf) < self.rate:  # under one second means nothing was spoken
            raise RuntimeError("no audio produced")
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(self.rate)
            w.writeframes(self.buf.tobytes())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--only", nargs="+", choices=tuple(ESPEAK_VOICE), help="limit to some languages")
    args = parser.parse_args()
    if not shutil.which("ffmpeg"):
        print("ffmpeg is required on PATH.")
        return 2
    engine = Engine()
    failures = 0
    rows = [r for r in combos() if not args.only or r[0] in args.only]
    with tempfile.TemporaryDirectory() as tmp:
        for i, (lang, level, topic) in enumerate(rows, 1):
            target = OUT / lang / f"{level}-{topic}.mp3"
            target.parent.mkdir(parents=True, exist_ok=True)
            wav = Path(tmp) / "clip.wav"
            try:
                engine.to_wav(voice.voice_text(lang, level, topic), lang, wav)
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-ac", "1", "-ar", "22050",
                                "-b:a", "24k", "-codec:a", "libmp3lame", str(target)], check=True)
                print(f"[{i}/{len(rows)}] OK   {target.relative_to(ROOT)}", flush=True)
            except Exception as exc:  # report and continue
                failures += 1
                print(f"[{i}/{len(rows)}] FAIL {lang}/{level}-{topic}: {exc}", flush=True)
    print(f"Done. {len(rows) - failures}/{len(rows)} clips.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
