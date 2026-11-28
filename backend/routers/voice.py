"""
Multilingual Voice Assistant Router — Live Gemini + Sarvam AI (saaras:v4 & bulbul:v3).
Never uses canned/stored Q&A fallbacks; always executes live Gemini reasoning with
location-aware Open-Meteo weather and cached APMC mandi price context.
"""
import asyncio
import base64
import json
import logging
import re
import time
from datetime import datetime
from typing import Optional

import edge_tts
import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

import config
import language_config
import location_service
import models

logger = logging.getLogger("voice")

router = APIRouter(prefix="/api/voice", tags=["voice"])

# ──────────────────────── LANGUAGE CONFIG ────────────────────────────────────

AGRICULTURAL_KEYTERMS = [
    "APMC",
    "mandi",
    "paddy",
    "arecanut",
    "areca",
    "ginger",
    "maize",
    "corn",
    "NPK",
    "urea",
    "DAP",
    "MOP",
    "fungicide",
    "pesticide",
    "blight",
    "stem borer",
    "PM-KISAN",
    "PM-KUSUM",
    "PMFBY",
    "KCC",
    "Nandini",
    "acre",
    "barrel",
    "quintal",
]

LANGUAGE_MAP = {
    cfg["short_code"]: {
        "sarvam_code": code,
        "gemini_name": cfg["gemini_name"],
        "edge_tts_voice": cfg["edge_tts_voice"],
    }
    for code, cfg in language_config.SUPPORTED_LANGUAGES.items()
}

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


def normalize_language_code(lang: Optional[str], default: str = "kn-IN") -> str:
    """Normalize short or regional language codes to supported Sarvam/Gemini BCP-47 codes."""
    return language_config.normalize_language_code(lang, default=default)


# ──────────────────── INTERNAL TOOL FUNCTIONS ────────────────────────────────
# These are called by Gemini's tool-calling loop to fetch real farm data.

def _get_db_session():
    """Get a one-shot DB session for tool calls."""
    from database import SessionLocal
    return SessionLocal()


def tool_get_weather_and_irrigation_advice(
    location: str = "Bengaluru",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> dict:
    """Fetch live Open-Meteo weather advisories and irrigation recommendations."""
    resolved = location_service.resolve_coordinates(lat=lat, lon=lon, location_name=location)
    q_lat = resolved["latitude"] if resolved["latitude"] is not None else 12.9716
    q_lon = resolved["longitude"] if resolved["longitude"] is not None else 77.5946
    loc_label = resolved["location_name"] if resolved["location_name"] != "Not specified" else (location or "Bengaluru")

    t0 = time.perf_counter()
    logger.info("[Weather Tool] Querying Open-Meteo for '%s' (lat=%.4f, lon=%.4f)...", loc_label, q_lat, q_lon)

    try:
        weather = location_service.fetch_live_weather_sync(q_lat, q_lon, loc_label)
        elapsed = time.perf_counter() - t0
        if weather.get("is_live"):
            today_rain = weather.get("rain_today_mm") or 0.0
            rain_prob = weather.get("rain_prob_pct") or 0
            tmax = weather.get("temp_max") or weather.get("temp_now") or 28.0
            tmin = weather.get("temp_min") or 19.0
            advice = []
            if today_rain > 10 or rain_prob > 70:
                advice.append("Heavy rain expected — postpone harvesting and avoid spraying pesticides.")
            elif today_rain == 0 and rain_prob < 25:
                advice.append("Dry weather window — good for harvesting, sun-drying, and foliar sprays.")
            advice.append(f"Temperature range: {tmin}°C – {tmax}°C (current {weather.get('temp_now')}°C, humidity {weather.get('humidity_pct')}%).")
            if tmax > 32:
                advice.append("High temperature alert — increase irrigation frequency for vegetable crops.")
            logger.info("[Weather Tool] Live Open-Meteo advice fetched for %s in %.2fs", loc_label, elapsed)
            return {
                "location": loc_label,
                "latitude": q_lat,
                "longitude": q_lon,
                "is_live": True,
                "today_rain_mm": today_rain,
                "rain_prob_pct": rain_prob,
                "temp_max": tmax,
                "temp_min": tmin,
                "current_temp_c": weather.get("temp_now"),
                "humidity_pct": weather.get("humidity_pct"),
                "advisories": advice,
            }
        return {
            "location": loc_label,
            "is_live": False,
            "error": weather.get("summary_text", "Live weather fetch failed"),
        }
    except Exception as exc:
        logger.error("[Weather Tool] Failed fetching Open-Meteo for %s: %s", loc_label, exc)
        print(f"[Weather Tool ERROR] {exc}", flush=True)
        return {"location": loc_label, "is_live": False, "error": str(exc)}


def tool_get_commodity_mandi_prices(commodity: str = "paddy") -> dict:
    """Fetch current cached APMC mandi prices for the specified commodity from SQLite."""
    db = _get_db_session()
    try:
        aliases = {
            "paddy": "Paddy (Fine)",
            "rice": "Paddy (Fine)",
            "areca": "Areca Nut (Chali)",
            "arecanut": "Areca Nut (Chali)",
            "ginger": "Ginger (Fresh)",
            "corn": "Corn / Maize",
            "maize": "Corn / Maize",
            "pepper": "Black Pepper",
            "coconut": "Coconut (Copra)",
        }
        canonical = aliases.get((commodity or "paddy").lower().strip(), commodity)
        c = db.query(models.Commodity).filter(
            models.Commodity.name.ilike(f"%{canonical}%")
        ).first()
        if not c:
            c = db.query(models.Commodity).filter(
                models.Commodity.name.ilike(f"%{commodity}%")
            ).first()
        mandis = db.query(models.MandiPrice).filter(
            models.MandiPrice.commodity_name.ilike(f"%{canonical}%")
        ).order_by(models.MandiPrice.modal_price.desc()).limit(6).all()
        if not mandis and c:
            mandis = db.query(models.MandiPrice).filter(
                models.MandiPrice.commodity_name.ilike(f"%{c.name}%")
            ).order_by(models.MandiPrice.modal_price.desc()).limit(6).all()
        mandi_list = [
            {
                "market": m.market_name,
                "district": m.district,
                "state": m.state,
                "min": m.min_price,
                "max": m.max_price,
                "modal": m.modal_price,
                "recorded_date": m.recorded_date,
            }
            for m in mandis
        ]
        if not c and not mandi_list:
            return {"commodity": commodity, "found": False, "note": "No matching APMC record found in local cache."}
        return {
            "commodity": c.name if c else commodity,
            "unit": c.unit if c else "quintal",
            "current_price_rs": c.current_price if c else (mandi_list[0]["modal"] if mandi_list else None),
            "trend": "up" if c and c.current_price > c.previous_price else "stable",
            "top_mandis": mandi_list,
        }
    finally:
        db.close()


def tool_get_dairy_milk_rates() -> dict:
    """Fetch current milk procurement rates from local SQLite DB."""
    db = _get_db_session()
    try:
        rates = db.query(models.DairyProcurementRate).order_by(
            models.DairyProcurementRate.rate_per_litre.desc()
        ).limit(8).all()
        rate_list = [
            {
                "dairy": r.dairy_name,
                "milk_type": r.milk_type,
                "slab": r.slab_name,
                "base_fat_pct": r.base_fat_pct,
                "base_snf_pct": r.base_snf_pct,
                "rate_per_litre": r.rate_per_litre,
                "govt_incentive": r.govt_incentive,
            }
            for r in rates
        ]
        return {"milk_rates": rate_list, "note": "Rates per litre from cached dairy procurement table."}
    finally:
        db.close()


def tool_get_farm_balance_sheet_summary() -> dict:
    """Return current year farm revenue vs expense summary from ledger."""
    db = _get_db_session()
    try:
        entries = db.query(models.FarmLedgerEntry).all()
        total_income = sum(e.amount for e in entries if e.entry_type in ("revenue", "income"))
        total_expense = sum(e.amount for e in entries if e.entry_type == "expense")
        net = total_income - total_expense
        return {
            "year": datetime.now().year,
            "total_income_rs": round(total_income, 2),
            "total_expense_rs": round(total_expense, 2),
            "net_profit_rs": round(net, 2),
            "status": "Profit" if net >= 0 else "Loss",
        }
    finally:
        db.close()


def tool_get_upcoming_scheme_deadlines() -> dict:
    """Return the upcoming government scheme deadlines."""
    db = _get_db_session()
    try:
        notifs = db.query(models.Notification).filter(
            models.Notification.deadline_date.isnot(None)
        ).order_by(models.Notification.deadline_date.asc()).limit(5).all()
        schemes = [
            {
                "scheme": n.title,
                "category": n.category,
                "deadline": str(n.deadline_date or "Ongoing"),
                "benefit": n.benefit_amount or "See notification for details",
            }
            for n in notifs
        ]
        return {"upcoming_deadlines": schemes, "helpline": "PM-Kisan Helpline: 155261"}
    finally:
        db.close()


# ─────────────────── GEMINI TOOL DEFINITIONS ─────────────────────────────────

GEMINI_TOOLS = [
    {
        "name": "get_weather_and_irrigation_advice",
        "description": "Get live Open-Meteo weather forecast and farm irrigation/harvesting advisories for a location or coordinates.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City, village, or district name"},
                "lat": {"type": "number", "description": "Optional latitude"},
                "lon": {"type": "number", "description": "Optional longitude"},
            },
            "required": [],
        },
    },
    {
        "name": "get_commodity_mandi_prices",
        "description": "Get APMC mandi prices for an agricultural commodity (paddy, areca, ginger, corn, pepper, coconut, tomato, onion, etc.).",
        "parameters": {
            "type": "object",
            "properties": {
                "commodity": {"type": "string", "description": "Commodity name (e.g., paddy, areca, ginger, corn, pepper, coconut)"}
            },
            "required": ["commodity"],
        },
    },
    {
        "name": "get_dairy_milk_rates",
        "description": "Get dairy milk procurement rates (cow and buffalo) from dairies like KMF Nandini, Amul, Dodla, Heritage.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_farm_balance_sheet_summary",
        "description": "Get the current year farm revenue and expense summary from the farm ledger.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_upcoming_scheme_deadlines",
        "description": "Get upcoming government scheme deadlines, crop insurance enrollment dates, and subsidy windows.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
]

TOOL_DISPATCH = {
    "get_weather_and_irrigation_advice": tool_get_weather_and_irrigation_advice,
    "get_commodity_mandi_prices": tool_get_commodity_mandi_prices,
    "get_dairy_milk_rates": tool_get_dairy_milk_rates,
    "get_farm_balance_sheet_summary": tool_get_farm_balance_sheet_summary,
    "get_upcoming_scheme_deadlines": tool_get_upcoming_scheme_deadlines,
}


# ─────────────────── GEMINI AGENTIC CALL ─────────────────────────────────────

def _call_gemini_with_tools(
    query_text: Optional[str],
    language_code: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    location_name: Optional[str] = None,
    user_id: Optional[str] = None,
    weather_summary: Optional[str] = None,
    audio_bytes: Optional[bytes] = None,
    audio_mime: str = "audio/webm",
) -> str:
    """
    Send farmer query (text or raw audio bytes) to live Google Gemini
    (gemini-3.5-flash-lite -> gemini-3.8-flash -> gemini-3.6-flash)
    with location context and 5 agri tool definitions.
    """
    import google.genai as genai
    from google.genai import errors as gerrors
    from google.genai import types as gtypes

    if not config.has_gemini():
        err_msg = "GEMINI_API_KEY is missing; cannot execute live Gemini query."
        logger.error("[Gemini] %s", err_msg)
        print(f"[Gemini ERROR] {err_msg}", flush=True)
        raise RuntimeError(err_msg)

    norm_lang = normalize_language_code(language_code, default="kn-IN")
    if norm_lang == "auto":
        norm_lang = detect_language_from_text(query_text or "", default="kn-IN")
    lang_info = LANGUAGE_MAP.get(norm_lang[:2], LANGUAGE_MAP["en"])

    resolved = location_service.resolve_coordinates(
        lat=lat, lon=lon, location_name=location_name, user_id=user_id
    )
    loc_label = resolved["location_name"] if resolved["location_name"] != "Not specified" else (location_name or "Karnataka, India")
    if weather_summary is None:
        if resolved["latitude"] is not None and resolved["longitude"] is not None:
            weather_info = location_service.fetch_live_weather_sync(
                resolved["latitude"], resolved["longitude"], loc_label
            )
            weather_summary = weather_info["summary_text"]
        else:
            weather_summary = f"Location: {loc_label}."

    client = genai.Client(
        api_key=config.GEMINI_API_KEY,
        http_options=gtypes.HttpOptions(
            timeout=20000,
            retry_options=gtypes.HttpRetryOptions(attempts=1),
        ),
    )

    selected_language = lang_info["gemini_name"]
    system_instruction = f"""Role: Expert Indian Agronomist & Farm Advisor for Karnataka and India.
User Location: {loc_label} (Brief weather context, use only if relevant: {weather_summary})

Strict Rule: Answer ONLY the farmer's exact question directly, factually, and practically (with exact crop varieties, chemical/organic dosages per liter/acre, or scheme eligibility where applicable). Never go off-topic.
Language Rule: Respond strictly in {selected_language} (using natural Kannada/Hindi/Telugu/Tamil/Marathi script, not transliterated English).
Tools: Use `get_commodity_mandi_prices`, `get_weather_and_irrigation_advice`, `get_dairy_milk_rates`, `get_farm_balance_sheet_summary`, or `get_upcoming_scheme_deadlines` ONLY when the farmer specifically asks about market prices, weather, milk rates, farm finances, or government schemes.
Keep answers concise (under 180 words), clear, and actionable."""

    tool_declarations = [
        gtypes.FunctionDeclaration(
            name=t["name"],
            description=t["description"],
            parameters=t["parameters"],
        )
        for t in GEMINI_TOOLS
    ]
    tools = gtypes.Tool(function_declarations=tool_declarations)
    if audio_bytes is not None:
        user_parts = [
            gtypes.Part.from_bytes(data=audio_bytes, mime_type=audio_mime),
            gtypes.Part(
                text=(
                    "Listen carefully to the farmer's audio. "
                    "If there is no intelligible speech, reply ONLY with: __NO_SPEECH__. "
                    f"Otherwise, transcribe and answer the farmer's exact question directly in {selected_language}."
                )
            ),
        ]
    else:
        user_parts = [gtypes.Part(text=query_text or "")]
    messages = [gtypes.Content(role="user", parts=user_parts)]

    candidate_models = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.6-flash"]
    last_error: Optional[Exception] = None

    for _iteration in range(5):
        response = None
        for _m in candidate_models:
            try:
                t_model_start = time.perf_counter()
                logger.info("[Gemini] Querying model %s (turn %d, lang=%s)...", _m, _iteration + 1, norm_lang)
                response = client.models.generate_content(
                    model=_m,
                    contents=messages,
                    config=gtypes.GenerateContentConfig(
                        system_instruction=system_instruction,
                        tools=[tools],
                        max_output_tokens=1000,
                        thinking_config=gtypes.ThinkingConfig(thinking_level="LOW"),
                    ),
                )
                logger.info("[Gemini] Model %s succeeded in %.2fs", _m, time.perf_counter() - t_model_start)
                break
            except gerrors.ServerError as _err:
                last_error = _err
                logger.error("[Gemini] ServerError (503/504) on %s: %s", _m, _err, exc_info=True)
                print(f"[Gemini SERVER ERROR] Model {_m} failed: {_err}", flush=True)
                continue
            except Exception as _err:
                last_error = _err
                logger.error("[Gemini] Model %s failed: %s: %s", _m, type(_err).__name__, _err, exc_info=True)
                print(f"[Gemini ERROR] Model {_m} failed: {type(_err).__name__}: {_err}", flush=True)
                continue

        if response is None:
            raise RuntimeError(f"All Gemini models failed ({candidate_models}): {last_error}")

        candidate = response.candidates[0] if response.candidates else None
        response_parts = candidate.content.parts if (candidate and candidate.content) else []
        function_calls = [p for p in response_parts if getattr(p, "function_call", None)]

        if not function_calls:
            text_parts = [p.text for p in response_parts if getattr(p, "text", None)]
            final_text = " ".join(text_parts).strip()
            if not final_text:
                raise RuntimeError("Gemini returned an empty text response.")
            return final_text

        tool_results = []
        for part in function_calls:
            fc = part.function_call
            fn = TOOL_DISPATCH.get(fc.name)
            if fn:
                try:
                    args = dict(fc.args) if fc.args else {}
                    if fc.name == "get_weather_and_irrigation_advice":
                        if "lat" not in args and resolved["latitude"] is not None:
                            args["lat"] = resolved["latitude"]
                        if "lon" not in args and resolved["longitude"] is not None:
                            args["lon"] = resolved["longitude"]
                        if "location" not in args and resolved["location_name"] != "Not specified":
                            args["location"] = resolved["location_name"]
                    result_data = fn(**args)
                except Exception as e:
                    logger.error("[Gemini Tool] Tool %s failed: %s", fc.name, e, exc_info=True)
                    result_data = {"error": str(e)}
            else:
                result_data = {"error": f"Tool '{fc.name}' not found"}

            tool_results.append(
                gtypes.Part(
                    function_response=gtypes.FunctionResponse(
                        name=fc.name,
                        response=result_data,
                    )
                )
            )

        messages.append(gtypes.Content(role="model", parts=response_parts))
        messages.append(gtypes.Content(role="user", parts=tool_results))

    raise RuntimeError("Gemini reached maximum tool-call iterations without producing a final response.")


# ─────────────────── SARVAM STT / TTS ───────────────────────────────────────

def detect_language_from_text(text: str, default: str = "kn-IN") -> str:
    """Detect Indian language from script unicode ranges, distinguishing Hindi and Marathi."""
    if not text:
        return default
    if any("\u0c80" <= c <= "\u0cff" for c in text):
        return "kn-IN"
    if any("\u0c00" <= c <= "\u0c7f" for c in text):
        return "te-IN"
    if any("\u0b80" <= c <= "\u0bff" for c in text):
        return "ta-IN"
    if any("\u0d00" <= c <= "\u0d7f" for c in text):
        return "ml-IN"
    if any("\u0900" <= c <= "\u097f" for c in text):
        marathi_markers = (
            "आहे", "आहेत", "माझ्या", "माझे", "तुमचा", "शेती", "पीक",
            "पाऊस", "काय", "किती", "नाही", "फवारणी", "खत", "कापणी", "भाव",
        )
        if any(m in text for m in marathi_markers):
            return "mr-IN"
        return "hi-IN"
    if all(ord(c) < 128 for c in text.strip()):
        return "en-IN"
    return default


NO_SPEECH_MESSAGES = {
    "kn-IN": "ದಯವಿಟ್ಟು ಮೈಕ್ ಹತ್ತಿರ ಮಾತನಾಡಿ ಮತ್ತು ಮತ್ತೊಮ್ಮೆ ಪ್ರಯತ್ನಿಸಿ. ನಿಮ್ಮ ಧ್ವನಿ ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ.",
    "hi-IN": "कृपया माइक के पास बोलें और फिर से प्रयास करें। आपकी आवाज़ स्पष्ट रूप से सुनाई नहीं दी।",
    "te-IN": "దయచేసి మైక్ దగ్గర మాట్లాడి మళ్లీ ప్రయత్నించండి. మీ మాట స్పష్టంగా వినిపించలేదు.",
    "ta-IN": "தயவுசெய்து மைக்கின் அருகில் பேசி மீண்டும் முயற்சிக்கவும். உங்கள் குரல் தெளிவாகக் கேட்கவில்லை.",
    "mr-IN": "कृपया माइकच्या जवळ बोला आणि पुन्हा प्रयत्न करा. तुमचा आवाज स्पष्ट ऐकू आला नाही.",
    "en-IN": "Please speak closer to the microphone and try again. I could not hear clear speech.",
}


def _detect_audio_mime_and_filename(audio_bytes: bytes) -> tuple[str, str]:
    """Detect audio MIME type and filename from magic bytes."""
    if audio_bytes.startswith(b"OggS"):
        return "audio/ogg", "recording.ogg"
    if audio_bytes.startswith(b"RIFF"):
        return "audio/wav", "recording.wav"
    if audio_bytes.startswith(b"\xff\xfb") or audio_bytes.startswith(b"\xff\xf3") or audio_bytes.startswith(b"ID3"):
        return "audio/mpeg", "recording.mp3"
    return "audio/webm", "recording.webm"


def _is_garbled_transcript(text: Optional[str]) -> bool:
    """Return True if transcript is empty, too short, or contains only punctuation/repeated characters."""
    if not text:
        return True
    cleaned = text.strip()
    if len(cleaned) < 2:
        return True
    alnum_chars = [c for c in cleaned if c.isalnum()]
    if len(alnum_chars) < 2:
        return True
    if len(set(alnum_chars)) == 1 and len(alnum_chars) > 3:
        return True
    return False


async def _sarvam_stt(
    audio_bytes: bytes,
    language_code: Optional[str] = None,
    keyterms: Optional[list] = None,
) -> dict:
    """
    Call Sarvam AI saarika:v2.5 STT with the exact language_code and proper filename/MIME type.
    Logs exact HTTP status and response text to the console.
    """
    mime_type, filename = _detect_audio_mime_and_filename(audio_bytes)

    sarvam_lang = normalize_language_code(language_code, default="kn-IN")
    if sarvam_lang == "auto":
        sarvam_lang = "kn-IN"

    payload = {
        "model": "saarika:v2.5",
        "language_code": sarvam_lang,
    }

    t0 = time.perf_counter()
    logger.info(
        "[Sarvam STT] Calling saarika:v2.5 (audio_bytes=%d, filename=%s, mime=%s, lang=%s)...",
        len(audio_bytes), filename, mime_type, sarvam_lang,
    )
    timeout = httpx.Timeout(12.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            SARVAM_STT_URL,
            headers={"api-subscription-key": config.SARVAM_API_KEY},
            files={"file": (filename, audio_bytes, mime_type)},
            data=payload,
        )
        print(f"[Sarvam STT] HTTP {resp.status_code}: {resp.text}", flush=True)
        logger.info("[Sarvam STT] HTTP %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()
        data = resp.json()
        transcript = (data.get("transcript") or data.get("text") or "").strip()
        raw_detected = data.get("language_code")
        if raw_detected and str(raw_detected).lower() not in ("unknown", "auto", ""):
            detected_lang = normalize_language_code(raw_detected, default=sarvam_lang)
        else:
            detected_lang = sarvam_lang

        elapsed = time.perf_counter() - t0
        logger.info(
            "[Sarvam STT] saarika:v2.5 completed in %.2fs: detected_lang=%s, transcript=%s",
            elapsed, detected_lang, transcript[:100],
        )
        return {"transcript": transcript, "language_code": detected_lang}


def clean_text_for_speech(text: str) -> str:
    """Strip Markdown symbols, emojis, and extra whitespace; truncate at sentence boundary <= 2200 chars."""
    if not text:
        return ""
    cleaned = text
    # Strip backticks and Markdown heading/emphasis/bullet markers
    cleaned = re.sub(r"`+", "", cleaned)
    cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"#+", "", cleaned)
    cleaned = re.sub(r"^\s*[-*•+]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\*{1,3}|_{1,3}|~~", "", cleaned)
    # Strip decorative emojis and variation selectors
    cleaned = re.sub(
        r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U00002600-\U000026FF\U0000FE00-\U0000FE0F\u200d]+",
        "",
        cleaned,
    )
    # Replace newlines with a natural pause and collapse extra spaces
    cleaned = re.sub(r"\r?\n+", ". ", cleaned)
    cleaned = re.sub(r"\.\s*\.", ".", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Truncate safely to 2,200 characters at a sentence boundary
    if len(cleaned) > 2200:
        candidate = cleaned[:2200]
        last_boundary = max(
            candidate.rfind("."),
            candidate.rfind("!"),
            candidate.rfind("?"),
            candidate.rfind("।"),
        )
        if last_boundary > 0:
            cleaned = candidate[: last_boundary + 1].strip()
        elif " " in candidate:
            cleaned = candidate.rsplit(" ", 1)[0].strip()
        else:
            cleaned = candidate
    return cleaned


async def _sarvam_tts(text: str, language_code: str) -> Optional[str]:
    """Call Sarvam bulbul:v3 TTS with speaker 'priya'. Returns base64-encoded WAV audio string."""
    norm = normalize_language_code(language_code, default="kn-IN")
    sarvam_lang = "kn-IN" if norm == "auto" else norm
    clean_speech_text = clean_text_for_speech(text)
    if not clean_speech_text:
        return None
    t0 = time.perf_counter()
    logger.info("[Sarvam TTS] Calling bulbul:v3 (lang=%s, chars=%d)...", sarvam_lang, len(clean_speech_text))
    timeout = httpx.Timeout(10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            SARVAM_TTS_URL,
            headers={
                "api-subscription-key": config.SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "text": clean_speech_text,
                "target_language_code": sarvam_lang,
                "language_code": sarvam_lang,
                "model": "bulbul:v3",
                "speaker": "priya",
                "pace": 1.0,
            },
        )
        if resp.status_code >= 400:
            logger.error("[Sarvam TTS] HTTP %s: %s", resp.status_code, resp.text)
            print(f"[Sarvam TTS ERROR] HTTP {resp.status_code}: {resp.text}", flush=True)
        resp.raise_for_status()
        data = resp.json()
        audios = data.get("audios", [])
        if audios:
            elapsed = time.perf_counter() - t0
            logger.info("[Sarvam TTS] bulbul:v3 completed in %.2fs (audio_b64_len=%d)", elapsed, len(audios[0]))
            return audios[0]
    return None


EDGE_TTS_VOICES = {
    "kn-IN": "kn-IN-SapnaNeural",
    "hi-IN": "hi-IN-SwaraNeural",
    "te-IN": "te-IN-ShrutiNeural",
    "ta-IN": "ta-IN-PallaviNeural",
    "mr-IN": "mr-IN-AarohiNeural",
    "ml-IN": "ml-IN-SobhanaNeural",
    "en-IN": "en-IN-NeerjaNeural",
}


async def _edge_tts(text: str, language_code: str) -> Optional[str]:
    """Synthesize text to MP3 audio using free edge-tts. Returns base64-encoded MP3 string."""
    norm = normalize_language_code(language_code, default="kn-IN")
    lang = "kn-IN" if norm == "auto" else norm
    voice_name = EDGE_TTS_VOICES.get(lang, "en-IN-NeerjaNeural")
    clean_speech_text = clean_text_for_speech(text)
    if not clean_speech_text:
        return None
    t0 = time.perf_counter()
    logger.info("[edge-tts] Synthesizing (voice=%s, chars=%d)...", voice_name, len(clean_speech_text))
    communicate = edge_tts.Communicate(clean_speech_text, voice=voice_name)
    chunks = []
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio" and chunk.get("data"):
            chunks.append(chunk["data"])
    if not chunks:
        return None
    audio_bytes = b"".join(chunks)
    elapsed = time.perf_counter() - t0
    logger.info("[edge-tts] Completed in %.2fs (%d bytes)", elapsed, len(audio_bytes))
    return base64.b64encode(audio_bytes).decode("utf-8")


async def synthesize_speech(text: str, language_code: str = "kn-IN") -> Optional[str]:
    """Synthesize text to speech using free edge-tts; returns None and logs if failed."""
    try:
        return await _edge_tts(text, language_code)
    except Exception as exc:
        logger.error("[edge-tts] Synthesis failed: %s", exc, exc_info=True)
        print(f"[edge-tts ERROR] {type(exc).__name__}: {exc}", flush=True)
        return None


# ─────────────────────────── ENDPOINTS ───────────────────────────────────────

class TextQueryRequest(BaseModel):
    text: Optional[str] = None
    query: Optional[str] = None
    language: str = "kn-IN"
    keyterms: Optional[list] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    location_name: Optional[str] = None
    user_id: Optional[str] = None


@router.get("/languages")
def get_supported_languages():
    return [
        {"code": k, "name": v["gemini_name"], "sarvam_code": v["sarvam_code"]}
        for k, v in LANGUAGE_MAP.items()
    ]


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).upper()
    return any(
        code in msg
        for code in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "504", "DEADLINE_EXCEEDED")
    )


def _build_quota_fallback_reply(
    language_code: str,
    transcript: str = "",
    location_name: str = "",
    weather_summary: str = "",
) -> str:
    """Build a helpful local fallback reply when all Gemini models hit 429 RESOURCE_EXHAUSTED."""
    loc_line = f" ({location_name})" if location_name and location_name != "Not specified" else ""
    weather_line = f"\n🌦️ {weather_summary}" if weather_summary and "Location:" not in weather_summary else ""
    templates = {
        "kn-IN": (
            f"🙏 ಕ್ಷಮಿಸಿ, ಇಂದಿನ AI ಸೇವೆಯ ದೈನಂದಿನ ಮಿತಿ (Daily Quota) ತಾತ್ಕಾಲಿಕವಾಗಿ ಪೂರ್ಣಗೊಂಡಿದೆ{loc_line}."
            f"{weather_line}\nದಯವಿಟ್ಟು ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ ಅಥವಾ ಕೃಷಿ ಸಹಾಯವಾಣಿ 155261 ಅನ್ನು ಸಂಪರ್ಕಿಸಿ."
        ),
        "hi-IN": (
            f"🙏 क्षमा करें, आज की AI सेवा की दैनिक सीमा (Daily Quota) अस्थायी रूप से पूरी हो गई है{loc_line}।"
            f"{weather_line}\nकृपया थोड़ी देर बाद पुनः प्रयास करें या किसान हेल्पलाइन 155261 पर संपर्क करें।"
        ),
        "te-IN": (
            f"🙏 క్షమించండి, ఈ రోజు AI సేవ యొక్క రోజువారీ పరిమితి (Daily Quota) తాత్కాలికంగా పూర్తయింది{loc_line}."
            f"{weather_line}\nదయచేసి కాసేపటి తర్వాత మళ్లీ ప్రయత్నించండి లేదా రైతు హెల్ప్‌లైన్ 155261 కు కాల్ చేయండి."
        ),
        "ta-IN": (
            f"🙏 மன்னிக்கவும், இன்றைய AI சேவையின் தினசரி வரம்பு (Daily Quota) தற்காலிகமாக நிறைவடைந்துள்ளது{loc_line}."
            f"{weather_line}\nதயவுசெய்து சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும் அல்லது உழவர் உதவி எண் 155261 ஐ அழைக்கவும்."
        ),
        "mr-IN": (
            f"🙏 क्षमस्व, आजची AI सेवेची दैनिक मर्यादा (Daily Quota) तात्पुरती पूर्ण झाली आहे{loc_line}."
            f"{weather_line}\nकृपया थोड्या वेळाने पुन्हा प्रयत्न करा किंवा किसान हेल्पलाइन 155261 वर संपर्क साधा."
        ),
        "en-IN": (
            f"🙏 Sorry, the daily AI advisory quota is temporarily exhausted{loc_line}."
            f"{weather_line}\nPlease try again shortly or call the Kisan Helpline at 155261."
        ),
    }
    base = templates.get(language_code, templates["en-IN"])
    if transcript:
        return f"📝 \"{transcript}\"\n\n{base}"
    return base


async def process_voice_or_text(
    query_text: Optional[str] = None,
    audio_bytes: Optional[bytes] = None,
    browser_transcript: Optional[str] = None,
    language: str = "kn-IN",
    keyterms: Optional[list] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    location_name: Optional[str] = None,
    user_id: Optional[str] = None,
    skip_tts: bool = False,
) -> dict:
    active_keyterms = keyterms or AGRICULTURAL_KEYTERMS
    transcript = (query_text or "").strip()
    clean_browser_transcript = (browser_transcript or "").strip()
    stt_status = "skipped" if transcript else "pending"
    current_lang = normalize_language_code(language, default="kn-IN")
    use_gemini_audio_fallback = False
    audio_mime = "audio/webm"
    t_start = time.perf_counter()

    # Step 1: Free STT (browser_transcript -> direct Gemini Native Audio)
    if audio_bytes is not None:
        audio_mime, _ = _detect_audio_mime_and_filename(audio_bytes)
        if len(audio_bytes) < 1500 and _is_garbled_transcript(clean_browser_transcript):
            raise ValueError("Audio recording is empty or too short. Please speak closer to the mic.")

        # Use browser_transcript when provided
        if not _is_garbled_transcript(clean_browser_transcript):
            transcript = clean_browser_transcript
            stt_status = "browser_transcript"
            logger.info("[Voice Pipeline] Using browser_transcript: %s", transcript[:100])

        # Fallback: Pass raw audio_bytes directly to Gemini Native Audio
        if not transcript:
            if len(audio_bytes) >= 1500:
                use_gemini_audio_fallback = True
                stt_status = "gemini_audio"
                logger.info("[Voice Pipeline] Falling back to direct Gemini audio transcription+answer.")
            else:
                no_speech_lang = "kn-IN" if current_lang in ("auto", "unknown", "") else current_lang
                no_speech_msg = NO_SPEECH_MESSAGES.get(no_speech_lang, NO_SPEECH_MESSAGES["en-IN"])
                return {
                    "transcript": "",
                    "response": no_speech_msg,
                    "audio_base64": None,
                    "language": no_speech_lang,
                    "keyterms": active_keyterms,
                    "location": {"latitude": lat, "longitude": lon, "location_name": location_name or "Not specified"},
                    "status": "no_speech",
                    "pipeline": {"stt": "no_speech", "llm": "skipped", "tts": "skipped"},
                }

    if not transcript and not use_gemini_audio_fallback:
        raise ValueError("Empty query: please provide text or audio.")

    if current_lang in ("auto", "unknown", "") or not current_lang:
        current_lang = detect_language_from_text(transcript, default="kn-IN")
    else:
        current_lang = normalize_language_code(current_lang, default="kn-IN")

    # Step 2: Location + Brief Weather Context (no unrelated bulk mandi/news dumps)
    resolved = location_service.resolve_coordinates(
        lat=lat, lon=lon, location_name=location_name, user_id=user_id
    )
    if resolved["latitude"] is not None and resolved["longitude"] is not None:
        weather_info = await location_service.fetch_live_weather_async(
            resolved["latitude"], resolved["longitude"], resolved["location_name"]
        )
        weather_summary = weather_info["summary_text"]
    else:
        weather_summary = f"Location: {resolved['location_name']}."

    # Step 3: Live Gemini Reasoning (NO canned/mock fallback)
    if not config.has_gemini():
        err_msg = "GEMINI_API_KEY is not configured; live advisory unavailable."
        logger.error("[Voice Pipeline] %s", err_msg)
        print(f"[Voice Pipeline ERROR] {err_msg}", flush=True)
        raise RuntimeError(err_msg)

    try:
        response_text = await asyncio.wait_for(
            asyncio.to_thread(
                _call_gemini_with_tools,
                transcript if not use_gemini_audio_fallback else None,
                current_lang,
                resolved["latitude"],
                resolved["longitude"],
                resolved["location_name"],
                user_id,
                weather_summary,
                audio_bytes if use_gemini_audio_fallback else None,
                audio_mime,
            ),
            timeout=95.0,
        )
        llm_status = "live"
    except Exception as exc:
        logger.error("[Voice Pipeline] Live Gemini reasoning failed: %s", exc, exc_info=True)
        print(f"[Voice Pipeline GEMINI ERROR] {type(exc).__name__}: {exc}", flush=True)
        if _is_quota_error(exc):
            response_text = _build_quota_fallback_reply(
                current_lang,
                transcript=transcript,
                location_name=resolved["location_name"],
                weather_summary=weather_summary,
            )
            llm_status = "quota_fallback"
        else:
            raise RuntimeError(f"Live Gemini advisory failed: {exc}") from exc

    if "__NO_SPEECH__" in response_text:
        response_text = NO_SPEECH_MESSAGES.get(current_lang, NO_SPEECH_MESSAGES["en-IN"])
        llm_status = "no_speech"

    # Step 4: Free edge-tts in exact detected language (MP3)
    speech_text = clean_text_for_speech(response_text)
    audio_b64 = None
    tts_status = "skipped"
    if not skip_tts:
        try:
            audio_b64 = await asyncio.wait_for(
                _edge_tts(speech_text, current_lang),
                timeout=15.0,
            )
            tts_status = "live" if audio_b64 else "unavailable"
        except Exception as exc:
            logger.error("[Voice Pipeline] edge-tts failed: %s", exc, exc_info=True)
            print(f"[Voice Pipeline TTS ERROR] {type(exc).__name__}: {exc}", flush=True)
            audio_b64 = None
            tts_status = "error"

    elapsed_total = time.perf_counter() - t_start
    logger.info(
        "[Voice Pipeline] Finished in %.2fs: stt=%s, llm=%s, tts=%s, lang=%s, loc=%s",
        elapsed_total, stt_status, llm_status, tts_status, current_lang, resolved["location_name"],
    )

    return {
        "transcript": transcript,
        "response": response_text,
        "reply_text": response_text,
        "speech_text": speech_text,
        "audio_base64": audio_b64,
        "audio_mime": "audio/mpeg",
        "language": current_lang,
        "keyterms": active_keyterms,
        "location": {
            "latitude": resolved["latitude"],
            "longitude": resolved["longitude"],
            "location_name": resolved["location_name"],
        },
        "status": "live",
        "pipeline": {
            "stt": stt_status,
            "llm": llm_status,
            "tts": tts_status,
        },
    }


@router.post("/query")
async def voice_query(
    audio: UploadFile = File(...),
    language: str = Form("auto"),
    browser_transcript: Optional[str] = Form(None),
    keyterms: Optional[str] = Form(None),
    lat: Optional[float] = Form(None),
    lon: Optional[float] = Form(None),
    location_name: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
):
    """
    Full live voice pipeline:
    1. Triple-verified STT: Sarvam saarika:v2.5 -> browser_transcript -> direct Gemini audio
    2. Live Gemini (gemini-3.5-flash-lite -> gemini-3.8-flash -> gemini-3.6-flash)
    3. Sarvam TTS (bulbul:v3) in detected native language
    """
    audio_bytes = await audio.read()
    if (not audio_bytes or len(audio_bytes) < 1500) and _is_garbled_transcript(browser_transcript):
        raise HTTPException(
            status_code=400,
            detail="Audio recording is empty or too short. Please speak closer to the mic.",
        )

    parsed_keyterms = None
    if keyterms:
        try:
            parsed_keyterms = json.loads(keyterms)
        except Exception:
            parsed_keyterms = [k.strip() for k in keyterms.split(",") if k.strip()]

    try:
        return await process_voice_or_text(
            query_text=None,
            audio_bytes=audio_bytes,
            browser_transcript=browser_transcript,
            language=language,
            keyterms=parsed_keyterms,
            lat=lat,
            lon=lon,
            location_name=location_name,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/text-query")
async def text_query(req: TextQueryRequest):
    """Live text-query pipeline with Gemini + location weather + cached APMC context + Sarvam TTS."""
    user_query = req.text or req.query or ""
    try:
        return await process_voice_or_text(
            query_text=user_query,
            audio_bytes=None,
            language=req.language,
            keyterms=req.keyterms,
            lat=req.lat,
            lon=req.lon,
            location_name=req.location_name,
            user_id=req.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/voice-query")
async def voice_query_alt(req: TextQueryRequest):
    """Alias endpoint for text/voice queries."""
    user_query = req.text or req.query or ""
    try:
        return await process_voice_or_text(
            query_text=user_query,
            audio_bytes=None,
            language=req.language,
            keyterms=req.keyterms,
            lat=req.lat,
            lon=req.lon,
            location_name=req.location_name,
            user_id=req.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
