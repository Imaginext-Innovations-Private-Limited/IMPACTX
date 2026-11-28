"""Server-side speech, for phones and laptops with no good voice for a language.

The web app speaks with the device's own voice when it has a natural one; otherwise it asks
the server. For each language the server takes the first backend that works (KK_TTS="auto"):

  bhashini  Government of India Bhashini TTS, natural voices in all six languages. Needs
            KK_BHASHINI_USER_ID and KK_BHASHINI_API_KEY and internet.
  neural    Offline neural voices run with sherpa-onnx (pip install sherpa-onnx==1.12.40):
            English (Piper jenny_dioco), Hindi (Piper priyamvada, trained on AI4Bharat data),
            Gujarati (Mimic3 CMU Indic). Downloaded once from the sherpa-onnx GitHub releases
            (python scripts/fetch_voices.py), then fully offline. See each model card for its
            licence; the Hindi voice is CC BY-NC-SA 4.0 (non-commercial).
  edge      Microsoft Edge "Read aloud" neural voices through the edge-tts package
            (pip install edge-tts), natural in all six languages and the voice that makes Kannada,
            Tamil and Telugu speak on laptops whose browser has no voice for them (Chrome on
            Windows, most Linux). Needs internet, no account. It receives only the spoken summary
            (names, phone and Aadhaar numbers are already masked). KK_TTS_ONLINE=0 turns it off.
  gtts      Google Translate's voices through the gTTS package (pip install gTTS), natural in
            all six languages. Needs internet; unofficial, so it is used only when chosen
            (KK_TTS_GTTS=1) and never sent anything but the spoken summary.
  espeak    espeak-ng, offline and always available, but robotic: the last resort.

KK_TTS can also name one backend ("neural", "espeak", ...) or "off" (captions only).
The text spoken is the script built from verified figures; nothing is generated here.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import urllib.request
from functools import lru_cache
from pathlib import Path

LANGS = ("en", "hi", "kn", "gu", "ta", "te")
ESPEAK_VOICE = {"en": "en-gb", "hi": "hi", "kn": "kn", "gu": "gu", "ta": "ta", "te": "te"}
VOICE_DIR = Path(os.environ.get("KK_TTS_DIR", Path.home() / ".cache" / "kharcha-kavach" / "tts"))
NEURAL = {  # language -> (sherpa-onnx release name, model file)
    "en": ("vits-piper-en_GB-jenny_dioco-medium", "en_GB-jenny_dioco-medium.onnx"),
    "hi": ("vits-piper-hi_IN-priyamvada-medium", "hi_IN-priyamvada-medium.onnx"),
    "gu": ("vits-mimic3-gu_IN-cmu-indic_low", "gu_IN-cmu-indic_low.onnx"),
}
NEURAL_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/{name}.tar.bz2"
GAP_S = 0.55        # pause between sentences: easier to follow than one long stream
NEURAL_PACE = 1.12  # a little slower than the model's natural pace
EDGE_VOICE = {  # Microsoft neural voices, one per language (female voices, clear at slow pace)
    "en": "en-IN-NeerjaNeural", "hi": "hi-IN-SwaraNeural", "kn": "kn-IN-SapnaNeural",
    "gu": "gu-IN-DhwaniNeural", "ta": "ta-IN-PallaviNeural", "te": "te-IN-ShrutiNeural",
}
EDGE_PACE = -8      # percent: a little slower than the voice's default
BHASHINI_CONFIG_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
BHASHINI_PIPELINE = os.environ.get("KK_BHASHINI_PIPELINE", "64392f96daac500b55c543cd")


class TTSUnavailable(RuntimeError):
    pass


def _neural_ready(lang: str) -> bool:
    if lang not in NEURAL:
        return False
    try:
        import sherpa_onnx  # noqa: F401
    except ImportError:
        return False
    name, model = NEURAL[lang]
    return (VOICE_DIR / name / model).exists()


def _edge_ok() -> bool:
    if os.environ.get("KK_TTS_ONLINE", "1") == "0":
        return False
    try:
        import edge_tts  # noqa: F401
        return True
    except ImportError:
        return False


def _gtts_ok() -> bool:
    if os.environ.get("KK_TTS_GTTS") != "1":
        return False
    try:
        import gtts  # noqa: F401
        return True
    except ImportError:
        return False


def backends(lang: str) -> list[str]:
    """Backends to try for a language, best first."""
    want = os.environ.get("KK_TTS", "auto").lower()
    has_bhashini = bool(os.environ.get("KK_BHASHINI_USER_ID") and os.environ.get("KK_BHASHINI_API_KEY"))
    avail = {"bhashini": has_bhashini, "neural": _neural_ready(lang), "edge": _edge_ok(),
             "gtts": _gtts_ok(),
             "espeak": shutil.which("espeak-ng") is not None}
    if want == "off":
        return []
    if want != "auto":
        return [want] if avail.get(want) else []
    return [b for b in ("bhashini", "neural", "edge", "gtts", "espeak") if avail[b]]


def backend(lang: str = "hi") -> str | None:
    b = backends(lang)
    return b[0] if b else None


def quality(lang: str) -> str:
    """'natural' when a natural voice will speak this language, 'basic' for espeak, 'none'."""
    b = backend(lang)
    return "none" if b is None else ("basic" if b == "espeak" else "natural")


def synthesize(lines: list[str] | str, lang: str, rate: float = 1.0) -> tuple[bytes, str]:
    """Speak each sentence separately and join the audio; return (bytes, media type).

    Sentence by sentence keeps long inputs reliable and puts a clear pause between sentences.
    The first backend that works for the language is used. MP3 when ffmpeg is installed.
    """
    if lang not in LANGS:
        raise TTSUnavailable(f"unsupported language {lang}")
    lines = [lines] if isinstance(lines, str) else [x for x in lines if x.strip()]
    errors = []
    for b in backends(lang):
        try:
            if b == "edge":
                # one request for the whole script; a new line makes the voice pause between sentences
                return _edge("\n".join(lines), lang, rate), "audio/mpeg"
            if b == "neural":
                wavs = [_neural(x, lang, rate) for x in lines]
            elif b == "espeak":
                wavs = [_espeak(x, lang, rate) for x in lines]
            elif b == "bhashini":
                wavs = [_bhashini(x, lang) for x in lines]
            else:
                wavs = [_gtts(x, lang) for x in lines]
            wav = _join_wavs(wavs)
            mp3 = _to_mp3(wav)
            return (mp3, "audio/mpeg") if mp3 else (wav, "audio/wav")
        except TTSUnavailable as e:
            errors.append(str(e))
    raise TTSUnavailable("no server speech backend worked: " + "; ".join(errors) if errors else
                         "no server speech backend is configured")


@lru_cache(maxsize=4)
def _neural_engine(lang: str):
    import sherpa_onnx
    name, model = NEURAL[lang]
    d = VOICE_DIR / name
    cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=str(d / model), lexicon="", tokens=str(d / "tokens.txt"),
                                                   data_dir=str(d / "espeak-ng-data"), length_scale=NEURAL_PACE),
        num_threads=2, provider="cpu"))
    return sherpa_onnx.OfflineTts(cfg)


def _neural(text: str, lang: str, rate: float) -> bytes:
    import io
    import wave
    a = _neural_engine(lang).generate(text, sid=0, speed=max(0.5, min(rate, 2.0)))
    if not len(a.samples):
        raise TTSUnavailable("neural voice produced no audio")
    import array
    pcm = array.array("h", (int(max(-1.0, min(1.0, x)) * 32767) for x in a.samples))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(a.sample_rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def _edge(text: str, lang: str, rate: float) -> bytes:
    """Microsoft Edge neural voice (online). Returns MP3 bytes; no ffmpeg needed."""
    try:
        import asyncio
        import edge_tts
        pct = EDGE_PACE + int(round((max(0.5, min(rate, 2.0)) - 1) * 100))

        async def run() -> bytes:
            out = bytearray()
            comm = edge_tts.Communicate(text, EDGE_VOICE[lang], rate=f"{pct:+d}%")
            async for chunk in comm.stream():
                if chunk.get("type") == "audio":
                    out.extend(chunk["data"])
            return bytes(out)

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            audio = asyncio.run(run())
        else:  # called from inside an event loop: run in a worker thread with its own loop
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(1) as ex:
                audio = ex.submit(asyncio.run, run()).result(timeout=120)
        if not audio:
            raise TTSUnavailable("online voice returned no audio")
        return audio
    except TTSUnavailable:
        raise
    except Exception as e:  # offline, blocked network, package missing
        raise TTSUnavailable(f"online voice failed: {e}") from e


def _gtts(text: str, lang: str) -> bytes:
    """Google Translate voice (online), converted to WAV so sentences can be joined."""
    try:
        import io
        from gtts import gTTS
        mp3 = io.BytesIO()
        gTTS(text=text, lang=lang, tld="co.in").write_to_fp(mp3)
        proc = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "mp3", "-i", "pipe:0",
                               "-ac", "1", "-ar", "22050", "-f", "wav", "pipe:1"],
                              input=mp3.getvalue(), capture_output=True, timeout=60, check=False)
        if proc.returncode != 0 or not proc.stdout:
            raise TTSUnavailable("could not convert gTTS audio (is ffmpeg installed?)")
        return proc.stdout
    except TTSUnavailable:
        raise
    except Exception as e:  # network refused, rate limit, package missing
        raise TTSUnavailable(f"gTTS failed: {e}") from e


def _join_wavs(wavs: list[bytes], gap_s: float = GAP_S) -> bytes:
    """Concatenate PCM WAVs with a short pause between sentences (resampled to the first one's rate)."""
    import io
    import wave
    frames, params = [], None
    for w in wavs:
        with wave.open(io.BytesIO(_fix_header(w))) as r:
            if params is None:
                params = r.getparams()
            elif r.getframerate() != params.framerate:
                raise TTSUnavailable("sentence audio came back at different sample rates")
            frames.append(r.readframes(r.getnframes()))
    if params is None:
        raise TTSUnavailable("no audio produced")
    silence = b"\x00" * int(params.framerate * gap_s) * params.sampwidth * params.nchannels
    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        out.setnchannels(params.nchannels)
        out.setsampwidth(params.sampwidth)
        out.setframerate(params.framerate)
        out.writeframes(silence.join(frames))
    return buf.getvalue()


def _fix_header(w: bytes) -> bytes:
    """espeak-ng --stdout writes placeholder sizes; rewrite RIFF and data sizes from the real length."""
    import struct
    if w[:4] != b"RIFF":
        return w
    i = w.find(b"data")
    if i < 0:
        return w
    n = len(w) - (i + 8)
    return w[:4] + struct.pack("<I", len(w) - 8) + w[8:i + 4] + struct.pack("<I", n) + w[i + 8:]


def _to_mp3(wav: bytes) -> bytes | None:
    if not shutil.which("ffmpeg") or os.environ.get("KK_TTS_FORMAT", "mp3") != "mp3":
        return None
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "wav", "-i", "pipe:0",
                           "-ac", "1", "-b:a", "48k", "-f", "mp3", "pipe:1"],
                          input=wav, capture_output=True, timeout=120, check=False)
    return proc.stdout if proc.returncode == 0 and proc.stdout else None


def _espeak(text: str, lang: str, rate: float) -> bytes:
    wpm = str(int(135 * max(0.5, min(rate, 2.0))))   # slower than espeak's default: easier to follow
    proc = subprocess.run(["espeak-ng", "-v", ESPEAK_VOICE[lang], "-s", wpm, "-g", "4", "--stdout"],
                          input=text.encode("utf-8"), capture_output=True, timeout=60, check=False)
    if proc.returncode != 0 or not proc.stdout:
        raise TTSUnavailable("espeak-ng failed: " + proc.stderr.decode(errors="ignore")[:200])
    return proc.stdout


def _post(url: str, body: dict, headers: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def _bhashini(text: str, lang: str) -> bytes:
    """Bhashini ULCA pipeline: fetch the TTS service for the language, then run it."""
    try:
        cfg = _post(BHASHINI_CONFIG_URL,
                    {"pipelineTasks": [{"taskType": "tts", "config": {"language": {"sourceLanguage": lang}}}],
                     "pipelineRequestConfig": {"pipelineId": BHASHINI_PIPELINE}},
                    {"userID": os.environ["KK_BHASHINI_USER_ID"], "ulcaApiKey": os.environ["KK_BHASHINI_API_KEY"]})
        service_id = cfg["pipelineResponseConfig"][0]["config"][0]["serviceId"]
        ep = cfg["pipelineInferenceAPIEndPoint"]
        key = ep["inferenceApiKey"]
        out = _post(ep["callbackUrl"],
                    {"pipelineTasks": [{"taskType": "tts", "config": {
                        "language": {"sourceLanguage": lang}, "serviceId": service_id,
                        "gender": "female", "samplingRate": 22050}}],
                     "inputData": {"input": [{"source": text}]}},
                    {key["name"]: key["value"]})
        return base64.b64decode(out["pipelineResponse"][0]["audio"][0]["audioContent"])
    except Exception as e:  # network, auth or schema change: fall back to captions
        raise TTSUnavailable(f"Bhashini TTS failed: {e}") from e
