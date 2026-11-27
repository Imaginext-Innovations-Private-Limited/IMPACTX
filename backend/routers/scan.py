"""
High-Accuracy Multimodal Photo Scanner Router — Live Gemini Vision Only.
Supports Web UI 4-mode Scanner + WhatsApp Image & Question/Caption analysis.
Never uses canned/mock fallback data; always places the structured text prompt
BEFORE the image in Gemini's contents array and injects live local weather.
"""
import io
import json
import logging
import time
from typing import Optional, Tuple

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

import config
import location_service

logger = logging.getLogger("scan")

router = APIRouter(prefix="/api/scan", tags=["scanner"])

LANGUAGE_NAMES = {
    "kn": "Kannada (ಕನ್ನಡ)",
    "hi": "Hindi (हिन्दी)",
    "ta": "Tamil (தமிழ்)",
    "te": "Telugu (తెలుగు)",
    "mr": "Marathi (मराठी)",
    "en": "English",
}


def _resolve_language_label(language_code: Optional[str]) -> str:
    if not language_code:
        return "English"
    short = language_code.strip().lower().split("-")[0]
    return LANGUAGE_NAMES.get(short, "English")


# ─────────────────────── GEMINI PROMPT BUILDER ───────────────────────────────

_UNIFIED_SCHEMA = json.dumps(
    {
        "image_classification": "diseased_leaf_or_pest | crop | agrochemical_label | soil | unclear_or_blurry",
        "detected_mode": "disease | crop | agrochemical | soil | blurry",
        "is_blurry_or_unreadable": False,
        "retake_photo_message": "string (non-empty ONLY if image is blurry/dark/unreadable; ask farmer in native language to retake closer well-lit photo)",
        "direct_answer_to_question": "string (direct answer in native language to user's caption/question if provided, else empty string)",
        "formatted_whatsapp_reply": "string (complete WhatsApp-formatted advisory in native language covering classification, details, weather-aware cause, uses/dosage per L/200L barrel/acre, safety/PHI cautions, or retake request if blurry)",
        "detected_crop": "string (for crop/disease)",
        "lifespan": "string",
        "suitable_soil": ["string"],
        "cultivation_steps": ["string"],
        "crop_height_cm": {"min": 0, "max": 0},
        "spacing_cm": {"row": 0, "plant": 0},
        "water_requirement_mm": {"total": 0},
        "irrigation_method": "string",
        "harvest_timing": "string",
        "expected_yield_tons_per_ha": {"min": 0, "max": 0},
        "msp_rs_per_quintal": 0,
        "disease_name": "string (exact common + scientific name of disease/pest)",
        "affected_parts": ["string"],
        "symptoms": "string (visible symptoms observed in the photo)",
        "cause": "string (why it happened, factoring in user's local weather)",
        "severity": "Low | Moderate | High | Severe",
        "organic_treatments": ["string (step-by-step organic treatment with exact dosage per L / 200L barrel / acre)"],
        "chemical_treatments": ["string (approved chemical treatment with exact dosage per L / 200L barrel / acre)"],
        "recommended_fertilizers": "string",
        "recommended_pesticides": ["string"],
        "spray_frequency": "string",
        "prevention": "string",
        "product_name": "string (exact product name read from label)",
        "type": "string (Insecticide / Fungicide / Herbicide / Fertilizer / Micronutrient)",
        "manufacturer": "string",
        "active_ingredient": "string (active ingredient / NPK ratio read from label)",
        "purpose": "string (uses: which crops, pests, diseases, or deficiencies)",
        "uses": ["string (crops, target pests/diseases, or nutrient deficiencies)"],
        "using_method": "string (step-by-step mixing rules, spray timing, nozzle/application method)",
        "dosage": {
            "per_litre": "string",
            "per_acre": "string",
            "per_barrel_200L": "string",
            "per_knapsack_15L": "string",
        },
        "application_method": "string",
        "suitable_weather": "string",
        "crops_suitable": ["string"],
        "side_effects": ["string"],
        "safety_cautions": ["string (PPE, waiting/PHI period in days, rainfastness, toxicity warnings)"],
        "mfr_date_check": "string",
        "soil_type": "string",
        "characteristics": {
            "pH": "string",
            "texture": "string",
            "organic_matter": "string",
            "drainage": "string",
            "water_retention": "string",
            "colour": "string",
        },
        "deficiencies": ["string"],
        "amendments_recommended": ["string"],
        "current_weather_context": "string",
        "ranked_suitable_crops": [{"rank": 1, "crop": "string", "reason": "string"}],
        "not_recommended": ["string"],
    },
    indent=2,
)


def _build_vision_prompt(
    mode_hint: str,
    question: Optional[str],
    language_label: str,
    weather_summary: str,
    mandi_summary: str,
) -> str:
    question_block = (
        f'User Question / Image Caption: "{question.strip()}"\n'
        f"You MUST directly and specifically answer this question in `direct_answer_to_question` and `formatted_whatsapp_reply`."
        if question and question.strip()
        else "User Question / Image Caption: None provided. Provide full proactive advisory."
    )

    mode_guidance = (
        f"Requested Scanner Mode Hint: {mode_hint}. "
        f"(First visually verify what is actually in the photo! If the photo is clearly a pesticide/fertilizer bottle/bag, classify it as `agrochemical_label` even if the hint was `auto` or `disease`; if it is blurry/unreadable, classify as `unclear_or_blurry`.)"
    )

    return f"""You are an expert Indian agricultural scientist, plant pathologist, soil agronomist, and agrochemical label specialist.

{mode_guidance}
{question_block}
Response Language: {language_label} — ALL descriptive text values, advice, treatment steps, safety cautions, `direct_answer_to_question`, `retake_photo_message`, and `formatted_whatsapp_reply` MUST be written STRICTLY in {language_label} (using its native script).

=== REAL-TIME LOCAL WEATHER & LOCATION CONTEXT ===
{weather_summary}

=== CACHED APMC MANDI CONTEXT ===
{mandi_summary}

=== CRITICAL CLASSIFICATION & ACCURACY RULES ===
1. FIRST classify the image accurately into one of:
   - `diseased_leaf_or_pest`: Diseased leaf, pest-damaged plant, insect, or fungal/bacterial/viral crop symptom.
   - `crop`: Healthy crop/plant identification & cultivation guidance.
   - `agrochemical_label`: Pesticide bottle, fungicide pack, herbicide container, fertilizer bag, or agrochemical label.
   - `soil`: Soil sample / field soil photo.
   - `unclear_or_blurry`: Photo is too blurry, dark, distant, out-of-focus, or occluded to read the label text or inspect leaf lesions.
2. IF `unclear_or_blurry` (too blurry/dark to read label or inspect leaf):
   - Set `"is_blurry_or_unreadable": true`, `"detected_mode": "blurry"`.
   - NEVER guess a product name, active ingredient, or disease, and NEVER return generic placeholder text.
   - Write a clear, polite message in `retake_photo_message` and `formatted_whatsapp_reply` (and put the same retake notice in `symptoms` / `purpose` / `disease_name` / `product_name` so any UI card displays it clearly) in {language_label} asking the farmer to retake a closer, sharper, well-lit photo (e.g., hold camera steady 15–20 cm from the label or affected leaf in daylight).
3. IF `diseased_leaf_or_pest` (or `crop` with symptoms):
   - Identify the exact crop and exact disease/pest (common + scientific name).
   - List visible symptoms actually seen in the image.
   - Explain WHY it happened, explicitly factoring in the farmer's local weather above (humidity, rain, temperature).
   - Give step-by-step organic AND chemical treatments with exact dosage per liter (mL/L or g/L), per 200L barrel, and per acre, plus spray frequency and prevention.
4. IF `agrochemical_label` (Pesticide / Fertilizer Bottle, Bag, or Label):
   - Read the EXACT product name, active ingredient, and/or NPK ratio directly from the visible label.
   - Explain its **Uses** (`purpose`, `uses`, `crops_suitable`): exact crops, target pests/diseases, or nutrient deficiencies.
   - Explain its **Using Method** (`using_method`, `dosage`, `application_method`): exact dosage per acre, per 200L barrel, per 15L knapsack, and per liter, plus spray timing and mixing rules (e.g., jar test, water volume, morning/evening).
   - Explain its **Safety Cautions** (`safety_cautions`, `side_effects`, `suitable_weather`): PPE (gloves, mask, full sleeves), Pre-Harvest Interval (PHI / waiting period in days), rainfastness window, and toxicity warnings (bees, fish, humans).
   - Directly answer any specific question the farmer asked in `direct_answer_to_question` and inside `formatted_whatsapp_reply`.
5. IF `soil`:
   - Identify soil type from colour/texture/structure, list likely deficiencies, amendments with per-acre dosage, and top 5 ranked suitable crops considering the local weather above.
6. Return ONLY a valid JSON object matching this schema (omit or leave empty strings/arrays for unrelated mode fields):
{_UNIFIED_SCHEMA}"""


class ScanResultSchema(BaseModel):
    category: str  # "disease" | "agrochemical" | "crop" | "soil" | "blurry"
    title: str
    summary: str
    uses_or_symptoms: list[str]
    dosage_and_method: str
    safety_cautions: list[str]
    weather_note: str
    is_blurry_or_unreadable: bool = False
    retake_photo_message: str = ""
    direct_answer_to_question: str = ""


def _safe_parse_scan_json(raw_text: str) -> dict:
    """Strip markdown fences and parse JSON, salvaging partial text on JSONDecodeError."""
    text = (raw_text or "").strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1].strip()
            if text.startswith("json"):
                text = text[4:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("[Gemini Vision] JSONDecodeError (%s); salvaging partial text", exc)
        cleaned = text.replace("{", " ").replace("}", " ").replace('"', "").strip()
        return {
            "category": "crop",
            "title": "Live Photo Analysis",
            "summary": cleaned[:1200] if cleaned else "Partial analysis received. Please try again with a clearer photo.",
            "uses_or_symptoms": [],
            "dosage_and_method": "",
            "safety_cautions": [],
            "weather_note": "",
            "is_blurry_or_unreadable": False,
            "retake_photo_message": "",
            "direct_answer_to_question": "",
        }


def _enrich_scan_dict(parsed: dict) -> dict:
    """Map ScanResultSchema fields onto the UI & WhatsApp response keys."""
    cat = (parsed.get("category") or "crop").strip().lower()
    if cat not in ("disease", "agrochemical", "crop", "soil", "blurry"):
        cat = "crop"
    title = parsed.get("title") or "Analysis Result"
    summary = parsed.get("summary") or ""
    uses_or_symptoms = parsed.get("uses_or_symptoms") or []
    dosage_and_method = parsed.get("dosage_and_method") or ""
    safety_cautions = parsed.get("safety_cautions") or []
    weather_note = parsed.get("weather_note") or ""
    is_blurry = bool(parsed.get("is_blurry_or_unreadable")) or cat == "blurry"
    retake_msg = parsed.get("retake_photo_message") or (summary if is_blurry else "")
    direct_ans = parsed.get("direct_answer_to_question") or ""

    enriched = dict(parsed)
    enriched["detected_mode"] = "blurry" if is_blurry else cat
    enriched["is_blurry_or_unreadable"] = is_blurry
    enriched["retake_photo_message"] = retake_msg
    enriched["direct_answer_to_question"] = direct_ans

    if cat == "agrochemical":
        enriched.setdefault("product_name", title)
        enriched.setdefault("purpose", summary)
        enriched.setdefault("uses", uses_or_symptoms)
        enriched.setdefault("using_method", dosage_and_method)
        enriched.setdefault("safety_cautions", safety_cautions)
    elif cat == "disease":
        enriched.setdefault("disease_name", title)
        enriched.setdefault("symptoms", summary)
        enriched.setdefault("cause", weather_note)
        enriched.setdefault("organic_treatments", uses_or_symptoms)
        enriched.setdefault("spray_frequency", dosage_and_method)
        enriched.setdefault("safety_cautions", safety_cautions)
    elif cat == "soil":
        enriched.setdefault("soil_type", title)
        enriched.setdefault("current_weather_context", weather_note or summary)
        enriched.setdefault("amendments_recommended", uses_or_symptoms)
        enriched.setdefault("using_method", dosage_and_method)
        enriched.setdefault("safety_cautions", safety_cautions)
    else:
        enriched.setdefault("detected_crop", title)
        enriched.setdefault("cultivation_steps", uses_or_symptoms)
        enriched.setdefault("using_method", dosage_and_method)
        enriched.setdefault("safety_cautions", safety_cautions)

    wa_lines = []
    if direct_ans:
        wa_lines.append(f"💬 {direct_ans}\n")
    wa_lines.append(f"*{title}*")
    if summary:
        wa_lines.append(summary)
    if uses_or_symptoms:
        wa_lines.append("\n• " + "\n• ".join(str(x) for x in uses_or_symptoms[:5]))
    if dosage_and_method:
        wa_lines.append(f"\n💧 {dosage_and_method}")
    if weather_note:
        wa_lines.append(f"\n🌦️ {weather_note}")
    if safety_cautions:
        wa_lines.append("\n⚠️ " + "; ".join(str(x) for x in safety_cautions[:4]))
    enriched["formatted_whatsapp_reply"] = retake_msg if is_blurry else "\n".join(wa_lines)
    return enriched


def _detect_mime(image_bytes: bytes) -> str:
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _compress_image_for_gemini(image_bytes: bytes, max_dim: int = 768, quality: int = 75) -> Tuple[bytes, str]:
    """
    Resize image to a maximum dimension of 768x768 and convert to JPEG (quality=75)
    using Pillow so Gemini Vision upload and inference are fast and reliable.
    """
    try:
        from PIL import Image, ImageOps

        with Image.open(io.BytesIO(image_bytes)) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                rgba_img = img.convert("RGBA")
                background.paste(rgba_img, mask=rgba_img.split()[3])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.BICUBIC)
            img.thumbnail((max_dim, max_dim), resample)

            out_buf = io.BytesIO()
            img.save(out_buf, format="JPEG", quality=quality, optimize=True)
            compressed = out_buf.getvalue()
            logger.info(
                "[Image Compress] Resized/compressed %d bytes -> %d bytes (max=%dx%d, JPEG q=%d)",
                len(image_bytes), len(compressed), max_dim, max_dim, quality,
            )
            return compressed, "image/jpeg"
    except Exception as exc:
        logger.warning("[Image Compress] Pillow compression failed (%s); sending original bytes", exc)
        return image_bytes, _detect_mime(image_bytes)


def _call_gemini_vision(
    image_bytes: bytes,
    mode: str,
    question: Optional[str] = None,
    language: str = "en-IN",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    location_name: Optional[str] = None,
    user_id: Optional[str] = None,
) -> dict:
    """
    Call Gemini Vision (gemini-3.8-flash -> gemini-3.6-flash -> gemini-3.5-flash-lite)
    with the structured text prompt BEFORE the image in `contents`.
    Logs exact exceptions and raises on failure (no mock/canned fallback).
    """
    import google.genai as genai
    from google.genai import errors as gerrors
    from google.genai import types as gtypes

    if not config.has_gemini():
        err_msg = "GEMINI_API_KEY is missing; cannot analyze image."
        logger.error("[Gemini Vision] %s", err_msg)
        print(f"[Gemini Vision ERROR] {err_msg}", flush=True)
        raise RuntimeError(err_msg)

    resolved = location_service.resolve_coordinates(
        lat=lat, lon=lon, location_name=location_name, user_id=user_id
    )
    if resolved["latitude"] is not None and resolved["longitude"] is not None:
        weather_info = location_service.fetch_live_weather_sync(
            resolved["latitude"], resolved["longitude"], resolved["location_name"]
        )
        weather_summary = weather_info["summary_text"]
    else:
        weather_summary = f"Location: {resolved['location_name']}. No GPS coordinates provided for this scan."

    mandi_summary = location_service.get_cached_mandi_prices_context(limit_commodities=6, limit_mandis=6)
    language_label = _resolve_language_label(language)

    prompt = _build_vision_prompt(
        mode_hint=mode,
        question=question,
        language_label=language_label,
        weather_summary=weather_summary,
        mandi_summary=mandi_summary,
    )

    compressed_bytes, mime = _compress_image_for_gemini(image_bytes, max_dim=768, quality=75)
    client = genai.Client(
        api_key=config.GEMINI_API_KEY,
        http_options=gtypes.HttpOptions(
            timeout=25000,
            retry_options=gtypes.HttpRetryOptions(attempts=1),
        ),
    )

    # CRITICAL: Structured text prompt MUST appear BEFORE the image in `contents`
    contents = [
        prompt,
        gtypes.Part.from_bytes(data=compressed_bytes, mime_type=mime),
    ]

    candidate_models = ["gemini-3.6-flash", "gemini-3.8-flash", "gemini-3.5-flash-lite"]
    last_error: Optional[Exception] = None

    for model_name in candidate_models:
        try:
            t0 = time.perf_counter()
            logger.info(
                "[Gemini Vision] Calling %s (mode=%s, lang=%s, compressed_bytes=%d)...",
                model_name, mode, language, len(compressed_bytes),
            )
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=gtypes.GenerateContentConfig(
                    system_instruction=(
                        f"You are Farm Advisor Multimodal Vision AI. Always reply in {language_label}. "
                        f"Keep each field concise and accurate. "
                        f"Local Context: {weather_summary}"
                    ),
                    response_mime_type="application/json",
                    response_schema=ScanResultSchema,
                    max_output_tokens=2500,
                    thinking_config=gtypes.ThinkingConfig(thinking_level="LOW"),
                ),
            )
            parsed = _safe_parse_scan_json(response.text or "")
            enriched = _enrich_scan_dict(parsed)
            logger.info("[Gemini Vision] %s succeeded in %.2fs", model_name, time.perf_counter() - t0)
            enriched["_model_used"] = model_name
            enriched["_weather_context"] = weather_summary
            return enriched
        except gerrors.ServerError as exc:
            last_error = exc
            logger.error("[Gemini Vision] ServerError (503/504) on %s: %s", model_name, exc, exc_info=True)
            print(f"[Gemini Vision SERVER ERROR] Model {model_name} failed: {exc}", flush=True)
            continue
        except Exception as exc:
            last_error = exc
            logger.error("[Gemini Vision] Model %s failed: %s: %s", model_name, type(exc).__name__, exc, exc_info=True)
            print(f"[Gemini Vision ERROR] Model {model_name} failed: {type(exc).__name__}: {exc}", flush=True)
            continue

    raise RuntimeError(f"All Gemini Vision models failed ({candidate_models}): {last_error}")


# ─────────────────────────── ENDPOINTS ───────────────────────────────────────

class ScanModeInfo(BaseModel):
    id: str
    label: str
    icon: str
    description: str


SCAN_MODES = [
    ScanModeInfo(
        id="crop",
        label="Crop Info",
        icon="Sprout",
        description="Identify crop: lifespan, soil, cultivation steps, yield",
    ),
    ScanModeInfo(
        id="disease",
        label="Crop Disease",
        icon="Bug",
        description="Diagnose disease/pest: cause, organic & chemical treatments",
    ),
    ScanModeInfo(
        id="agrochemical",
        label="Fertilizer / Pesticide",
        icon="FlaskConical",
        description="Scan bottle/bag: dosage per acre, per barrel, spraying guide",
    ),
    ScanModeInfo(
        id="soil",
        label="Soil Analysis",
        icon="Mountain",
        description="Identify soil type and get ranked crop recommendations",
    ),
]


MODE_NAMES = {
    "auto": "Smart Auto Analysis",
    "crop": "Crop Info",
    "disease": "Crop Disease",
    "agrochemical": "Fertilizer / Pesticide",
    "soil": "Soil Analysis",
    "blurry": "Unclear / Blurry Photo",
}

MODE_NORMALIZATION = {
    "auto": "auto",
    "1": "crop",
    "crop": "crop",
    "crop info": "crop",
    "2": "disease",
    "disease": "disease",
    "crop disease": "disease",
    "3": "agrochemical",
    "agrochemical": "agrochemical",
    "fertilizer": "agrochemical",
    "pesticide": "agrochemical",
    "fertilizer / pesticide": "agrochemical",
    "4": "soil",
    "soil": "soil",
    "soil analysis": "soil",
}


def process_scan_bytes(
    image_bytes: bytes,
    mode: str = "auto",
    filename: str = "scan.jpg",
    question: Optional[str] = None,
    language: str = "en-IN",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    location_name: Optional[str] = None,
    user_id: Optional[str] = None,
) -> dict:
    """Process image scan live via Gemini Vision (no mock/canned fallback)."""
    if not image_bytes:
        raise ValueError("Uploaded image bytes are empty.")

    raw_mode_str = str(mode or "auto").strip().lower()
    norm_mode = MODE_NORMALIZATION.get(raw_mode_str, "auto")
    file_size_kb = round(len(image_bytes) / 1024, 1)

    result = _call_gemini_vision(
        image_bytes=image_bytes,
        mode=norm_mode,
        question=question,
        language=language,
        lat=lat,
        lon=lon,
        location_name=location_name,
        user_id=user_id,
    )

    detected_mode = result.get("detected_mode") or norm_mode
    if detected_mode == "auto":
        cls_map = {
            "diseased_leaf_or_pest": "disease",
            "agrochemical_label": "agrochemical",
            "soil": "soil",
            "crop": "crop",
            "unclear_or_blurry": "blurry",
        }
        detected_mode = cls_map.get(result.get("image_classification", ""), "crop")

    effective_mode = detected_mode if (norm_mode == "auto" or detected_mode in ("crop", "disease", "agrochemical", "soil")) else norm_mode
    if result.get("is_blurry_or_unreadable"):
        effective_mode = "blurry" if norm_mode == "auto" else norm_mode

    if "mode_name" not in result:
        result["mode_name"] = MODE_NAMES.get(effective_mode, "Smart Analysis")

    model_used = result.pop("_model_used", "gemini-3.8-flash")
    weather_ctx = result.pop("_weather_context", None)

    return {
        "mode": effective_mode,
        "requested_mode": norm_mode,
        "status": "live",
        "api": f"Live Gemini Vision ({model_used})",
        "language": language,
        "weather_context": weather_ctx,
        "filename": filename,
        "file_size_kb": file_size_kb,
        "result": result,
        "analysis": result,
    }


@router.get("/modes")
def get_scan_modes():
    return [m.model_dump() for m in SCAN_MODES]


@router.post("")
@router.post("/")
async def scan_image(
    file: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    mode: str = Form("auto"),
    question: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    language: str = Form("en-IN"),
    lat: Optional[float] = Form(None),
    lon: Optional[float] = Form(None),
    location_name: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
):
    """
    Live Multimodal Smart Scanner.
    Accepts image + optional mode, question/caption, language, and lat/lon/location_name.
    """
    upload_file = file or image
    if not upload_file:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    raw_mode_str = str(mode).strip().lower()
    norm_mode = MODE_NORMALIZATION.get(raw_mode_str)
    if not norm_mode:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{mode}'. Choose: auto, crop, disease, agrochemical, soil (or 1, 2, 3, 4)",
        )

    image_bytes = await upload_file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    filename = upload_file.filename or f"scan_{norm_mode}.jpg"
    effective_question = question or caption

    try:
        return process_scan_bytes(
            image_bytes=image_bytes,
            mode=norm_mode,
            filename=filename,
            question=effective_question,
            language=language,
            lat=lat,
            lon=lon,
            location_name=location_name,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
