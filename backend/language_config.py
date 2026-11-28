"""
Unified Pan-Indian Language & State Configuration for Farm Advisor (KrishiMitra).
Provides:
- Canonical language registry (code, English name, native script name, edge-tts neural voice, aliases)
- Language matching from text (English names, native scripts, phonetic spellings)
- State-to-default-language mapping for major Indian states
"""
import re
from typing import Dict, List, Optional

SUPPORTED_LANGUAGES: Dict[str, Dict[str, object]] = {
    "kn-IN": {
        "code": "kn-IN",
        "short_code": "kn",
        "english_name": "Kannada",
        "native_name": "ಕನ್ನಡ",
        "gemini_name": "Kannada (ಕನ್ನಡ)",
        "edge_tts_voice": "kn-IN-SapnaNeural",
        "edge_tts_fallback": "en-IN-NeerjaNeural",
        "aliases": [
            "kn", "kn-in", "kannada", "kanada", "karnataka", "ಕನ್ನಡ",
        ],
    },
    "hi-IN": {
        "code": "hi-IN",
        "short_code": "hi",
        "english_name": "Hindi",
        "native_name": "हिन्दी",
        "gemini_name": "Hindi (हिन्दी)",
        "edge_tts_voice": "hi-IN-SwaraNeural",
        "edge_tts_fallback": "en-IN-NeerjaNeural",
        "aliases": [
            "hi", "hi-in", "hindi", "hindhi", "hindustani", "हिन्दी", "हिंदी",
        ],
    },
    "te-IN": {
        "code": "te-IN",
        "short_code": "te",
        "english_name": "Telugu",
        "native_name": "తెలుగు",
        "gemini_name": "Telugu (తెలుగు)",
        "edge_tts_voice": "te-IN-ShrutiNeural",
        "edge_tts_fallback": "en-IN-NeerjaNeural",
        "aliases": [
            "te", "te-in", "telugu", "telgu", "తెలుగు",
        ],
    },
    "ta-IN": {
        "code": "ta-IN",
        "short_code": "ta",
        "english_name": "Tamil",
        "native_name": "தமிழ்",
        "gemini_name": "Tamil (தமிழ்)",
        "edge_tts_voice": "ta-IN-PallaviNeural",
        "edge_tts_fallback": "en-IN-NeerjaNeural",
        "aliases": [
            "ta", "ta-in", "tamil", "tamizh", "தமிழ்",
        ],
    },
    "mr-IN": {
        "code": "mr-IN",
        "short_code": "mr",
        "english_name": "Marathi",
        "native_name": "मराठी",
        "gemini_name": "Marathi (मराठी)",
        "edge_tts_voice": "mr-IN-AarohiNeural",
        "edge_tts_fallback": "hi-IN-SwaraNeural",
        "aliases": [
            "mr", "mr-in", "marathi", "marati", "मराठी",
        ],
    },
    "ml-IN": {
        "code": "ml-IN",
        "short_code": "ml",
        "english_name": "Malayalam",
        "native_name": "മലയാളം",
        "gemini_name": "Malayalam (മലയാളം)",
        "edge_tts_voice": "ml-IN-SobhanaNeural",
        "edge_tts_fallback": "en-IN-NeerjaNeural",
        "aliases": [
            "ml", "ml-in", "malayalam", "malyalam", "മലയാളം",
        ],
    },
    "bn-IN": {
        "code": "bn-IN",
        "short_code": "bn",
        "english_name": "Bengali",
        "native_name": "বাংলা",
        "gemini_name": "Bengali (বাংলা)",
        "edge_tts_voice": "bn-IN-TanishaaNeural",
        "edge_tts_fallback": "hi-IN-SwaraNeural",
        "aliases": [
            "bn", "bn-in", "bengali", "bangla", "bangali", "বাংলা",
        ],
    },
    "gu-IN": {
        "code": "gu-IN",
        "short_code": "gu",
        "english_name": "Gujarati",
        "native_name": "ગુજરાતી",
        "gemini_name": "Gujarati (ગુજરાતી)",
        "edge_tts_voice": "gu-IN-DhwaniNeural",
        "edge_tts_fallback": "hi-IN-SwaraNeural",
        "aliases": [
            "gu", "gu-in", "gujarati", "gujrati", "ગુજરાતી",
        ],
    },
    "pa-IN": {
        "code": "pa-IN",
        "short_code": "pa",
        "english_name": "Punjabi",
        "native_name": "ਪੰਜਾਬੀ",
        "gemini_name": "Punjabi (ਪੰਜਾਬੀ)",
        "edge_tts_voice": "pa-IN-OjasNeural",
        "edge_tts_fallback": "hi-IN-SwaraNeural",
        "aliases": [
            "pa", "pa-in", "punjabi", "panjabi", "ਪੰਜਾਬੀ", "पंजाबी",
        ],
    },
    "en-IN": {
        "code": "en-IN",
        "short_code": "en",
        "english_name": "English",
        "native_name": "English",
        "gemini_name": "English",
        "edge_tts_voice": "en-IN-NeerjaNeural",
        "edge_tts_fallback": "en-IN-NeerjaNeural",
        "aliases": [
            "en", "en-in", "en-us", "en-gb", "english", "angrezi", "inglish",
        ],
    },
}

STATE_DEFAULT_LANGUAGE: Dict[str, str] = {
    "karnataka": "kn-IN",
    "maharashtra": "mr-IN",
    "tamil nadu": "ta-IN",
    "telangana": "te-IN",
    "andhra pradesh": "te-IN",
    "kerala": "ml-IN",
    "uttar pradesh": "hi-IN",
    "punjab": "pa-IN",
    "haryana": "hi-IN",
    "madhya pradesh": "hi-IN",
    "gujarat": "gu-IN",
    "west bengal": "bn-IN",
    "rajasthan": "hi-IN",
    "bihar": "hi-IN",
    "odisha": "en-IN",
    "delhi": "hi-IN",
    "jharkhand": "hi-IN",
    "chhattisgarh": "hi-IN",
    "uttarakhand": "hi-IN",
    "himachal pradesh": "hi-IN",
    "goa": "mr-IN",
    "assam": "bn-IN",
}

MAJOR_INDIAN_STATES: List[str] = [
    "Karnataka",
    "Maharashtra",
    "Tamil Nadu",
    "Telangana",
    "Andhra Pradesh",
    "Kerala",
    "Uttar Pradesh",
    "Punjab",
    "Haryana",
    "Madhya Pradesh",
    "Gujarat",
    "West Bengal",
    "Rajasthan",
    "Bihar",
    "Odisha",
]


def get_language_config(lang_code: Optional[str], default: str = "en-IN") -> Dict[str, object]:
    """Return the unified config dict for a language code."""
    normalized = normalize_language_code(lang_code, default=default)
    return SUPPORTED_LANGUAGES.get(normalized, SUPPORTED_LANGUAGES[default])


def normalize_language_code(lang: Optional[str], default: str = "en-IN") -> str:
    """Normalize short codes, BCP-47 codes, English names, native scripts, or phonetic spellings."""
    if not lang:
        return default
    cleaned = lang.strip().lower()
    if cleaned in ("auto", "unknown"):
        return "auto"
    if lang.strip() in SUPPORTED_LANGUAGES:
        return lang.strip()
    short = cleaned.split("-")[0]
    for code, cfg in SUPPORTED_LANGUAGES.items():
        if short == cfg["short_code"] or cleaned in cfg["aliases"]:
            return code
    return default


def match_language_from_text(text: Optional[str]) -> Optional[str]:
    """
    Detect if a user's text or voice-note transcript explicitly selects or names a language
    (e.g. 'Hindi', 'हिन्दी', 'Speak in Punjabi', 'मराठी मध्ये बोला').
    Returns canonical BCP-47 code or None.
    """
    if not text:
        return None
    stripped = text.strip()
    lowered = stripped.lower()

    # Exact or near-exact match first
    for code, cfg in SUPPORTED_LANGUAGES.items():
        for alias in cfg["aliases"]:
            if lowered == alias:
                return code

    # Word-boundary / script substring match
    for code, cfg in SUPPORTED_LANGUAGES.items():
        for alias in cfg["aliases"]:
            if len(alias) <= 2:
                # Avoid false positives on 2-letter codes like 'hi', 'pa', 'mr' in normal sentences
                continue
            if alias.isascii():
                if re.search(rf"\b{re.escape(alias)}\b", lowered):
                    return code
            else:
                if alias in stripped:
                    return code
    return None


def get_default_language_for_state(state: Optional[str], default: str = "en-IN") -> str:
    """Return default regional language code for an Indian state."""
    if not state:
        return default
    return STATE_DEFAULT_LANGUAGE.get(state.strip().lower(), default)


def get_edge_tts_voice(lang_code: Optional[str]) -> str:
    """Return the primary edge-tts neural voice for a language code."""
    cfg = get_language_config(lang_code, default="en-IN")
    return str(cfg["edge_tts_voice"])


def get_edge_tts_fallback(lang_code: Optional[str]) -> str:
    """Return the fallback edge-tts neural voice for a language code."""
    cfg = get_language_config(lang_code, default="en-IN")
    return str(cfg["edge_tts_fallback"])
