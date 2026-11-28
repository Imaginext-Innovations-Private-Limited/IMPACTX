"""
FasalSaarathi — Live All-India APMC Mandi Market Prices & Farmer Selling Guide
===========================================================================
100% Real Data • Zero Hardcoded Price Dictionaries • Plain Farmer Language

Data Pipeline:
1. Geocodes any Indian village, taluk, district, 6-digit PIN code, Indic place name,
   or exact GPS (lat, lon) via `geocode_india_location` to find the farmer's district,
   state, and coordinates.
2. Fetches live daily APMC wholesale market arrivals (Lowest, Usual/Average, Highest
   rate per 100 kg Quintal & per 1 kg + arrival date) across all Indian states from:
   - Official OGD India `api.data.gov.in` Agmarknet resource (when `DATA_GOV_API_KEY` is set)
   - Live pan-India Agmarknet APMC market feeds (state/district APMC tables & multi-day history)
   - Official Ministry of Agriculture Agmarknet 2.0 open national daily summary & 2026-27 MSP API
3. Ranks nearby APMC yards by real GPS Haversine distance (km) from the farmer's farm,
   computes real multi-day price movement (Going Up / Steady / Going Down), compares
   against Government Support Price (MSP) where applicable, and caches real records in
   SQLite (`data/mandi_cache.db`) for offline reliability.
"""

import math
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

from tools.weather_tool import geocode_location

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CACHE_DB_PATH = os.path.join(DATA_DIR, "mandi_cache.db")

MAX_CACHE_AGE_SECONDS = 7 * 24 * 3600  # 7 days max offline market history validity

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}

AGMARKNET_HEADERS = {
    "User-Agent": HTTP_HEADERS["User-Agent"],
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://agmarknet.gov.in",
    "Referer": "https://agmarknet.gov.in/",
}

# Commodity slug & multilingual alias mapping (NO prices stored here — only names & URL slugs!)
# Tuple format: (display_name_en, kisandeals_slug, commodityonline_slug, agmarknet_match_substr)
COMMODITY_CATALOG: Dict[str, Tuple[str, str, str, str]] = {
    "tomato": ("Tomato", "TOMATO", "tomato", "tomato"),
    "onion": ("Onion", "ONION", "onion", "onion"),
    "potato": ("Potato", "POTATO", "potato", "potato"),
    "green_chilli": ("Green Chilli", "GREEN-CHILLI", "green-chilli", "green chilli"),
    "dry_chilli": ("Dry Red Chilli", "DRY-CHILLIES", "dry-chillies", "dry chillies"),
    "paddy": ("Paddy (Rice)", "PADDY-DHAN-COMMON", "paddy-dhan-common", "paddy(common)"),
    "wheat": ("Wheat", "WHEAT", "wheat", "wheat"),
    "maize": ("Maize (Corn)", "MAIZE", "maize", "maize"),
    "ragi": ("Ragi (Finger Millet)", "RAGI-FINGER-MILLET", "ragi-finger-millet", "ragi"),
    "jowar": ("Jowar (Sorghum)", "JOWAR-SORGHUM", "jowar-sorghum", "jowar"),
    "bajra": ("Bajra (Pearl Millet)", "BAJRA-PEARL-MILLET-CUMBU", "bajra-pearl-millet-cumbu", "bajra"),
    "tur": ("Tur / Red Gram (Arhar)", "ARHAR-TUR-RED-GRAM-WHOLE", "arhar-tur-red-gram-whole", "red gram"),
    "chana": ("Chana / Bengal Gram", "BENGAL-GRAM-GRAM-WHOLE", "bengal-gram-gram-whole", "bengal gram"),
    "moong": ("Moong / Green Gram", "GREEN-GRAM-MOONG-WHOLE", "green-gram-moong-whole", "green gram"),
    "urad": ("Urad / Black Gram", "BLACK-GRAM-URD-BEANS-WHOLE", "black-gram-urd-beans-whole", "black gram"),
    "groundnut": ("Groundnut", "GROUNDNUT", "groundnut", "groundnut"),
    "soyabean": ("Soyabean", "SOYABEAN", "soyabean", "soyabean"),
    "mustard": ("Mustard", "MUSTARD", "mustard", "mustard"),
    "sunflower": ("Sunflower Seed", "SUNFLOWER", "sunflower", "sunflower"),
    "cotton": ("Cotton", "COTTON", "cotton", "cotton"),
    "sugarcane": ("Sugarcane", "SUGARCANE", "sugarcane", "sugarcane"),
    "coffee": ("Coffee", "COFFEE", "coffee", "coffee"),
    "arecanut": ("Arecanut (Supari)", "ARECANUT", "arecanut-betelnut-supari", "arecanut"),
    "black_pepper": ("Black Pepper", "BLACK-PEPPER", "black-pepper", "black pepper"),
    "turmeric": ("Turmeric", "TURMERIC", "turmeric", "turmeric"),
    "cardamom": ("Cardamom", "CARDAMOMS", "cardamoms", "cardamom"),
    "coconut": ("Coconut", "COCONUT", "coconut", "coconut"),
    "copra": ("Copra (Dry Coconut)", "COPRA", "copra", "copra"),
    "banana": ("Banana", "BANANA", "banana", "banana"),
    "mango": ("Mango", "MANGO", "mango", "mango"),
    "pomegranate": ("Pomegranate", "POMEGRANATE", "pomegranate", "pomegranate"),
    "grapes": ("Grapes", "GRAPES", "grapes", "grapes"),
    "apple": ("Apple", "APPLE", "apple", "apple"),
    "lemon": ("Lemon", "LEMON", "lemon", "lemon"),
    "garlic": ("Garlic", "GARLIC", "garlic", "garlic"),
    "ginger": ("Ginger", "GINGER-GREEN", "ginger-green", "ginger"),
    "brinjal": ("Brinjal (Eggplant)", "BRINJAL", "brinjal", "brinjal"),
    "cabbage": ("Cabbage", "CABBAGE", "cabbage", "cabbage"),
    "cauliflower": ("Cauliflower", "CAULIFLOWER", "cauliflower", "cauliflower"),
    "okra": ("Ladies Finger (Bhindi)", "BHINDI-LADIES-FINGER", "bhindi-ladies-finger", "bhindi"),
    "beans": ("French Beans", "BEANS", "beans", "beans"),
    "carrot": ("Carrot", "CARROT", "carrot", "carrot"),
    "coriander": ("Coriander Leaves", "CORIANDER-LEAVES", "coriander-leaves", "coriander"),
}

# Farmer everyday & regional Indic crop aliases -> canonical key in COMMODITY_CATALOG
CROP_ALIASES: Dict[str, str] = {
    "tomato": "tomato", "tomatoes": "tomato", "tamatar": "tomato",
    "ಟೊಮೆಟೊ": "tomato", "ಟೊಮೇಟೊ": "tomato", "टमाटर": "tomato", "தக்காளி": "tomato", "టమాటా": "tomato", "టమోటా": "tomato", "टोमॅटो": "tomato",
    "onion": "onion", "onions": "onion", "pyaz": "onion", "kanda": "onion",
    "ಈರುಳ್ಳಿ": "onion", "प्याज": "onion", "कांदा": "onion", "வெங்காயம்": "onion", "ఉల్లి": "onion", "ఉల్లిపాయ": "onion",
    "potato": "potato", "potatoes": "potato", "aloo": "potato",
    "ಆಲೂಗಡ್ಡೆ": "potato", "आलू": "potato", "बटाटा": "potato", "உருளைக்கிழங்கு": "potato", "బంగాళాదుంప": "potato",
    "chilli": "green_chilli", "chili": "green_chilli", "chillies": "green_chilli", "green chilli": "green_chilli", "mirchi": "green_chilli",
    "ಮೆಣಸಿನಕಾಯಿ": "green_chilli", "मिर्च": "green_chilli", "हरी मिर्च": "green_chilli", "मिरची": "green_chilli", "மிளகாய்": "green_chilli", "మిర్చి": "green_chilli", "మిరప": "green_chilli",
    "dry chilli": "dry_chilli", "red chilli": "dry_chilli", "byadagi": "dry_chilli", "ಗುಂಟೂರು ಮೆಣಸಿನಕಾಯಿ": "dry_chilli",
    "rice": "paddy", "paddy": "paddy", "dhan": "paddy",
    "ಭತ್ತ": "paddy", "धान": "paddy", "भात": "paddy", "நெல்": "paddy", "వరి": "paddy",
    "wheat": "wheat", "gehu": "wheat", "ಗೋಧಿ": "wheat", "गेहूं": "wheat", "गहू": "wheat", "கோதுமை": "wheat", "గోధుమ": "wheat",
    "maize": "maize", "corn": "maize", "makka": "maize",
    "ಮೆಕ್ಕೆಜೋಳ": "maize", "ಜೋಳ": "jowar", "मक्का": "maize", "मका": "maize", "மக்காச்சோளம்": "maize", "మొక్కజొన్న": "maize",
    "ragi": "ragi", "finger millet": "ragi", "ರಾಗಿ": "ragi", "रागी": "ragi", "नाचणी": "ragi", "கேழ்வரகு": "ragi", "రాగులు": "ragi",
    "jowar": "jowar", "sorghum": "jowar", "ज्वार": "jowar", "ज्वारी": "jowar", "சோளம்": "jowar", "జొన్నలు": "jowar",
    "bajra": "bajra", "pearl millet": "bajra", "ಸಜ್ಜೆ": "bajra", "बाजरा": "bajra", "बाजरी": "bajra", "கம்பு": "bajra", "సజ్జలు": "bajra",
    "tur": "tur", "arhar": "tur", "red gram": "tur", "toor": "tur", "pigeon pea": "tur",
    "ತೊಗರಿ": "tur", "अरहर": "tur", "तूर": "tur", "துவரை": "tur", "కందులు": "tur",
    "chana": "chana", "chickpea": "chana", "bengal gram": "chana", "gram": "chana",
    "ಕಡಲೆ": "chana", "चना": "chana", "हरभरा": "chana", "கொண்டைக்கடலை": "chana", "శనగలు": "chana",
    "moong": "moong", "green gram": "moong", "ಹೆಸರುಕಾಳು": "moong", "मूंग": "moong", "मूग": "moong",
    "urad": "urad", "black gram": "urad", "ಉದ್ದು": "urad", "उड़द": "urad", "उडीद": "urad",
    "groundnut": "groundnut", "peanut": "groundnut", "ಶೇಂಗಾ": "groundnut", "ಕಡಲೆಕಾಯಿ": "groundnut", "मूंगफली": "groundnut", "भुईमूग": "groundnut", "நிலக்கடலை": "groundnut", "వేరుశనగ": "groundnut",
    "soybean": "soyabean", "soyabean": "soyabean", "ಸೋಯಾಬೀನ್": "soyabean", "सोयाबीन": "soyabean",
    "mustard": "mustard", "ಸಾಸಿವೆ": "mustard", "सरसों": "mustard",
    "sunflower": "sunflower", "ಸೂರ್ಯಕಾಂತಿ": "sunflower", "सूरजमुखी": "sunflower",
    "cotton": "cotton", "kapas": "cotton", "ಹತ್ತಿ": "cotton", "कपास": "cotton", "कापूस": "cotton", "பருத்தி": "cotton", "పత్తి": "cotton",
    "sugarcane": "sugarcane", "ಕಬ್ಬು": "sugarcane", "गन्ना": "sugarcane", "ऊस": "sugarcane", "கரும்பு": "sugarcane", "చెరకు": "sugarcane",
    "coffee": "coffee", "ಕಾಫಿ": "coffee", "कॉफ़ी": "coffee", "कॉफी": "coffee", "காபி": "coffee", "కాఫీ": "coffee",
    "arecanut": "arecanut", "areca": "arecanut", "supari": "arecanut", "betelnut": "arecanut",
    "ಅಡಿಕೆ": "arecanut", "सुपारी": "arecanut", "பாக்கு": "arecanut", "పోక": "arecanut",
    "pepper": "black_pepper", "black pepper": "black_pepper", "ಕರಿಮೆಣಸು": "black_pepper", "काली मिर्च": "black_pepper", "काळी मिरी": "black_pepper", "மிளகு": "black_pepper", "మిరియాలు": "black_pepper",
    "turmeric": "turmeric", "haldi": "turmeric", "ಅರಿಶಿನ": "turmeric", "हल्दी": "turmeric", "हळद": "turmeric", "மஞ்சள்": "turmeric", "పసుపు": "turmeric",
    "cardamom": "cardamom", "ಏಲಕ್ಕಿ": "cardamom", "इलायची": "cardamom", "ஏலக்காய்": "cardamom", "యాలకులు": "cardamom",
    "coconut": "coconut", "ತೆಂಗಿನಕಾಯಿ": "coconut", "नारियल": "coconut", "नारळ": "coconut", "தேங்காய்": "coconut", "కొబ్బరి": "coconut",
    "copra": "copra", "ಕೊಬ್ಬರಿ": "copra", "खोबरे": "copra",
    "banana": "banana", "ಬಾಳೆ": "banana", "ಬಾಳೆಹಣ್ಣು": "banana", "केला": "banana", "केळी": "banana", "வாழை": "banana", "అరటి": "banana",
    "mango": "mango", "ಮಾವು": "mango", "आम": "mango", "आंबा": "mango", "மாம்பழம்": "mango", "మామిడి": "mango",
    "pomegranate": "pomegranate", "ದಾಳಿಂಬೆ": "pomegranate", "अनार": "pomegranate", "डाळिंब": "pomegranate",
    "grape": "grapes", "grapes": "grapes", "ದ್ರಾಕ್ಷಿ": "grapes", "अंगूर": "grapes", "द्राक्षे": "grapes",
    "apple": "apple", "ಸೇಬು": "apple", "सेब": "apple",
    "lemon": "lemon", "ನಿಂಬೆ": "lemon", "नींबू": "lemon", "लिंबू": "lemon",
    "garlic": "garlic", "ಬೆಳ್ಳುಳ್ಳಿ": "garlic", "लहसुन": "garlic", "लसूण": "garlic", "பூண்டு": "garlic", "వెల్లుల్లి": "garlic",
    "ginger": "ginger", "ಶುಂಠಿ": "ginger", "अदरक": "ginger", "आले": "ginger", "இഞ്ചி": "ginger", "అల్లం": "ginger",
    "brinjal": "brinjal", "eggplant": "brinjal", "ಬದನೆಕಾಯಿ": "brinjal", "बैंगन": "brinjal", "वांगी": "brinjal", "கத்திரிக்காய்": "brinjal", "వంకాయ": "brinjal",
    "cabbage": "cabbage", "ಎಲೆಕೋಸು": "cabbage", "पत्तागोभी": "cabbage", "कोबी": "cabbage",
    "cauliflower": "cauliflower", "ಹೂಕೋಸು": "cauliflower", "फूलगोभी": "cauliflower", "फ्लॉवर": "cauliflower",
    "okra": "okra", "bhindi": "okra", "ladies finger": "okra", "ಬೆಂಡೆಕಾಯಿ": "okra", "भिंडी": "okra", "भेंडी": "okra", "வெண்டைக்காய்": "okra", "బెండకాయ": "okra",
    "beans": "beans", "ಹುರಳಿಕಾಯಿ": "beans",
    "carrot": "carrot", "ಕ್ಯಾರೆಟ್": "carrot", "गाजर": "carrot",
    "coriander": "coriander", "ಕೊತ್ತಂಬರಿ": "coriander", "धनिया": "coriander", "कोथिंबीर": "coriander",
}

INDIAN_STATES = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh", "goa", "gujarat",
    "haryana", "himachal pradesh", "jharkhand", "karnataka", "kerala", "madhya pradesh",
    "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
    "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura", "uttar pradesh",
    "uttarakhand", "west bengal", "delhi", "jammu and kashmir", "puducherry", "chandigarh",
}

STATE_ALIASES = {
    "orissa": "Odisha",
    "pondicherry": "Puducherry",
    "nct of delhi": "Delhi",
    "new delhi": "Delhi",
    "uttaranchal": "Uttarakhand",
}


# ─────────────────────────────────────────────────────────────
# SQLite Real Cache (Zero Hardcoding)
# ─────────────────────────────────────────────────────────────
def _init_db() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(CACHE_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mandi_arrivals (
            commodity_key TEXT NOT NULL,
            commodity_label TEXT NOT NULL,
            state TEXT NOT NULL,
            district TEXT NOT NULL,
            mandi TEXT NOT NULL,
            variety TEXT NOT NULL,
            min_price REAL NOT NULL,
            modal_price REAL NOT NULL,
            max_price REAL NOT NULL,
            arrival_date TEXT NOT NULL,
            source_name TEXT NOT NULL,
            fetched_at INTEGER NOT NULL,
            PRIMARY KEY (commodity_key, state, mandi, variety, arrival_date)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mandi_trend_meta (
            commodity_key TEXT NOT NULL,
            state_scope TEXT NOT NULL,
            trend_code TEXT NOT NULL,
            trend_pct REAL,
            msp_price REAL,
            national_avg_price REAL,
            fetched_at INTEGER NOT NULL,
            PRIMARY KEY (commodity_key, state_scope)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS market_geocache (
            place_key TEXT PRIMARY KEY,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            updated_at INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def _save_arrivals_to_cache(
    commodity_key: str,
    commodity_label: str,
    records: List[Dict[str, Any]],
    state_scope: str,
    trend_code: str,
    trend_pct: Optional[float],
    msp_price: Optional[float],
    national_avg: Optional[float],
) -> None:
    if not records:
        return
    now_ts = int(time.time())
    conn = _init_db()
    try:
        for r in records:
            conn.execute(
                """
                INSERT OR REPLACE INTO mandi_arrivals
                (commodity_key, commodity_label, state, district, mandi, variety,
                 min_price, modal_price, max_price, arrival_date, source_name, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    commodity_key,
                    commodity_label,
                    r.get("state") or "",
                    r.get("district") or "",
                    r.get("mandi") or "",
                    r.get("variety") or "Standard",
                    float(r["min_price"]),
                    float(r["modal_price"]),
                    float(r["max_price"]),
                    r.get("arrival_date") or datetime.now().strftime("%d/%m/%Y"),
                    r.get("source_name") or "Agmarknet APMC Feed",
                    now_ts,
                ),
            )
        conn.execute(
            """
            INSERT OR REPLACE INTO mandi_trend_meta
            (commodity_key, state_scope, trend_code, trend_pct, msp_price, national_avg_price, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (commodity_key, state_scope or "ALL", trend_code, trend_pct, msp_price, national_avg, now_ts),
        )
        conn.commit()
    finally:
        conn.close()


def _load_cached_arrivals(
    commodity_key: str, state_filter: Optional[str]
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    cutoff = int(time.time()) - MAX_CACHE_AGE_SECONDS
    conn = _init_db()
    try:
        rows = []
        if state_filter:
            rows = conn.execute(
                """
                SELECT * FROM mandi_arrivals
                WHERE commodity_key = ? AND LOWER(state) = LOWER(?) AND fetched_at >= ?
                ORDER BY fetched_at DESC
                """,
                (commodity_key, state_filter, cutoff),
            ).fetchall()
        if not rows:
            rows = conn.execute(
                """
                SELECT * FROM mandi_arrivals
                WHERE commodity_key = ? AND fetched_at >= ?
                ORDER BY fetched_at DESC
                """,
                (commodity_key, cutoff),
            ).fetchall()

        meta_row = conn.execute(
            """
            SELECT * FROM mandi_trend_meta
            WHERE commodity_key = ? AND state_scope IN (?, 'ALL') AND fetched_at >= ?
            ORDER BY CASE WHEN state_scope = ? THEN 0 ELSE 1 END, fetched_at DESC
            LIMIT 1
            """,
            (commodity_key, state_filter or "ALL", cutoff, state_filter or "ALL"),
        ).fetchone()
        return [dict(r) for r in rows], (dict(meta_row) if meta_row else None)
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# Crop & Distance Helpers
# ─────────────────────────────────────────────────────────────
def resolve_commodity(query: str) -> Optional[Tuple[str, str, str, str, str]]:
    """
    Resolve user crop text (English or Indic script) to:
      (commodity_key, display_name_en, kisandeals_slug, commodityonline_slug, agmarknet_match)
    Never defaults to 'tomato' when empty or unrecognized!
    """
    if not query or not str(query).strip():
        return None
    q = str(query).strip().lower()
    q_clean = re.sub(r"[().,!?/\\\-_]+", " ", q).strip()
    q_clean = re.sub(r"\s+", " ", q_clean)

    # 1. Exact alias match
    if q_clean in CROP_ALIASES:
        k = CROP_ALIASES[q_clean]
        disp, kd_s, co_s, agm_s = COMMODITY_CATALOG[k]
        return k, disp, kd_s, co_s, agm_s
    if q in CROP_ALIASES:
        k = CROP_ALIASES[q]
        disp, kd_s, co_s, agm_s = COMMODITY_CATALOG[k]
        return k, disp, kd_s, co_s, agm_s

    # 2. Catalog key match
    if q_clean in COMMODITY_CATALOG:
        disp, kd_s, co_s, agm_s = COMMODITY_CATALOG[q_clean]
        return q_clean, disp, kd_s, co_s, agm_s

    # 3. Substring word match on known crop names/aliases (longest first so 'green chilli' beats 'chilli')
    for alias in sorted(CROP_ALIASES.keys(), key=len, reverse=True):
        if len(alias) >= 3 and alias in q_clean:
            k = CROP_ALIASES[alias]
            disp, kd_s, co_s, agm_s = COMMODITY_CATALOG[k]
            return k, disp, kd_s, co_s, agm_s

    return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _lookup_market_coords(district: str, state: str, allow_network: bool = True) -> Optional[Tuple[float, float]]:
    place_key = f"{(district or '').strip().lower()}|{(state or '').strip().lower()}"
    if not district and not state:
        return None
    conn = _init_db()
    try:
        row = conn.execute("SELECT lat, lon FROM market_geocache WHERE place_key = ?", (place_key,)).fetchone()
        if row:
            return float(row["lat"]), float(row["lon"])
    finally:
        conn.close()

    if not allow_network:
        return None
    q = f"{district}, {state}".strip(", ")
    geo, err_code, _ = geocode_location(location_query=q)
    if not err_code and geo and geo.get("latitude") is not None and geo.get("longitude") is not None:
        lat_f, lon_f = float(geo["latitude"]), float(geo["longitude"])
        conn = _init_db()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO market_geocache (place_key, lat, lon, updated_at) VALUES (?, ?, ?, ?)",
                (place_key, lat_f, lon_f, int(time.time())),
            )
            conn.commit()
        finally:
            conn.close()
        return lat_f, lon_f
    return None


# ─────────────────────────────────────────────────────────────
# Live Multi-Source APMC Fetchers (Zero Captcha)
# ─────────────────────────────────────────────────────────────
def _parse_rupee_number(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(text).replace(",", ""))
    if not cleaned:
        return None
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None


def _fetch_datagov_ogd_api(commodity_label: str, state: Optional[str]) -> List[Dict[str, Any]]:
    """Query official data.gov.in OGD API if DATA_GOV_API_KEY is configured in .env."""
    api_key = os.getenv("DATA_GOV_API_KEY", "").strip()
    if not api_key:
        return []
    params: Dict[str, Any] = {
        "api-key": api_key,
        "format": "json",
        "limit": 40,
        "filters[commodity]": commodity_label.split("(")[0].strip(),
    }
    if state:
        params["filters[state]"] = state
    try:
        r = requests.get(
            "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070",
            params=params,
            timeout=(2.5, 6.0),
        )
        if r.status_code != 200:
            return []
        body = r.json()
        out = []
        for rec in body.get("records") or []:
            modal = _parse_rupee_number(rec.get("modal_price"))
            min_p = _parse_rupee_number(rec.get("min_price")) or modal
            max_p = _parse_rupee_number(rec.get("max_price")) or modal
            if not modal:
                continue
            out.append(
                {
                    "mandi": f"{rec.get('market', '').strip()} APMC".replace("APMC APMC", "APMC").strip(),
                    "district": (rec.get("district") or "").strip(),
                    "state": (rec.get("state") or state or "").strip(),
                    "variety": (rec.get("variety") or "Standard").strip(),
                    "min_price": round(min_p),
                    "modal_price": round(modal),
                    "max_price": round(max_p),
                    "arrival_date": (rec.get("arrival_date") or "").strip(),
                    "source_name": "Agmarknet (data.gov.in Live API)",
                }
            )
        return out
    except Exception:
        return []


def _fetch_kisandeals_apmc_live(
    kd_slug: str, state: Optional[str]
) -> Tuple[List[Dict[str, Any]], List[Tuple[str, float]]]:
    """
    Fetch real daily APMC yard arrivals & multi-day price history from KisanDeals Agmarknet mirror.
    Returns (market_records, daily_avg_series).
    """
    state_slug = re.sub(r"[^A-Z0-9]+", "-", state.upper()).strip("-") if state else "ALL"
    url = f"https://www.kisandeals.com/mandiprices/{kd_slug}/{state_slug}/ALL"
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=(3.0, 8.0))
        if resp.status_code != 200:
            return [], []
        html = resp.text
    except Exception:
        return [], []

    tables = re.findall(r"<table[^>]*>([\s\S]*?)</table>", html)
    daily_series: List[Tuple[str, float]] = []
    records: List[Dict[str, Any]] = []

    for tb in tables:
        rows = re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", tb)
        if len(rows) < 2:
            continue
        headers = [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip().lower()
            for c in re.findall(r"<t[dh][^>]*>([\s\S]*?)</t[dh]>", rows[0])
        ]
        # Multi-day trend table: ['date', 'avg ₹', 'min ₹', 'max ₹', 'change']
        if len(headers) >= 4 and "date" in headers[0] and "avg" in headers[1]:
            for tr in rows[1:8]:
                cells = [
                    re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                    for c in re.findall(r"<td[^>]*>([\s\S]*?)</td>", tr)
                ]
                if len(cells) >= 2:
                    avg_v = _parse_rupee_number(cells[1])
                    if avg_v:
                        daily_series.append((cells[0], avg_v))

        # Market-wise APMC table:
        # ['commodity', 'variety', 'market (apmc)', 'district', 'state', 'min price ₹', 'modal price ₹', 'max price ₹', 'change', 'date', ...]
        elif any("market" in h for h in headers) and any("modal" in h for h in headers):
            for tr in rows[1:]:
                cells = [
                    re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                    for c in re.findall(r"<td[^>]*>([\s\S]*?)</td>", tr)
                ]
                if len(cells) < 8:
                    continue
                variety = cells[1] if cells[1] and cells[1] != "-" else "Standard"
                mandi_name = cells[2].strip()
                district_name = cells[3].strip()
                state_name = cells[4].strip()
                min_v = _parse_rupee_number(cells[5])
                modal_v = _parse_rupee_number(cells[6])
                max_v = _parse_rupee_number(cells[7])
                arr_date = cells[9].strip() if len(cells) >= 10 and cells[9].strip() else datetime.now().strftime("%d/%m/%Y")
                if not modal_v or not mandi_name:
                    continue
                records.append(
                    {
                        "mandi": mandi_name,
                        "district": district_name,
                        "state": state_name,
                        "variety": variety,
                        "min_price": round(min_v or modal_v),
                        "modal_price": round(modal_v),
                        "max_price": round(max_v or modal_v),
                        "arrival_date": arr_date,
                        "source_name": "Agmarknet APMC Daily Arrivals",
                    }
                )
    return records, daily_series


def _fetch_commodityonline_apmc_live(co_slug: str, state: Optional[str]) -> List[Dict[str, Any]]:
    """Secondary independent live APMC market-wise source (CommodityOnline Agmarknet feed)."""
    if not state:
        return []
    state_slug = re.sub(r"[^a-z0-9]+", "-", state.lower()).strip("-")
    url = f"https://www.commodityonline.com/mandiprices/{co_slug}/{state_slug}"
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=(3.0, 8.0))
        if resp.status_code != 200:
            return []
        html = resp.text
    except Exception:
        return []

    tables = re.findall(r"<table[^>]*>([\s\S]*?)</table>", html)
    records: List[Dict[str, Any]] = []
    for tb in tables[:2]:
        rows = re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", tb)
        if len(rows) < 2:
            continue
        headers = [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip().lower()
            for c in re.findall(r"<t[dh][^>]*>([\s\S]*?)</t[dh]>", rows[0])
        ]
        # Format: ['market', 'variety', 'price', 'date'] where price is '₹30/Kg (₹25-₹35)'
        if len(headers) >= 4 and headers[0] == "market" and "price" in headers[2]:
            for tr in rows[1:]:
                cells = [
                    re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                    for c in re.findall(r"<td[^>]*>([\s\S]*?)</td>", tr)
                ]
                if len(cells) < 4:
                    continue
                mkt = cells[0].strip()
                var = cells[1].strip() or "Standard"
                price_cell = cells[2]
                dt_str = cells[3].strip()
                m_kg = re.search(r"₹\s*([\d.]+)\s*/\s*Kg(?:\s*\(\s*₹\s*([\d.]+)\s*-\s*₹\s*([\d.]+)\s*\))?", price_cell, re.I)
                if not m_kg:
                    continue
                modal_qtl = float(m_kg.group(1)) * 100.0
                min_qtl = float(m_kg.group(2)) * 100.0 if m_kg.group(2) else modal_qtl
                max_qtl = float(m_kg.group(3)) * 100.0 if m_kg.group(3) else modal_qtl
                records.append(
                    {
                        "mandi": f"{mkt} APMC" if "apmc" not in mkt.lower() and "market" not in mkt.lower() else mkt,
                        "district": mkt.split("(")[0].strip(),
                        "state": state.title(),
                        "variety": var,
                        "min_price": round(min_qtl),
                        "modal_price": round(modal_qtl),
                        "max_price": round(max_qtl),
                        "arrival_date": dt_str,
                        "source_name": "Agmarknet State APMC Feed",
                    }
                )
    return records


def _fetch_agmarknet_official_summary(agm_match: str) -> Optional[Dict[str, Any]]:
    """
    Query official Ministry of Agriculture Agmarknet 2.0 open national daily summary endpoint:
    https://api.agmarknet.gov.in/v1/dashboard-default-data/
    Provides official 2026-27 MSP (`msp_price`), national weighted average price, and 3-day movement!
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        r = requests.get(
            "https://api.agmarknet.gov.in/v1/dashboard-default-data/",
            params={"dashboard": "marketwise_price_arrival", "date": today_str},
            headers=AGMARKNET_HEADERS,
            timeout=(2.5, 6.0),
        )
        if r.status_code != 200:
            return None
        records = r.json().get("data", {}).get("records") or []
        target = agm_match.lower()
        for rec in records:
            cname = (rec.get("cmdt_name") or "").lower()
            if target in cname or cname.split("(")[0].strip() == target:
                as_on = _parse_rupee_number(rec.get("as_on_price"))
                prev1 = _parse_rupee_number(rec.get("one_day_ago_price"))
                prev2 = _parse_rupee_number(rec.get("two_day_ago_price"))
                msp = _parse_rupee_number(rec.get("msp_price"))
                return {
                    "national_avg_price": round(as_on) if as_on else None,
                    "one_day_ago_price": round(prev1) if prev1 else None,
                    "two_day_ago_price": round(prev2) if prev2 else None,
                    "msp_price": round(msp) if msp else None,
                    "reported_date": rec.get("reported_date") or today_str,
                    "agm_trend": rec.get("trend"),
                }
    except Exception:
        return None
    return None


# ─────────────────────────────────────────────────────────────
# Plain-Language Farmer Selling Guidance (All 6 Languages)
# ─────────────────────────────────────────────────────────────
def _compute_trend(
    daily_series: List[Tuple[str, float]], agm_info: Optional[Dict[str, Any]]
) -> Tuple[str, Optional[float]]:
    """
    Compute real price direction ('UP', 'DOWN', or 'STEADY') and % change
    from multi-day market arrival history. Never uses fake hardcoded strings.
    """
    if len(daily_series) >= 2:
        latest = daily_series[0][1]
        ref_idx = min(3, len(daily_series) - 1)
        older = daily_series[ref_idx][1]
        if older > 0:
            pct = round(((latest - older) / older) * 100.0, 1)
            if pct >= 2.5:
                return "UP", pct
            if pct <= -2.5:
                return "DOWN", pct
            return "STEADY", pct

    if agm_info and agm_info.get("national_avg_price"):
        cur = agm_info["national_avg_price"]
        ref = agm_info.get("two_day_ago_price") or agm_info.get("one_day_ago_price")
        if ref and ref > 0:
            pct = round(((cur - ref) / ref) * 100.0, 1)
            if pct >= 2.5:
                return "UP", pct
            if pct <= -2.5:
                return "DOWN", pct
            return "STEADY", pct

    return "STEADY", None


def _format_plain_trend(trend_code: str, trend_pct: Optional[float], lang: str = "en") -> str:
    pct_str = f" ({'+' if (trend_pct or 0) > 0 else ''}{trend_pct}%)" if trend_pct is not None else ""
    labels = {
        "en": {"UP": f"Prices Going Up{pct_str}", "DOWN": f"Prices Going Down{pct_str}", "STEADY": f"Prices Steady{pct_str}"},
        "kn": {"UP": f"ದರ ಏರಿಕೆಯಾಗುತ್ತಿದೆ{pct_str}", "DOWN": f"ದರ ಇಳಿಕೆಯಾಗುತ್ತಿದೆ{pct_str}", "STEADY": f"ದರ ಸ್ಥಿರವಾಗಿದೆ{pct_str}"},
        "hi": {"UP": f"भाव बढ़ रहा है{pct_str}", "DOWN": f"भाव कम हो रहा है{pct_str}", "STEADY": f"भाव स्थिर है{pct_str}"},
        "ta": {"UP": f"விலை உயர்கிறது{pct_str}", "DOWN": f"விலை குறைகிறது{pct_str}", "STEADY": f"விலை நிலையானது{pct_str}"},
        "te": {"UP": f"ధర పెరుగుతోంది{pct_str}", "DOWN": f"ధర తగ్గుతోంది{pct_str}", "STEADY": f"ధర స్థిరంగా ఉంది{pct_str}"},
        "mr": {"UP": f"भाव वाढत आहे{pct_str}", "DOWN": f"भाव कमी होत आहे{pct_str}", "STEADY": f"भाव स्थिर आहे{pct_str}"},
    }
    tmap = labels.get(lang, labels["en"])
    return tmap.get(trend_code, tmap["STEADY"])


def _build_plain_selling_advice(
    crop_en: str,
    primary: Dict[str, Any],
    all_mandis: List[Dict[str, Any]],
    trend_code: str,
    msp_price: Optional[float],
    lang: str = "en",
) -> str:
    modal = int(round(primary["modal_price"]))
    per_kg = round(modal / 100.0, 1)
    m_name = primary["mandi"]

    # Check if another nearby mandi pays noticeably higher (>= ₹150/qtl and >= 5% higher)
    better_mandi = None
    extra_per_qtl = 0
    for cand in all_mandis[1:6]:
        if isinstance(cand.get("distance_km"), (int, float)) and cand["distance_km"] > 180:
            continue
        diff = int(round(cand["modal_price"] - primary["modal_price"]))
        if diff >= max(150, int(0.05 * modal)):
            if better_mandi is None or diff > extra_per_qtl:
                better_mandi = cand
                extra_per_qtl = diff

    msp_note_en = ""
    if msp_price:
        if modal >= msp_price:
            msp_note_en = f" Current market rate is ₹{int(modal - msp_price)}/quintal above the Government Support Price (₹{int(msp_price)})."
        else:
            msp_note_en = (
                f" Note: Open market rate (₹{modal}) is below the Government Support Price (₹{int(msp_price)}/quintal) — "
                f"check your nearest government procurement centre if registered."
            )

    if lang == "kn":
        if trend_code == "UP":
            base = "ದರ ಏರುತ್ತಿದೆ — ಇಂದು ಅರ್ಧ ಬೆಳೆ ಮಾರಿ, ಉಳಿದ ಅರ್ಧವನ್ನು 3 ರಿಂದ 4 ದಿನ ಕಾದು ಮಾರಾಟ ಮಾಡಬಹುದು."
        elif trend_code == "DOWN":
            base = "ದರ ಇಳಿಕೆಯಾಗುತ್ತಿದೆ — ಕಟಾವಾದ ಬೆಳೆಯನ್ನು ತಡಮಾಡದೆ ಮಾರಾಟ ಮಾಡುವುದು ಒಳ್ಳೆಯದು."
        else:
            base = "ಮಾರುಕಟ್ಟೆ ದರ ಸ್ಥಿರವಾಗಿದೆ — ಬೆಳೆ ಸಿದ್ಧವಾದಂತೆ ಸಾಮಾನ್ಯವಾಗಿ ಮಾರಾಟ ಮಾಡಿ."
        if better_mandi:
            base += f" ಹತ್ತಿರದ {better_mandi['mandi']} ಮಾರುಕಟ್ಟೆಯಲ್ಲಿ ಕ್ವಿಂಟಾಲ್‌ಗೆ ₹{extra_per_qtl} ಹೆಚ್ಚು ದರ ಸಿಗುತ್ತಿದೆ — ಸಾಗಾಟ ವೆಚ್ಚ ಕಡಿಮೆಯಿದ್ದರೆ ಅಲ್ಲಿಗೆ ಕಳುಹಿಸಬಹುದು."
        if msp_price:
            if modal >= msp_price:
                base += f" (ಸರ್ಕಾರಿ ಬೆಂಬಲ ಬೆಲೆ ₹{int(msp_price)} ಕಿಂತ ಉತ್ತಮ ದರ ಇದೆ.)"
            else:
                base += f" (ಗಮನಿಸಿ: ಸರ್ಕಾರಿ ಬೆಂಬಲ ಬೆಲೆ ₹{int(msp_price)}/ಕ್ವಿಂಟಾಲ್ ಇದೆ — ಸರ್ಕಾರಿ ಖರೀದಿ ಕೇಂದ್ರವನ್ನೂ ವಿಚಾರಿಸಿ.)"
        return base

    if lang == "hi":
        if trend_code == "UP":
            base = "भाव बढ़ रहा है — आधी फसल अभी बेचें और बाकी 3 से 4 दिन रुककर बेच सकते हैं।"
        elif trend_code == "DOWN":
            base = "भाव कम हो रहा है — तैयार फसल को रोके बिना जल्द बेच देना बेहतर रहेगा।"
        else:
            base = "बाजार भाव स्थिर है — फसल तैयार होने के हिसाब से आराम से बेचें।"
        if better_mandi:
            base += f" पास की {better_mandi['mandi']} में ₹{extra_per_qtl}/क्विंटल ज्यादा भाव मिल रहा है — भाड़ा कम पड़े तो वहां ले जा सकते हैं।"
        if msp_price:
            if modal >= msp_price:
                base += f" (यह सरकारी समर्थन मूल्य ₹{int(msp_price)} से ऊपर है।)"
            else:
                base += f" (ध्यान दें: सरकारी समर्थन मूल्य ₹{int(msp_price)}/क्विंटल है — सरकारी खरीद केंद्र पर भी पता करें।)"
        return base

    if lang == "ta":
        if trend_code == "UP":
            base = f"விலை உயர்கிறது ({m_name}: ₹{modal}/குவிண்டால், அதாவது ₹{per_kg}/கிலோ). பாதி மகசூலை இன்று விற்று, மீதியை 3 முதல் 4 நாள் கழித்து விற்கலாம்."
        elif trend_code == "DOWN":
            base = f"விலை குறைகிறது ({m_name}: ₹{modal}/குவிண்டால், அதாவது ₹{per_kg}/கிலோ). அறுவடை செய்த பயிரை தாமதிக்காமல் விற்பது நல்லது."
        else:
            base = f"சந்தை விலை சீராக உள்ளது ({m_name}: ₹{modal}/குவிண்டால், அதாவது ₹{per_kg}/கிலோ). அறுவடைக்கு ஏற்ப வழக்கம் போல் விற்கவும்."
        if better_mandi:
            base += f" அருகிலுள்ள {better_mandi['mandi']} சந்தையில் குவிண்டாலுக்கு ₹{extra_per_qtl} கூடுதல் விலை கிடைக்கிறது."
        return base

    if lang == "te":
        if trend_code == "UP":
            base = f"ధర పెరుగుతోంది ({m_name}: ₹{modal}/క్వింటాల్, అంటే ₹{per_kg}/కిలో). సగం పంటను ఈరోజు అమ్మి, మిగతా సగాన్ని 3 నుండి 4 రోజులు ఆగి అమ్మవచ్చు."
        elif trend_code == "DOWN":
            base = f"ధర తగ్గుతోంది ({m_name}: ₹{modal}/క్వింటాల్, అంటే ₹{per_kg}/కిలో). కోసిన పంటను ఆలస్యం చేయకుండా వెంటనే అమ్మడం మంచిది."
        else:
            base = f"మార్కెట్ ధర స్థిరంగా ఉంది ({m_name}: ₹{modal}/క్विంటాల్, అంటే ₹{per_kg}/కిలో). పంట కోత ప్రకారం సాధారణంగా అమ్మండి."
        if better_mandi:
            base += f" సమీపంలోని {better_mandi['mandi']} మార్కెట్లో క్వింటాల్‌కు ₹{extra_per_qtl} ఎక్కువ ధర లభిస్తోంది."
        return base

    if lang == "mr":
        if trend_code == "UP":
            base = f"भाव वाढत आहे ({m_name}: ₹{modal}/क्विंटल म्हणजे ₹{per_kg}/किलो). अर्धा माल आज विका आणि उरलेला माल 3 ते 4 दिवसांनी विकू शकता."
        elif trend_code == "DOWN":
            base = f"भाव कमी होत आहे ({m_name}: ₹{modal}/क्विंटल म्हणजे ₹{per_kg}/किलो). काढलेला माल न थांबवता लवकर विकणे फायदेशीर ठरेल."
        else:
            base = f"बाजारभाव स्थिर आहे ({m_name}: ₹{modal}/क्विंटल म्हणजे ₹{per_kg}/किलो). काढणीनुसार नेहमीप्रमाणे विक्री करा."
        if better_mandi:
            base += f" जवळच्या {better_mandi['mandi']} बाजारात क्विंटलमागे ₹{extra_per_qtl} जास्त भाव मिळत आहे."
        return base

    # Plain everyday English
    if trend_code == "UP":
        base = "Prices are going up — if your crop can be stored safely, sell half today and hold the rest for 3 to 4 days."
    elif trend_code == "DOWN":
        base = "Prices are going down as more arrivals reach the market — sell harvested stock soon without holding."
    else:
        base = "Market prices are steady — sell normally as your crop becomes ready for harvest."
    if better_mandi:
        dist_note = f" ({better_mandi['distance_km']} km away)" if better_mandi.get("distance_km") is not None else ""
        base += (
            f" Nearby {better_mandi['mandi']}{dist_note} is paying ₹{extra_per_qtl} more per quintal — "
            f"worth sending there if transport cost is smaller than the extra price."
        )
    return base + msp_note_en


# ─────────────────────────────────────────────────────────────
# Main Public Entry Point
# ─────────────────────────────────────────────────────────────
def fetch_mandi_prices(
    commodity_query: str = "",
    location_hint: str = "",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    language: str = "en",
    allow_online: bool = True,
) -> Dict[str, Any]:
    """
    Fetch real, location-aware APMC wholesale market prices across India.
    Zero hardcoded price dictionaries and never silently defaults to 'Tomato' or 'Kolar'.
    """
    lang = (language or "en").lower()
    if lang not in ("en", "kn", "hi", "ta", "te", "mr"):
        lang = "en"

    if not commodity_query or not str(commodity_query).strip():
        return {
            "status": "missing_commodity",
            "is_live_data": False,
            "message": "Please enter or choose a crop (for example: Tomato, Onion, Paddy, Chilli, Coffee, Cotton) to check APMC market prices.",
        }

    resolved = resolve_commodity(commodity_query)
    if resolved is None:
        return {
            "status": "commodity_not_found",
            "is_live_data": False,
            "requested_commodity": str(commodity_query).strip(),
            "message": f"Could not recognize crop '{str(commodity_query).strip()}'. Please enter a crop name like Tomato, Onion, Paddy, Maize, Chilli, Coffee, Arecanut, or Cotton.",
        }

    comm_key, comm_label_en, kd_slug, co_slug, agm_match = resolved

    # 1. Resolve optional farmer location (Village / Taluk / District / PIN / State / GPS)
    farmer_lat: Optional[float] = None
    farmer_lon: Optional[float] = None
    farmer_district: Optional[str] = None
    farmer_state: Optional[str] = None
    display_location: str = "All India"

    loc_clean = (location_hint or "").strip()
    if lat is not None and lon is not None:
        farmer_lat, farmer_lon = float(lat), float(lon)
        geo, err_code, _ = geocode_location(lat=farmer_lat, lon=farmer_lon) if allow_online else (None, "offline", None)
        if not err_code and geo:
            farmer_district = geo.get("district") or geo.get("name")
            farmer_state = geo.get("state")
            parts = [geo.get("name") or ""]
            if farmer_state and farmer_state.lower() not in parts[0].lower():
                parts.append(farmer_state)
            display_location = ", ".join(p for p in parts if p) or f"{farmer_lat:.3f}, {farmer_lon:.3f}"
        else:
            display_location = f"{farmer_lat:.3f}, {farmer_lon:.3f}"
    elif loc_clean:
        low_loc = STATE_ALIASES.get(loc_clean.lower(), loc_clean).lower()
        if low_loc in INDIAN_STATES:
            farmer_state = low_loc.title()
            display_location = farmer_state
        else:
            geo, err_code, err_msg = geocode_location(location_query=loc_clean)
            if not err_code and geo:
                farmer_lat = float(geo["latitude"])
                farmer_lon = float(geo["longitude"])
                farmer_district = geo.get("district") or geo.get("name")
                farmer_state = geo.get("state")
                if farmer_state:
                    farmer_state = STATE_ALIASES.get(farmer_state.lower(), farmer_state)
                parts = [geo.get("name") or loc_clean]
                if farmer_state and farmer_state.lower() not in parts[0].lower():
                    parts.append(farmer_state)
                display_location = ", ".join(p for p in parts if p)
            elif err_code == "location_not_found":
                return {
                    "status": "location_not_found",
                    "is_live_data": False,
                    "requested_location": loc_clean,
                    "commodity": comm_label_en,
                    "message": err_msg or f"Could not find location '{loc_clean}' in India. Please check the spelling or enter your district or PIN code.",
                }
            else:
                display_location = loc_clean

    # 2. Fetch Live APMC Data when online
    live_records: List[Dict[str, Any]] = []
    daily_series: List[Tuple[str, float]] = []
    agm_info: Optional[Dict[str, Any]] = None
    scope_note = ""

    if allow_online:
        # 2a. Official OGD data.gov.in (if DATA_GOV_API_KEY set)
        live_records = _fetch_datagov_ogd_api(comm_label_en, farmer_state)

        # 2b. State-level live APMC yards + multi-day arrival series
        kd_recs, daily_series = _fetch_kisandeals_apmc_live(kd_slug, farmer_state)
        if kd_recs:
            live_records.extend(kd_recs)

        if farmer_state and len(live_records) < 3:
            co_recs = _fetch_commodityonline_apmc_live(co_slug, farmer_state)
            live_records.extend(co_recs)

        # 2c. If requested state had no recent arrivals for this crop (e.g. plantation crop in another region),
        # query All-India APMC arrivals transparently so farmer still gets real Indian mandi rates!
        if not live_records and farmer_state:
            all_recs, all_series = _fetch_kisandeals_apmc_live(kd_slug, None)
            if all_recs:
                live_records = all_recs
                if not daily_series:
                    daily_series = all_series
                scope_note = f"No recent {comm_label_en} arrivals reported in {farmer_state}; showing nearest reporting Indian APMCs."

        # 2d. Official Ministry of Agriculture Agmarknet 2.0 national summary & 2026-27 MSP
        agm_info = _fetch_agmarknet_official_summary(agm_match)

    # Deduplicate live_records by (mandi, variety) keeping newest / first
    dedup: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for rec in live_records:
        key = (rec["mandi"].strip().lower(), rec.get("variety", "Standard").strip().lower())
        if key not in dedup:
            dedup[key] = rec
    records = list(dedup.values())

    is_live = False
    msp_price: Optional[float] = agm_info.get("msp_price") if agm_info else None
    national_avg: Optional[float] = agm_info.get("national_avg_price") if agm_info else None

    if records:
        is_live = True
        trend_code, trend_pct = _compute_trend(daily_series, agm_info)
        _save_arrivals_to_cache(
            comm_key, comm_label_en, records, farmer_state or "ALL",
            trend_code, trend_pct, msp_price, national_avg,
        )
    elif agm_info and agm_info.get("national_avg_price"):
        # Commodity is in official Agmarknet 2.0 national live feed even if state table had 0 rows today
        is_live = True
        nat_p = float(agm_info["national_avg_price"])
        records = [
            {
                "mandi": "All-India Agmarknet Weighted Average",
                "district": farmer_district or "",
                "state": farmer_state or "All India",
                "variety": "FAQ / Standard",
                "min_price": round(min(nat_p, agm_info.get("one_day_ago_price") or nat_p, agm_info.get("two_day_ago_price") or nat_p)),
                "modal_price": round(nat_p),
                "max_price": round(max(nat_p, agm_info.get("one_day_ago_price") or nat_p, agm_info.get("two_day_ago_price") or nat_p)),
                "arrival_date": agm_info.get("reported_date") or datetime.now().strftime("%d-%m-%Y"),
                "source_name": "Ministry of Agriculture Agmarknet 2.0 Live",
            }
        ]
        trend_code, trend_pct = _compute_trend([], agm_info)
        _save_arrivals_to_cache(
            comm_key, comm_label_en, records, farmer_state or "ALL",
            trend_code, trend_pct, msp_price, national_avg,
        )
    else:
        # 3. Offline / Service-Unreachable -> Check Real SQLite Cache
        cached_rows, cached_meta = _load_cached_arrivals(comm_key, farmer_state)
        if not cached_rows:
            return {
                "status": "service_unavailable",
                "is_live_data": False,
                "commodity": comm_label_en,
                "requested_location": loc_clean or display_location,
                "message": (
                    f"Live APMC market data for {comm_label_en} is currently unreachable and no recent saved price "
                    f"is stored offline. Please check your internet connection and try again."
                ),
            }
        records = cached_rows
        trend_code = (cached_meta or {}).get("trend_code") or "STEADY"
        trend_pct = (cached_meta or {}).get("trend_pct")
        msp_price = (cached_meta or {}).get("msp_price")
        national_avg = (cached_meta or {}).get("national_avg_price")

    # 4. Rank APMCs by exact district match & real GPS Haversine distance (km)
    ranked: List[Dict[str, Any]] = []
    req_words = {w.lower() for w in re.findall(r"[A-Za-z]{3,}", f"{loc_clean} {farmer_district or ''}")}

    for idx, rec in enumerate(records):
        item = dict(rec)
        dist_km: Optional[int] = None
        m_text = f"{item.get('mandi', '')} {item.get('district', '')}".lower()
        exact_match = any(w in m_text for w in req_words) if req_words else False
        same_state = bool(farmer_state and item.get("state", "").lower() == farmer_state.lower())

        # Geocode up to top 8 candidate markets when farmer coordinates are known
        if farmer_lat is not None and farmer_lon is not None and idx < 8:
            m_coords = _lookup_market_coords(
                item.get("district") or item.get("mandi", ""),
                item.get("state") or farmer_state or "",
                allow_network=allow_online and idx < 5,
            )
            if m_coords:
                dist_km = max(2, int(round(_haversine_km(farmer_lat, farmer_lon, m_coords[0], m_coords[1]))))

        item["distance_km"] = dist_km
        item["price_per_kg"] = round(float(item["modal_price"]) / 100.0, 1)
        item["unit"] = "₹ / Quintal (100 kg)"
        item["_sort_key"] = (
            0 if exact_match else (1 if same_state else 2),
            dist_km if dist_km is not None else 9999,
            -float(item["modal_price"]),
        )
        ranked.append(item)

    ranked.sort(key=lambda x: x["_sort_key"])
    for r in ranked:
        r.pop("_sort_key", None)

    primary = ranked[0]
    modal_p = int(round(float(primary["modal_price"])))
    min_p = int(round(float(primary["min_price"])))
    max_p = int(round(float(primary["max_price"])))
    per_kg = round(modal_p / 100.0, 1)
    arr_date = primary.get("arrival_date") or datetime.now().strftime("%d/%m/%Y")

    plain_trend = _format_plain_trend(trend_code, trend_pct, lang)
    selling_advice = _build_plain_selling_advice(comm_label_en, primary, ranked, trend_code, msp_price, lang)
    if scope_note and lang == "en":
        selling_advice = f"{scope_note} {selling_advice}"

    source_label = (
        f"Live APMC Arrivals ({arr_date})"
        if is_live
        else f"Saved APMC Rate ({arr_date})"
    )

    return {
        "status": "success" if is_live else "cached_real",
        "is_live_data": is_live,
        "data_source_label": source_label,
        "source": primary.get("source_name") or "Agmarknet APMC",
        "last_updated": arr_date,
        "arrival_date": arr_date,
        "commodity": comm_label_en,
        "commodity_key": comm_key,
        "requested_location": display_location,
        "primary_mandi": primary["mandi"],
        "primary_district": primary.get("district") or "",
        "primary_state": primary.get("state") or "",
        "variety": primary.get("variety") or "Standard",
        "modal_price": modal_p,
        "min_price": min_p,
        "max_price": max_p,
        "unit": "₹ / 100 kg Quintal",
        "price_per_kg": per_kg,
        "trend_code": trend_code,
        "trend_change_pct": trend_pct,
        "trend": plain_trend,
        "msp_price": int(round(msp_price)) if msp_price else None,
        "national_avg_price": int(round(national_avg)) if national_avg else None,
        "all_mandis_comparison": ranked[:6],
        "selling_advisory": selling_advice,
        "summary": (
            f"{comm_label_en} usual rate at {primary['mandi']} ({primary.get('state', '')}) on {arr_date}: "
            f"₹{modal_p} per 100 kg quintal (₹{per_kg}/kg; range ₹{min_p}–₹{max_p}). "
            f"{plain_trend}. {selling_advice}"
        ),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_mandi_prices("tomato", "Kolar"), ensure_ascii=False, indent=2))
