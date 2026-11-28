"""FastAPI web server. Does not log or store scanned messages by design."""
from __future__ import annotations

import io
import os
import asyncio
import json
import math
import httpx
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict

from . import __version__
from .engine import MAX_TEXT, analyze
from .languages import CONTENT, LEVELS, LANGUAGE_NAMES
from . import voice

BASE_DIR = Path(__file__).resolve().parent.parent
app = FastAPI(title="ScamShield AI", version=__version__,
              description="Privacy-conscious fraud indicator screening. Not a definitive fraud detector.")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

class AnalysisInput(BaseModel):
    text: str = Field(default="", max_length=MAX_TEXT)
    channel: str = "auto"
    language: str = "en"
    cloud_consent: bool = False
    qr_payloads: list[str] | None = Field(default=None, max_length=10)
    email_meta: dict | None = None


class QRPayloadDetail(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    qr_type: str | None = None
    raw: str
    destination: str | None = None
    protocol: str | None = None
    registered_domain: str | None = None
    cross_modal_mismatch: bool | None = None
    mismatch_reason: str | None = None
    upi: dict | None = None
    url_assessment: dict | None = None


class QRAnalysisOut(BaseModel):
    model_config = ConfigDict(extra="allow")
    qr_count: int
    payloads: list[QRPayloadDetail]


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    level: str
    title: str
    summary: str
    score: int
    score_label: str
    indicators: list[dict]
    categories: list[str]
    actions: list[str]
    channel: str
    analysis_mode: str
    qr_analysis: QRAnalysisOut | None = None
    identity: dict | None = None
    engine_contributions: dict | None = None
    live_reputation: dict | None = None

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.get("/api/health")
def health():
    from .training_data import SUSPICIOUS, BENIGN
    from . import live_reputation
    from .url_classifier import threat_db_metadata
    return {"status": "ok", "version": __version__, "privacy": "No content persisted by server",
            "training_samples": len(SUSPICIOUS) + len(BENIGN), "offline_engine": "tfidf-linear-svm-regional-context",
            "groq_configured": bool(os.environ.get("GROQ_API_KEY", "").strip()),
            "live_reputation_configured": live_reputation.configured(),
            "threat_db": threat_db_metadata()}

@app.get("/api/voice-prompts")
def voice_prompts():
    """Static, non-sensitive warnings to record with a consenting native speaker."""
    return {lang: {level: CONTENT[lang]["voice"][i] for i, level in enumerate(LEVELS)}
            for lang in LANGUAGE_NAMES}

class VoiceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: str
    level: str
    topic: str = "generic"


def voice_selection(language, level, topic):
    try:
        voice.voice_text(language, level, topic)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid voice selection") from exc


@app.get("/api/voice/status")
def voice_status(language: str, level: str, topic: str = "generic"):
    voice_selection(language, level, topic)
    return {"cached": bool(voice.cached(language, level, topic)), "configured": voice.configured()}


@app.get("/api/voice/audio")
def cached_voice(language: str, level: str, topic: str = "generic"):
    voice_selection(language, level, topic)
    path = voice.cached(language, level, topic)
    if path is None:
        raise HTTPException(status_code=404, detail="No cached audio")
    return FileResponse(path, media_type="audio/mpeg")


@app.post("/api/voice/generate")
def generate_voice(data: VoiceInput, request: Request):
    # This is a local app. Prevent cross-site browser requests from consuming credits.
    origin = request.headers.get("origin")
    if origin and origin not in {"http://127.0.0.1:8000", "http://localhost:8000"}:
        raise HTTPException(status_code=403, detail="Local origin required")
    if request.headers.get("content-type", "").split(";")[0] != "application/json":
        raise HTTPException(status_code=415, detail="JSON required")
    voice_selection(data.language, data.level, data.topic)
    try:
        voice.synthesize(data.language, data.level, data.topic)
    except voice.VoiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"cached": True}


@app.post("/api/analyze", response_model=AnalysisResponse)
def analyze_message(data: AnalysisInput, request: Request):
    try:
        if data.cloud_consent:
            origin = request.headers.get("origin")
            if origin and origin not in {"http://127.0.0.1:8000", "http://localhost:8000"}:
                raise HTTPException(status_code=403, detail="Local origin required")
        result = analyze(data.text, data.channel, data.language, qr_payloads=data.qr_payloads, email_meta=data.email_meta)
        ind_ids = {i.get("id") for i in result.get("indicators", [])}
        contributions = {
            "local_rules": True,
            "text_ml": result.get("model_signal", "unavailable"),
            "url_ml": "flagged" if ind_ids & {"url_ml_phishing", "url_ml_review", "qr_url_ml_phishing", "qr_url_ml_review"} else "checked",
            "local_threat_db": "matched" if ind_ids & {"url_threat_db", "qr_url_threat_db"} else "checked_no_match",
            "qr_decoder": "decoded" if result.get("qr_analysis") else "none",
            "identity_verifier": "checked" if result.get("identity") else "none",
            "live_url_reputation": "not_requested",
            "cloud_llm": "not_requested",
        }
        if data.cloud_consent:
            from . import live_reputation
            urls = list(result.get("entities", {}).get("urls", []))
            for link in (result.get("identity") or {}).get("hyperlinks", []):
                if link.get("href") and link["href"] not in urls:
                    urls.append(link["href"])
            for p in (result.get("qr_analysis") or {}).get("payloads", []):
                if p.get("url") and p["url"] not in urls:
                    urls.append(p["url"])
            live_res = live_reputation.check_urls_live(urls)
            result["live_reputation"] = live_res
            contributions["live_url_reputation"] = live_res["status"]
            matched_urls = {m["url"] for m in live_res.get("matches", [])}
            for p in (result.get("qr_analysis") or {}).get("payloads", []):
                if p.get("type") in {"url", "apk_download"}:
                    ua = p.setdefault("url_assessment", {})
                    ua["live_reputation_status"] = live_res["status"]
                    ua["live_reputation_matched"] = p.get("url") in matched_urls
            if live_res["status"] == "threat_match":
                for match in live_res["matches"][:3]:
                    result["indicators"].insert(0, {
                        "id": "live_url_threat",
                        "title": "Live URL reputation matched a verified threat",
                        "explanation": f"Matched {match['threat_type']} via {match['provider']}.",
                        "weight": 7,
                        "evidence": match["url"][:160],
                        "start": 0, "end": 0,
                        "advice": "Do not open this link.",
                    })
                result["level"] = "high"
                result["score"] = max(int(result.get("score", 0)), 8)
            if data.text.strip():
                from .cloud import hybrid
                result = hybrid(data.text, result, data.language)
                contributions["cloud_llm"] = result.get("analysis_mode", "offline_fallback")
            else:
                result["analysis_mode"] = "offline"
        else:
            result["analysis_mode"] = "offline"
        result["engine_contributions"] = contributions
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.post("/api/transcribe-audio")
async def transcribe_audio(request: Request, file: UploadFile = File(...), language: str = Query("en"),
                           duration_seconds: float = Form(...), consent: bool = Form(False)):
    """Explicitly authorized cloud STT; no persistent local scan history."""
    origin = request.headers.get("origin")
    if origin and origin not in {"http://127.0.0.1:8000", "http://localhost:8000"}:
        await file.close()
        raise HTTPException(status_code=403, detail="Local origin required")
    if not consent:
        await file.close()
        raise HTTPException(status_code=400, detail="Confirm permission to send this recording to Sarvam AI.")
    language_codes = {"en":"en-IN", "hi":"hi-IN", "bn":"bn-IN", "kn":"kn-IN",
                     "te":"te-IN", "or":"od-IN", "mr":"mr-IN", "ta":"ta-IN", "ml":"ml-IN", "gu":"gu-IN", "pa":"pa-IN"}
    if language not in language_codes:
        await file.close()
        raise HTTPException(status_code=422, detail="Unsupported audio language")
    if not math.isfinite(duration_seconds) or duration_seconds <= 0 or duration_seconds > 180:
        await file.close()
        raise HTTPException(status_code=413, detail="Choose a recording that is 3 minutes or shorter.")
    extensions = {".mp3":"audio/mpeg", ".wav":"audio/wav", ".m4a":"audio/mp4",
                  ".mp4":"audio/mp4", ".aac":"audio/aac", ".ogg":"audio/ogg",
                  ".opus":"audio/ogg", ".webm":"audio/webm", ".flac":"audio/flac",
                  ".amr":"audio/amr", ".wma":"audio/x-ms-wma", ".aiff":"audio/aiff"}
    suffix = Path(file.filename or "").suffix.lower()
    content_type = extensions.get(suffix)
    if not content_type:
        await file.close()
        raise HTTPException(status_code=415, detail="Choose an MP3, WAV, M4A, AAC, OGG, WebM or FLAC audio file.")
    audio = await file.read(20 * 1024 * 1024 + 1)
    await file.close()
    if not audio:
        raise HTTPException(status_code=422, detail="The selected audio file is empty.")
    if len(audio) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio file limit is 20 MB.")
    key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="Audio-file transcription requires a Sarvam API key. Start the app with run.bat with your Sarvam key.")
    try:
        if duration_seconds <= 30:
            transcript = await asyncio.to_thread(_sarvam_short_transcribe, audio, suffix, content_type, language_codes[language], key)
        else:
            transcript = await asyncio.to_thread(_sarvam_batch_transcribe, audio, suffix, language_codes[language], key)
    except HTTPException:
        raise
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Sarvam transcription took too long. Try again in a moment.") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Sarvam could not transcribe this file. Check your API key, credits, file format, and internet connection.") from exc
    transcript = transcript.strip() if isinstance(transcript, str) else ""
    if not transcript:
        raise HTTPException(status_code=422, detail="No speech was recognized in the recording.")
    return {"text": transcript[:MAX_TEXT], "language_code": language_codes[language],
            "note":"Transcript generated by Sarvam AI. Review it before analysis."}

def _sarvam_short_transcribe(audio: bytes, suffix: str, content_type: str, language_code: str, api_key: str) -> str:
    """Use synchronous STT for short demo clips; provider enforces its 30-second limit."""
    response = httpx.post("https://api.sarvam.ai/speech-to-text",
        headers={"api-subscription-key": api_key},
        files={"file": ("recording" + suffix, audio, content_type)},
        data={"model": "saaras:v4", "mode": "transcribe", "language_code": language_code},
        timeout=httpx.Timeout(45, connect=5))
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Speech provider returned HTTP {response.status_code}. Check key, credits, audio format and duration.")
    return response.json().get("transcript", "")


def _sarvam_batch_transcribe(audio: bytes, suffix: str, language_code: str, api_key: str) -> str:
    """Run one temporary Sarvam batch job; input and output files are deleted afterward."""
    from sarvamai import SarvamAI
    with tempfile.TemporaryDirectory(prefix="scamshield-audio-") as workdir:
        work = Path(workdir)
        source = work / f"recording{suffix}"
        output = work / "transcripts"
        output.mkdir()
        source.write_bytes(audio)
        client = SarvamAI(api_subscription_key=api_key)
        job = client.speech_to_text_job.create_job(
            model="saaras:v4", mode="transcribe", language_code=language_code)
        job.upload_files(file_paths=[str(source)])
        job.start()
        job.wait_until_complete(poll_interval=5, timeout=180)
        results = job.get_file_results()
        if results.get("failed") or not results.get("successful"):
            raise RuntimeError("Sarvam batch job did not produce a successful transcript")
        job.download_outputs(output_dir=str(output))
        for path in output.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            transcript = data.get("transcript", "")
            if transcript:
                return transcript
    return ""

def _resolve_tesseract_cmd() -> str | None:
    """Locate the Tesseract OCR executable across PATH and standard Windows paths."""
    found = shutil.which("tesseract")
    if found:
        return found
    if os.name == "nt":
        bases = (
            os.environ.get("ProgramFiles", "C:/Program Files"),
            os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
        )
        for base in bases:
            if not base:
                continue
            for rel in ("Tesseract-OCR/tesseract.exe", "Programs/Tesseract-OCR/tesseract.exe"):
                candidate = Path(base) / rel
                if candidate.is_file():
                    return str(candidate)
    return None


@app.post("/api/ocr")
async def ocr_image(file: UploadFile = File(...), language: str = Query("auto")):
    if language not in {*LANGUAGE_NAMES, "auto"}:
        raise HTTPException(status_code=422, detail="Invalid OCR language")
    if file.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(status_code=415, detail="Upload a PNG, JPEG or WebP screenshot.")
    data = await file.read(4 * 1024 * 1024 + 1)
    await file.close()
    if len(data) > 4 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image limit is 4 MB.")
    from .qr_decoder import classify_qr_payload, decode_qr_from_bytes
    qr_payloads: list[str] = []
    qr_analysis: list[dict] = []
    ocr_unavailable_reason: str | None = None
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
        import pytesseract
        with Image.open(io.BytesIO(data)) as raw:
            if raw.format not in {"PNG", "JPEG", "WEBP"}:
                raise HTTPException(status_code=415, detail="Not a supported image format.")
            if raw.width * raw.height > 12_000_000:
                raise HTTPException(status_code=413, detail="Image resolution too large.")
            qr_payloads = decode_qr_from_bytes(data)
            qr_analysis = [classify_qr_payload(p) for p in qr_payloads]
            im = ImageOps.exif_transpose(raw).convert("RGB")
            t_cmd = _resolve_tesseract_cmd()
            if t_cmd:
                pytesseract.pytesseract.tesseract_cmd = t_cmd
            installed = pytesseract.get_languages(config="")
            desired = {"en":"eng", "hi":"hin", "bn":"ben", "kn":"kan", "te":"tel", "or":"ori", "mr":"mar", "ta":"tam", "ml":"mal", "gu":"guj", "pa":"pan"}
            if language != "auto" and desired[language] not in installed:
                raise HTTPException(status_code=503, detail=f"OCR language {desired[language]} not installed. Add its Tesseract traineddata file.")
            requested = ("eng", "hin") if language == "auto" else tuple(dict.fromkeys((desired[language], "eng")))
            selected = [code for code in requested if code in installed]
            if not selected:
                raise RuntimeError("No supported OCR language installed")
            extracted = pytesseract.image_to_string(im, lang="+".join(selected), config="--psm 6", timeout=15)
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Image could not be read.") from exc
    except (RuntimeError, pytesseract.TesseractError, pytesseract.TesseractNotFoundError) as exc:
        if not qr_payloads:
            raise HTTPException(status_code=503, detail="OCR is unavailable: install Tesseract OCR and the desired language data.") from exc
        extracted = ""
        selected = []
        ocr_unavailable_reason = "Tesseract OCR unavailable; QR code decoded locally."
    text = extracted.strip()[:MAX_TEXT]
    if not text and not qr_payloads:
        raise HTTPException(status_code=422, detail="No legible text or QR code was found. Try a clearer screenshot.")
    note = ocr_unavailable_reason or "OCR may contain errors. Check transcription before interpreting results."
    return {
        "text": text,
        "characters": len(text),
        "ocr_languages": selected,
        "qr_payloads": qr_payloads,
        "qr_analysis": qr_analysis,
        "note": note,
    }


@app.post("/api/parse-email")
async def parse_email_file(file: UploadFile = File(...)):
    """Parse an uploaded .eml file locally without executing HTML or fetching remote resources."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix != ".eml" and file.content_type not in {"message/rfc822", "text/plain", "application/octet-stream"}:
        await file.close()
        raise HTTPException(status_code=415, detail="Upload a .eml email file.")
    raw = await file.read(4 * 1024 * 1024 + 1)
    await file.close()
    if not raw:
        raise HTTPException(status_code=422, detail="The selected .eml file is empty.")
    if len(raw) > 4 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Email file limit is 4 MB.")
    from .identity_verifier import parse_eml_bytes
    parsed = parse_eml_bytes(raw)
    text = parsed["combined_text"].strip()[:MAX_TEXT]
    if not text:
        raise HTTPException(status_code=422, detail="No readable email content found.")
    return {
        "text": text,
        "email_meta": {
            "from_raw": parsed["from_raw"],
            "reply_to_raw": parsed["reply_to_raw"],
            "subject": parsed["subject"],
            "auth_raw": parsed["auth_raw"],
            "links": parsed["links"],
            "attachments": parsed["attachments"],
        },
        "note": "Email parsed locally without loading remote images or scripts. Header claims are not independently verified.",
    }
