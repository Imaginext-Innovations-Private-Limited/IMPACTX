"""
FasalSaarathi — Module 1: Picture-PIN Authentication & Farmer Profile Store
==========================================================================
Provides passwordless 4-icon Picture-PIN registration/login, Guest mode,
and persistent farmer/terrace-grower context in `data/fasalsaarathi_users.db`.

Shared Data Contract (`users` table):
  user_id, name, phone, pin_icons (PBKDF2 hashed), persona ("farmer"|"terrace"),
  language ("en"|"kn"|"hi"|"ta"|"te"|"mr"), location_query, lat, lon, primary_crop
"""

import os
import re
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from werkzeug.security import check_password_hash, generate_password_hash

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_USERS_DB = os.path.join(PROJECT_ROOT, "data", "fasalsaarathi_users.db")

SUPPORTED_LANGS = ("en", "kn", "hi", "ta", "te", "mr")
VALID_PERSONAS = ("farmer", "terrace")

# 6 universal farm icons for the visual 4-icon Picture-PIN
PICTURE_PIN_ICONS: List[Dict[str, Any]] = [
    {
        "id": "tomato",
        "emoji": "🍅",
        "labels": {
            "en": "Tomato", "kn": "ಟೊಮೆಟೊ", "hi": "टमाटर",
            "ta": "தக்காளி", "te": "టమాటా", "mr": "टोमॅटो",
        },
    },
    {
        "id": "sun",
        "emoji": "☀️",
        "labels": {
            "en": "Sun", "kn": "ಸೂರ್ಯ", "hi": "सूरज",
            "ta": "சூரியன்", "te": "సూర్యుడు", "mr": "सूर्य",
        },
    },
    {
        "id": "tractor",
        "emoji": "🚜",
        "labels": {
            "en": "Tractor", "kn": "ಟ್ರ್ಯಾಕ್ಟರ್", "hi": "ट्रैक्टर",
            "ta": "டிராக்டர்", "te": "ట్రాక్టర్", "mr": "ट्रॅक्टर",
        },
    },
    {
        "id": "wheat",
        "emoji": "🌾",
        "labels": {
            "en": "Crop", "kn": "ಬೆಳೆ", "hi": "फसल",
            "ta": "பயிர்", "te": "పంట", "mr": "पीक",
        },
    },
    {
        "id": "water",
        "emoji": "💧",
        "labels": {
            "en": "Water", "kn": "ನೀರು", "hi": "पानी",
            "ta": "தண்ணீர்", "te": "నీరు", "mr": "पाणी",
        },
    },
    {
        "id": "sprout",
        "emoji": "🌱",
        "labels": {
            "en": "Sprout", "kn": "ಮೊಳಕೆ", "hi": "पौधा",
            "ta": "நாற்று", "te": "మొక్క", "mr": "रोप",
        },
    },
]

VALID_ICON_IDS = {item["id"] for item in PICTURE_PIN_ICONS}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_phone(phone: str) -> str:
    """Extract digits and normalize Indian 10-digit mobile numbers."""
    digits = re.sub(r"\D", "", str(phone or ""))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits


def _normalize_pin_icons(pin_icons: Any) -> Optional[str]:
    """Validate a 4-icon Picture-PIN sequence and return canonical 'a|b|c|d' string."""
    if isinstance(pin_icons, str):
        parts = [p.strip().lower() for p in re.split(r"[,|\s]+", pin_icons) if p.strip()]
    elif isinstance(pin_icons, (list, tuple)):
        parts = [str(p).strip().lower() for p in pin_icons if str(p).strip()]
    else:
        return None

    if len(parts) != 4 or any(p not in VALID_ICON_IDS for p in parts):
        return None
    return "|".join(parts)


def _row_to_profile(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "user_id": row["user_id"],
        "name": row["name"],
        "phone": row["phone"],
        "persona": row["persona"],
        "language": row["language"],
        "location_query": row["location_query"] or "",
        "lat": row["lat"],
        "lon": row["lon"],
        "primary_crop": row["primary_crop"] or "tomato",
        "is_guest": row["user_id"] == "guest",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db(db_path: str = DEFAULT_USERS_DB) -> None:
    """Initialize the shared SQLite `users` table and ensure the `guest` profile exists."""
    with closing(_connect(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                pin_icons TEXT NOT NULL,
                persona TEXT NOT NULL DEFAULT 'farmer',
                language TEXT NOT NULL DEFAULT 'en',
                location_query TEXT DEFAULT '',
                lat REAL,
                lon REAL,
                primary_crop TEXT DEFAULT 'tomato',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        now = _now_iso()
        conn.execute(
            """
            INSERT OR IGNORE INTO users (
                user_id, name, phone, pin_icons, persona, language,
                location_query, lat, lon, primary_crop, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "guest",
                "Guest Farmer",
                "0000000000",
                generate_password_hash("tomato|sun|tractor|wheat"),
                "farmer",
                "en",
                "",
                None,
                None,
                "tomato",
                now,
                now,
            ),
        )
        conn.commit()


def register_user(
    name: str,
    phone: str,
    pin_icons: Any,
    persona: str = "farmer",
    language: str = "en",
    location_query: str = "",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    primary_crop: str = "tomato",
    db_path: str = DEFAULT_USERS_DB,
) -> Dict[str, Any]:
    """Register a new farmer or terrace grower using a 4-icon Picture-PIN."""
    init_auth_db(db_path)

    clean_name = (name or "").strip()
    if len(clean_name) < 2 or len(clean_name) > 60:
        return {"status": "error", "message": "Please enter your name (2 to 60 characters)."}

    norm_phone = _normalize_phone(phone)
    if len(norm_phone) != 10 or norm_phone == "0000000000":
        return {"status": "error", "message": "Please enter a valid 10-digit mobile number."}

    canonical_pin = _normalize_pin_icons(pin_icons)
    if not canonical_pin:
        return {"status": "error", "message": "Please select exactly 4 picture icons for your PIN."}

    clean_persona = (persona or "farmer").strip().lower()
    if clean_persona not in VALID_PERSONAS:
        clean_persona = "farmer"

    clean_lang = (language or "en").strip().lower()
    if clean_lang not in SUPPORTED_LANGS:
        clean_lang = "en"

    clean_loc = (location_query or "").strip()[:100]
    clean_crop = (primary_crop or "tomato").strip().lower()[:40] or "tomato"

    pin_hash = generate_password_hash(canonical_pin)
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    now = _now_iso()

    try:
        with closing(_connect(db_path)) as conn:
            conn.execute(
                """
                INSERT INTO users (
                    user_id, name, phone, pin_icons, persona, language,
                    location_query, lat, lon, primary_crop, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id, clean_name, norm_phone, pin_hash, clean_persona,
                    clean_lang, clean_loc, lat, lon, clean_crop, now, now,
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return {"status": "success", "user": _row_to_profile(row)}
    except sqlite3.IntegrityError:
        return {
            "status": "duplicate_phone",
            "message": "This mobile number is already registered. Please log in with your 4-picture PIN.",
        }


def login_user(
    phone: str,
    pin_icons: Any,
    db_path: str = DEFAULT_USERS_DB,
) -> Dict[str, Any]:
    """Authenticate a user by 10-digit mobile number and 4-icon Picture-PIN."""
    init_auth_db(db_path)

    norm_phone = _normalize_phone(phone)
    if len(norm_phone) != 10 or norm_phone == "0000000000":
        return {"status": "error", "message": "Please enter a valid 10-digit mobile number."}

    canonical_pin = _normalize_pin_icons(pin_icons)
    if not canonical_pin:
        return {"status": "error", "message": "Please tap all 4 icons of your Picture-PIN."}

    with closing(_connect(db_path)) as conn:
        row = conn.execute("SELECT * FROM users WHERE phone = ?", (norm_phone,)).fetchone()

    if not row or not check_password_hash(row["pin_icons"], canonical_pin):
        return {"status": "unauthorized", "message": "Mobile number or Picture-PIN did not match."}

    return {"status": "success", "user": _row_to_profile(row)}


def get_guest_profile(db_path: str = DEFAULT_USERS_DB) -> Dict[str, Any]:
    """Return the built-in Guest demo profile."""
    init_auth_db(db_path)
    with closing(_connect(db_path)) as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = 'guest'").fetchone()
    return {"status": "success", "user": _row_to_profile(row)}


def get_user_profile(user_id: str, db_path: str = DEFAULT_USERS_DB) -> Optional[Dict[str, Any]]:
    """Fetch a user's saved profile by user_id, or None if not found."""
    if not user_id:
        return None
    init_auth_db(db_path)
    with closing(_connect(db_path)) as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return _row_to_profile(row) if row else None


def update_user_profile(
    user_id: str,
    updates: Dict[str, Any],
    db_path: str = DEFAULT_USERS_DB,
) -> Dict[str, Any]:
    """Update persona, language, location, GPS coordinates, or primary crop for a user."""
    init_auth_db(db_path)
    existing = get_user_profile(user_id, db_path=db_path)
    if not existing:
        return {"status": "not_found", "message": "User profile not found."}

    name = (updates.get("name") or existing["name"]).strip()[:60] or existing["name"]

    persona = (updates.get("persona") or existing["persona"]).strip().lower()
    if persona not in VALID_PERSONAS:
        persona = existing["persona"]

    language = (updates.get("language") or existing["language"]).strip().lower()
    if language not in SUPPORTED_LANGS:
        language = existing["language"]

    if "location_query" in updates:
        location_query = str(updates.get("location_query") or "").strip()[:100]
    else:
        location_query = existing["location_query"]

    lat = updates["lat"] if "lat" in updates else existing["lat"]
    lon = updates["lon"] if "lon" in updates else existing["lon"]
    if lat is not None:
        try:
            lat = float(lat)
        except (TypeError, ValueError):
            lat = existing["lat"]
    if lon is not None:
        try:
            lon = float(lon)
        except (TypeError, ValueError):
            lon = existing["lon"]

    primary_crop = (updates.get("primary_crop") or existing["primary_crop"]).strip().lower()[:40]
    if not primary_crop:
        primary_crop = existing["primary_crop"]

    now = _now_iso()
    with closing(_connect(db_path)) as conn:
        conn.execute(
            """
            UPDATE users
            SET name = ?, persona = ?, language = ?, location_query = ?,
                lat = ?, lon = ?, primary_crop = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (name, persona, language, location_query, lat, lon, primary_crop, now, user_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    return {"status": "success", "user": _row_to_profile(row)}
