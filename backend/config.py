"""
Sprint 4 configuration — loads .env and exposes API key helpers.
Every endpoint checks has_gemini() / has_sarvam() / has_data_gov() before
calling live APIs; falls back gracefully to SQLite/mock data when absent.
"""
import os
try:
    from dotenv import load_dotenv
    load_dotenv()           # reads .env from current working directory
except ImportError:
    pass                    # python-dotenv not installed; env vars still work via OS

GEMINI_API_KEY: str  = os.getenv("GEMINI_API_KEY", "").strip()
SARVAM_API_KEY: str  = os.getenv("SARVAM_API_KEY", "").strip()
DATA_GOV_API_KEY: str = os.getenv("DATA_GOV_API_KEY", "").strip()
WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "krishimitra_verify").strip()
WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()


def has_gemini() -> bool:
    return bool(GEMINI_API_KEY)


def has_sarvam() -> bool:
    return bool(SARVAM_API_KEY)


def has_data_gov() -> bool:
    return bool(DATA_GOV_API_KEY)


def has_whatsapp() -> bool:
    return bool(WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID)


def api_status_pill() -> dict:
    """Return a summary dict the frontend can render as status pills."""
    return {
        "gemini": "live" if has_gemini() else "demo",
        "sarvam": "live" if has_sarvam() else "demo",
        "data_gov": "live" if has_data_gov() else "demo",
    }
