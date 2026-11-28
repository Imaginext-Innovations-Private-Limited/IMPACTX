from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId


DEFAULT_ACCESSIBILITY_SETTINGS = {
    "modes": [],
    "font_size": 18,
    "font_style": "default",
    "high_contrast": False,
    "theme": "light",
    "line_spacing": 1.6,
    "letter_spacing": 0.02,
    "zoom": 100,
    "highlight_keywords": True,
    "tts_speed": 1.0,
    "tts_voice": "",
    "onboarding_completed": False,
}


def utc_now():
    return datetime.now(timezone.utc)


def to_iso(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def parse_object_id(value: str):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def serialize_user(user_doc: dict) -> dict:
    prefs = {**DEFAULT_ACCESSIBILITY_SETTINGS, **(user_doc.get("accessibility") or {})}
    return {
        "id": str(user_doc["_id"]),
        "full_name": user_doc.get("full_name", ""),
        "email": user_doc.get("email", ""),
        "accessibility": prefs,
        "created_at": to_iso(user_doc.get("created_at")),
        "updated_at": to_iso(user_doc.get("updated_at")),
    }


def serialize_document(doc: dict, include_text: bool = True) -> dict:
    payload = {
        "id": str(doc["_id"]),
        "user_id": str(doc["user_id"]),
        "filename": doc.get("filename", ""),
        "file_size": doc.get("file_size", 0),
        "page_count": doc.get("page_count", 0),
        "word_count": doc.get("word_count", 0),
        "status": doc.get("status", "ready"),
        "ocr_recommended": doc.get("ocr_recommended", False),
        "extraction_method": doc.get("extraction_method", "pymupdf"),
        "status_message": doc.get("status_message", ""),
        "has_simplification": bool(doc.get("latest_simplification")),
        "created_at": to_iso(doc.get("created_at")),
        "updated_at": to_iso(doc.get("updated_at")),
    }
    if include_text:
        payload["extracted_text"] = doc.get("extracted_text", "")
        payload["pages"] = doc.get("pages", [])
        payload["latest_simplification"] = doc.get("latest_simplification")
    return payload
