"""
FasalSaarathi — Module 3: PMFBY Crop Insurance Shield & 72-Hour Weather-Loss Dossier
===================================================================================
Real Agro-Meteorological Triggers + Standard PMFBY Premium Caps • 6 Languages

Features:
1. PMFBY Premium & Coverage Estimator:
   - Standard PMFBY farmer share caps: Kharif (2.0%), Rabi (1.5%), Horticulture/Commercial (5.0%).
   - Plain-language coverage explanation & voice text in English, Kannada, Hindi, Tamil, Telugu, Marathi.
2. Live 72-Hour Extreme Weather Loss Trigger (`fetch_live_weather`):
   - Evaluates Open-Meteo WMO storm/hail codes (95, 96, 99), heavy rain (>= 40 mm),
     violent wind gusts (>= 55 km/h), and heatwave stress (>= 42 °C).
   - Never hardcodes weather or location; returns honest `missing_location` / `service_unavailable` when needed.
3. Policy Vault & Timestamped Claim Evidence Dossier (`data/fasalsaarathi_users.db`):
   - Stores farmer's insured crop policies and builds timestamped, GPS- & weather-stamped claim dossiers.
"""

from contextlib import closing
import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from tools.auth_tool import DEFAULT_USERS_DB, init_auth_db
from tools.weather_tool import fetch_live_weather

LANGS = ("en", "kn", "hi", "ta", "te", "mr")

# Standard PMFBY Farmer Premium Share Caps (Ministry of Agriculture & Farmers Welfare)
SEASON_RATES: Dict[str, Dict[str, Any]] = {
    "kharif": {
        "farmer_pct": 2.0,
        "cutoff": "July 31 (typical Kharif enrollment cutoff)",
        "labels": {
            "en": "Kharif (Monsoon • 2% Farmer Share)",
            "kn": "ಮುಂಗಾರು / ಖರೀಫ್ (2% ರೈತರ ಪಾಲು)",
            "hi": "खरीफ (मानसून • 2% किसान हिस्सा)",
            "ta": "காரீப் (பருவமழை • 2% விவசாயி பங்கு)",
            "te": "ఖరీఫ్ (వర్షాకాలం • 2% రైతు వాటా)",
            "mr": "खरीप (पावसाळी • 2% शेतकरी हिस्सा)",
        },
    },
    "rabi": {
        "farmer_pct": 1.5,
        "cutoff": "December 31 (typical Rabi enrollment cutoff)",
        "labels": {
            "en": "Rabi (Winter • 1.5% Farmer Share)",
            "kn": "ಹಿಂಗಾರು / ರಬಿ (1.5% ರೈತರ ಪಾಲು)",
            "hi": "रबी (सर्दी • 1.5% किसान हिस्सा)",
            "ta": "ரபி (குளிர்காலம் • 1.5% விவசாயி பங்கு)",
            "te": "రబీ (చలికాలం • 1.5% రైతు వాటా)",
            "mr": "रब्बी (हिवाळी • 1.5% शेतकरी हिस्सा)",
        },
    },
    "horticulture": {
        "farmer_pct": 5.0,
        "cutoff": "Season-specific state notification (5% cap)",
        "labels": {
            "en": "Commercial / Horticulture (5% Farmer Share)",
            "kn": "ವಾಣಿಜ್ಯ / ತೋಟಗಾರಿಕೆ (5% ರೈತರ ಪಾಲು)",
            "hi": "बागवानी / वाणिज्यिक (5% किसान हिस्सा)",
            "ta": "தோட்டக்கலை / வணிகப் பயிர் (5% பங்கு)",
            "te": "ఉద్యానవన / వాణిజ్య పంట (5% వాటా)",
            "mr": "फळबाग / नगदी पीक (5% शेतकरी हिस्सा)",
        },
    },
}

# Indicative Scale-of-Finance Sum Insured per Acre (₹) for planning estimates
CROP_SUM_INSURED_PER_ACRE: Dict[str, Dict[str, Any]] = {
    "paddy": {"sum_per_acre": 32000, "default_season": "kharif", "names": {"en": "Paddy (Rice)", "kn": "ಭತ್ತ", "hi": "धान", "ta": "நெல்", "te": "వరి", "mr": "भात"}},
    "wheat": {"sum_per_acre": 28000, "default_season": "rabi", "names": {"en": "Wheat", "kn": "ಗೋಧಿ", "hi": "गेहूं", "ta": "கோதுமை", "te": "గోధుమ", "mr": "गहू"}},
    "maize": {"sum_per_acre": 24000, "default_season": "kharif", "names": {"en": "Maize", "kn": "ಮೆಕ್ಕೆಜೋಳ", "hi": "मक्का", "ta": "மக்காச்சோளம்", "te": "మొక్కజొన్న", "mr": "मका"}},
    "ragi": {"sum_per_acre": 20000, "default_season": "kharif", "names": {"en": "Ragi (Finger Millet)", "kn": "ರಾಗಿ", "hi": "रागी", "ta": "கேழ்வரகு", "te": "రాగులు", "mr": "नाचणी"}},
    "tur": {"sum_per_acre": 26000, "default_season": "kharif", "names": {"en": "Tur / Red Gram", "kn": "ತೊಗರಿ", "hi": "अरहर / तुअर", "ta": "துவரை", "te": "కందులు", "mr": "तूर"}},
    "groundnut": {"sum_per_acre": 30000, "default_season": "kharif", "names": {"en": "Groundnut", "kn": "ಶೇಂಗಾ / ಕಡಲೆಕಾಯಿ", "hi": "मूंगफली", "ta": "நிலக்கடலை", "te": "వేరుశనగ", "mr": "भुईमूग"}},
    "cotton": {"sum_per_acre": 38000, "default_season": "horticulture", "names": {"en": "Cotton", "kn": "ಹತ್ತಿ", "hi": "कपास", "ta": "பருத்தி", "te": "పత్తి", "mr": "कापूस"}},
    "sugarcane": {"sum_per_acre": 55000, "default_season": "horticulture", "names": {"en": "Sugarcane", "kn": "ಕಬ್ಬು", "hi": "गन्ना", "ta": "கரும்பு", "te": "చెరకు", "mr": "ऊस"}},
    "tomato": {"sum_per_acre": 48000, "default_season": "horticulture", "names": {"en": "Tomato", "kn": "ಟೊಮೆಟೊ", "hi": "टमाटर", "ta": "தக்காளி", "te": "టమాటా", "mr": "टोमॅटो"}},
    "onion": {"sum_per_acre": 42000, "default_season": "horticulture", "names": {"en": "Onion", "kn": "ಈರುಳ್ಳಿ", "hi": "प्याज", "ta": "வெங்காயம்", "te": "ఉల్లి", "mr": "कांदा"}},
    "potato": {"sum_per_acre": 46000, "default_season": "horticulture", "names": {"en": "Potato", "kn": "ಆಲೂಗಡ್ಡೆ", "hi": "आलू", "ta": "உருளைக்கிழங்கு", "te": "బంగాళాదుంప", "mr": "बटाटा"}},
    "chilli": {"sum_per_acre": 45000, "default_season": "horticulture", "names": {"en": "Chilli", "kn": "ಮೆಣಸಿನಕಾಯಿ", "hi": "मिर्च", "ta": "மிளகாய்", "te": "మిర్చి", "mr": "मिरची"}},
    "coffee": {"sum_per_acre": 65000, "default_season": "horticulture", "names": {"en": "Coffee", "kn": "ಕಾಫಿ", "hi": "कॉफ़ी", "ta": "காபி", "te": "కాఫీ", "mr": "कॉफी"}},
    "arecanut": {"sum_per_acre": 80000, "default_season": "horticulture", "names": {"en": "Arecanut", "kn": "ಅಡಿಕೆ", "hi": "सुपारी", "ta": "பாக்கு", "te": "పోక", "mr": "सुपारी"}},
    "banana": {"sum_per_acre": 60000, "default_season": "horticulture", "names": {"en": "Banana", "kn": "ಬಾಳೆ", "hi": "केला", "ta": "வாழை", "te": "అరటి", "mr": "केळी"}},
}

CROP_ALIASES = {
    "rice": "paddy", "dhan": "paddy", "bhatta": "paddy",
    "red gram": "tur", "arhar": "tur",
    "corn": "maize", "green chilli": "chilli", "dry chilli": "chilli",
}

PMFBY_HELPLINE = "14447"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_insurance_db(db_path: str = DEFAULT_USERS_DB) -> None:
    """Ensure `users`, `insurance_policies`, and `insurance_claims` tables exist."""
    init_auth_db(db_path)
    with closing(_connect(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS insurance_policies (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                crop TEXT NOT NULL,
                season TEXT NOT NULL,
                acres REAL NOT NULL,
                sum_insured_inr INTEGER NOT NULL,
                farmer_premium_inr INTEGER NOT NULL,
                cutoff_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS insurance_claims (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                policy_id TEXT,
                weather_event TEXT NOT NULL,
                photo_path TEXT DEFAULT '',
                gps_lat REAL,
                gps_lon REAL,
                weather_snapshot_json TEXT NOT NULL,
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _resolve_crop_key(crop_raw: str) -> str:
    key = (crop_raw or "paddy").strip().lower()
    key = CROP_ALIASES.get(key, key)
    return key if key in CROP_SUM_INSURED_PER_ACRE else "paddy"


# ─────────────────────────────────────────────────────────────────────────────
# 1. PMFBY Premium & Coverage Quote
# ─────────────────────────────────────────────────────────────────────────────
def calculate_pmfby_quote(
    crop: str = "paddy",
    season: str = "",
    acres: float = 1.0,
    custom_sum_per_acre: Optional[float] = None,
    language: str = "en",
) -> Dict[str, Any]:
    """Compute PMFBY sum insured, farmer share premium, and subsidy estimate."""
    lang = (language or "en").strip().lower()
    if lang not in LANGS:
        lang = "en"

    try:
        acres_f = float(acres)
    except (TypeError, ValueError):
        return {"status": "error", "message": "Please enter a valid land area in acres (e.g. 1.5)."}

    if acres_f <= 0 or acres_f > 500:
        return {"status": "error", "message": "Land area must be between 0.1 and 500 acres."}

    crop_key = _resolve_crop_key(crop)
    crop_info = CROP_SUM_INSURED_PER_ACRE[crop_key]
    crop_name = crop_info["names"].get(lang) or crop_info["names"]["en"]

    season_key = (season or crop_info["default_season"]).strip().lower()
    if season_key not in SEASON_RATES:
        season_key = crop_info["default_season"]
    season_spec = SEASON_RATES[season_key]

    sum_per_acre = crop_info["sum_per_acre"]
    if custom_sum_per_acre is not None:
        try:
            custom_val = float(custom_sum_per_acre)
            if 5000 <= custom_val <= 300000:
                sum_per_acre = custom_val
        except (TypeError, ValueError):
            pass

    sum_insured = int(round(sum_per_acre * acres_f))
    farmer_pct = float(season_spec["farmer_pct"])
    farmer_premium = int(round(sum_insured * (farmer_pct / 100.0)))

    # Typical total actuarial rate benchmark ~10% (state + central govt pay the balance above farmer cap)
    est_actuarial = int(round(sum_insured * 0.10))
    govt_subsidy = max(0, est_actuarial - farmer_premium)

    summary_map = {
        "en": (
            f"For {acres_f} acres of {crop_name} ({season_key.title()}), estimated crop cover is ₹{sum_insured:,}. "
            f"Under PMFBY, you pay only {farmer_pct}% (₹{farmer_premium:,}), while government subsidy covers the rest (~₹{govt_subsidy:,})."
        ),
        "kn": (
            f"{acres_f} ಎಕರೆ {crop_name} ಬೆಳೆಗೆ ಅಂದಾಜು ವಿಮಾ ಮೊತ್ತ ₹{sum_insured:,}. "
            f"PMFBY ಯೋಜನೆಯಲ್ಲಿ ರೈತರ ಪಾಲು ಕೇವಲ {farmer_pct}% (₹{farmer_premium:,}), ಉಳಿದ ಮೊತ್ತವನ್ನು ಸರ್ಕಾರ ಭರಿಸುತ್ತದೆ."
        ),
        "hi": (
            f"{acres_f} एकड़ {crop_name} के लिए अनुमानित बीमा राशि ₹{sum_insured:,} है। "
            f"PMFBY के तहत आपको केवल {farmer_pct}% (₹{farmer_premium:,}) देना होगा, बाकी सब्सिडी सरकार देती है।"
        ),
        "ta": (
            f"{acres_f} ஏக்கர் {crop_name} பயிருக்கு மதிப்பீட்டு காப்பீட்டுத் தொகை ₹{sum_insured:,}. "
            f"PMFBY திட்டத்தில் விவசாயி பங்கு {farmer_pct}% (₹{farmer_premium:,}) மட்டுமே; மீதியை அரசு மானியமாக ஏற்கிறது."
        ),
        "te": (
            f"{acres_f} ఎకరాల {crop_name} పంటకు అంచనా బీమా మొత్తం ₹{sum_insured:,}. "
            f"PMFBY లో రైతు వాటా కేవలం {farmer_pct}% (₹{farmer_premium:,}) మాత్రమే; మిగిలినది ప్రభుత్వం చెల్లిస్తుంది."
        ),
        "mr": (
            f"{acres_f} एकर {crop_name} पिकासाठी अंदाजे विमा संरक्षण ₹{sum_insured:,} आहे. "
            f"PMFBY अंतर्गत शेतकरी हिस्सा फक्त {farmer_pct}% (₹{farmer_premium:,}) असून उर्वरित हप्ता सरकार भरते."
        ),
    }
    summary = summary_map.get(lang, summary_map["en"])

    return {
        "status": "success",
        "crop": crop_key,
        "crop_name": crop_name,
        "season": season_key,
        "season_label": season_spec["labels"].get(lang, season_spec["labels"]["en"]),
        "acres": round(acres_f, 2),
        "sum_insured_per_acre_inr": int(sum_per_acre),
        "sum_insured_inr": sum_insured,
        "farmer_premium_pct": farmer_pct,
        "farmer_premium_inr": farmer_premium,
        "govt_subsidy_estimate_inr": govt_subsidy,
        "cutoff_guidance": season_spec["cutoff"],
        "helpline": PMFBY_HELPLINE,
        "summary": summary,
        "speech_text": summary,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Policy Vault
# ─────────────────────────────────────────────────────────────────────────────
def save_insurance_policy(
    user_id: str,
    crop: str,
    season: str,
    acres: float,
    db_path: str = DEFAULT_USERS_DB,
    language: str = "en",
) -> Dict[str, Any]:
    """Save an active PMFBY crop insurance policy for a user."""
    init_insurance_db(db_path)
    uid = (user_id or "guest").strip() or "guest"
    quote = calculate_pmfby_quote(crop=crop, season=season, acres=acres, language=language)
    if quote["status"] != "success":
        return quote

    policy_id = f"pol_{uuid.uuid4().hex[:10]}"
    now = _now_iso()
    with closing(_connect(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO insurance_policies (
                id, user_id, crop, season, acres, sum_insured_inr,
                farmer_premium_inr, cutoff_date, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                policy_id,
                uid,
                quote["crop"],
                quote["season"],
                quote["acres"],
                quote["sum_insured_inr"],
                quote["farmer_premium_inr"],
                quote["cutoff_guidance"],
                "active",
                now,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM insurance_policies WHERE id = ?", (policy_id,)).fetchone()

    return {"status": "success", "policy": dict(row), "quote": quote}


def list_insurance_policies(user_id: str, db_path: str = DEFAULT_USERS_DB) -> List[Dict[str, Any]]:
    init_insurance_db(db_path)
    uid = (user_id or "guest").strip() or "guest"
    with closing(_connect(db_path)) as conn:
        rows = conn.execute(
            "SELECT * FROM insurance_policies WHERE user_id = ? ORDER BY created_at DESC",
            (uid,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_insurance_policy(user_id: str, policy_id: str, db_path: str = DEFAULT_USERS_DB) -> Dict[str, Any]:
    init_insurance_db(db_path)
    uid = (user_id or "guest").strip() or "guest"
    with closing(_connect(db_path)) as conn:
        cur = conn.execute(
            "DELETE FROM insurance_policies WHERE id = ? AND user_id = ?",
            (policy_id, uid),
        )
        conn.commit()
    if cur.rowcount == 0:
        return {"status": "not_found", "message": "Policy not found."}
    return {"status": "success"}


# ─────────────────────────────────────────────────────────────────────────────
# 3. Live 72-Hour Extreme Weather Loss Trigger
# ─────────────────────────────────────────────────────────────────────────────
def evaluate_weather_claim_alert(
    location_query: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    language: str = "en",
    weather_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Evaluate real Open-Meteo telemetry for PMFBY localized-calamity triggers
    (hail/thunderstorm, heavy rain >= 40 mm, severe wind gusts >= 55 km/h, heatwave >= 42 °C).
    """
    lang = (language or "en").strip().lower()
    if lang not in LANGS:
        lang = "en"

    loc_clean = (location_query or "").strip()
    if weather_data is None:
        if not loc_clean and (lat is None or lon is None):
            return {
                "status": "missing_location",
                "is_live_data": False,
                "message": "Please enter your village, city, PIN code, or tap GPS to check live weather-loss triggers.",
            }
        weather_data = fetch_live_weather(location_query=loc_clean or None, lat=lat, lon=lon)

    w_status = weather_data.get("status")
    if w_status not in ("success", "cached_real"):
        return {
            "status": w_status or "service_unavailable",
            "is_live_data": False,
            "message": weather_data.get("message") or "Weather telemetry unavailable.",
        }

    w_code = int(weather_data.get("weather_code") or 0)
    rain_today = float(weather_data.get("rain_today_mm") or 0.0)
    rain_tom = float(weather_data.get("rain_tomorrow_mm") or 0.0)
    wind_kmh = float(weather_data.get("wind_speed_kmh") or 0.0)
    gust_kmh = float(weather_data.get("wind_gusts_kmh") or wind_kmh)
    temp_c = float(weather_data.get("current_temperature_c") or 0.0)
    disp_loc = weather_data.get("display_location") or weather_data.get("location") or loc_clean

    triggers: List[str] = []
    alert_level = "GREEN_SAFE"
    event_code = "NORMAL_WEATHER"

    _trig_i18n = {
        "storm": {
            "en": f"Thunderstorm / hailstorm ({weather_data.get('weather_condition', 'Storm')})",
            "kn": "ಗುಡುಗು-ಸಿಡಿಲು / ಆಲಿಕಲ್ಲು ಮಳೆ",
            "hi": "आंधी-तूफ़ान / ओलावृष्टि",
            "ta": "இடி-மின்னல் / ஆலங்கட்டி மழை",
            "te": "ఉరుములు / వడగళ్ళ వాన",
            "mr": "वादळ / गारपीट",
        },
        "rain": {
            "en": f"Heavy rainfall today ({rain_today} mm)",
            "kn": f"ಇಂದು ಭಾರೀ ಮಳೆ ({rain_today} ಮಿ.ಮೀ)",
            "hi": f"आज भारी बारिश ({rain_today} मिमी)",
            "ta": f"இன்று கனமழை ({rain_today} மி.மீ)",
            "te": f"నేడు భారీ వర్షం ({rain_today} మి.మీ)",
            "mr": f"आज मुसळधार पाऊस ({rain_today} मिमी)",
        },
        "wind": {
            "en": f"Strong wind gusts ({gust_kmh} km/h)",
            "kn": f"ಬಲವಾದ ಗಾಳಿ ({gust_kmh} ಕಿ.ಮೀ/ಗಂ)",
            "hi": f"तेज़ हवा के झोंके ({gust_kmh} किमी/घं)",
            "ta": f"பலத்த காற்று ({gust_kmh} கி.மீ/மணி)",
            "te": f"బలమైన ఈదురు గాలులు ({gust_kmh} కి.మీ/గం)",
            "mr": f"जोरदार वारे ({gust_kmh} किमी/तास)",
        },
        "tom_rain": {
            "en": f"Heavy rain forecast tomorrow ({rain_tom} mm)",
            "kn": f"ನಾಳೆ ಭಾರೀ ಮಳೆ ಮುನ್ಸೂಚನೆ ({rain_tom} ಮಿ.ಮೀ)",
            "hi": f"कल भारी बारिश की संभावना ({rain_tom} मिमी)",
            "ta": f"நாளை கனமழை வாய்ப்பு ({rain_tom} மி.மீ)",
            "te": f"రేపు భారీ వర్ష సూచన ({rain_tom} మి.మీ)",
            "mr": f"उद्या मुसळधार पावसाचा अंदाज ({rain_tom} मिमी)",
        },
        "heat": {
            "en": f"Extreme heatwave ({temp_c}°C)",
            "kn": f"ತೀವ್ರ ಬಿಸಿಗಾಳಿ ({temp_c}°C)",
            "hi": f"भीषण लू / गर्मी ({temp_c}°C)",
            "ta": f"கடும் வெப்ப அலை ({temp_c}°C)",
            "te": f"తీవ్ర వడగాల్పులు ({temp_c}°C)",
            "mr": f"तीव्र उष्णतेची लाट ({temp_c}°C)",
        },
    }

    if w_code in (95, 96, 99):
        triggers.append(_trig_i18n["storm"][lang])
        alert_level = "RED_72H_CLAIM"
        event_code = "HAIL_OR_THUNDERSTORM"
    if rain_today >= 40.0 or w_code in (65, 82):
        triggers.append(_trig_i18n["rain"][lang])
        alert_level = "RED_72H_CLAIM"
        event_code = "HEAVY_RAIN_FLOODING" if event_code == "NORMAL_WEATHER" else event_code
    if gust_kmh >= 55.0 or wind_kmh >= 40.0:
        triggers.append(_trig_i18n["wind"][lang])
        if alert_level == "GREEN_SAFE":
            alert_level = "AMBER_WATCH"
            event_code = "HIGH_WIND_SQUALL"
    if rain_tom >= 40.0 and alert_level == "GREEN_SAFE":
        triggers.append(_trig_i18n["tom_rain"][lang])
        alert_level = "AMBER_WATCH"
        event_code = "FORECAST_HEAVY_RAIN"
    if temp_c >= 42.0 and alert_level == "GREEN_SAFE":
        triggers.append(_trig_i18n["heat"][lang])
        alert_level = "AMBER_WATCH"
        event_code = "HEAT_STRESS"

    if alert_level == "RED_72H_CLAIM":
        msg_map = {
            "en": f"URGENT ALERT for {disp_loc}: {', '.join(triggers)}. If your insured crop suffered flooding, hail, or lodging, report localized damage within 72 hours via Krishi Rakshak helpline {PMFBY_HELPLINE} or upload a field photo below.",
            "kn": f"{disp_loc} ನಲ್ಲಿ ತುರ್ತು ಎಚ್ಚರಿಕೆ: {', '.join(triggers)}. ಬೆಳೆ ಹಾನಿಯಾಗಿದ್ದರೆ 72 ಗಂಟೆಗಳ ಒಳಗೆ ಸಹಾಯವಾಣಿ {PMFBY_HELPLINE} ಗೆ ಕರೆ ಮಾಡಿ ಅಥವಾ ಕೆಳಗೆ ಫೋಟೋ ಸೇರಿಸಿ.",
            "hi": f"{disp_loc} के लिए आपातकालीन अलर्ट: {', '.join(triggers)}। फसल नुकसान होने पर 72 घंटे के भीतर हेल्पलाइन {PMFBY_HELPLINE} पर सूचना दें या नीचे फोटो अपलोड करें।",
            "ta": f"{disp_loc} பகுதிக்கு அவசர எச்சரிக்கை: {', '.join(triggers)}. பயிர் சேதம் ஏற்பட்டால் 72 மணி நேரத்திற்குள் உதவி எண் {PMFBY_HELPLINE} மூலம் புகார் செய்யவும்.",
            "te": f"{disp_loc} కు అత్యవసర హెచ్చరిక: {', '.join(triggers)}. పంట నష్టం జరిగితే 72 గంటల్లో హెల్ప్‌లైన్ {PMFBY_HELPLINE} కు తెలియజేయండి లేదా ఫోటో అప్‌లోడ్ చేయండి.",
            "mr": f"{disp_loc} साठी तातडीचा इशारा: {', '.join(triggers)}. पिकाचे नुकसान झाल्यास 72 तासांत हेल्पलाइन {PMFBY_HELPLINE} वर कळवा किंवा खाली फोटो जोडा.",
        }
    elif alert_level == "AMBER_WATCH":
        msg_map = {
            "en": f"Weather Watch in {disp_loc}: {', '.join(triggers)}. Clear field drainage channels and keep photos ready in case crop damage occurs.",
            "kn": f"{disp_loc} ನಲ್ಲಿ ಹವಾಮಾನ ಎಚ್ಚರಿಕೆ: {', '.join(triggers)}. ಹೊಲದಲ್ಲಿ ನೀರು ಬಸಿದುಹೋಗುವ ಕಾಲುವೆಗಳನ್ನು ಸ್ವಚ್ಛವಾಗಿಡಿ.",
            "hi": f"{disp_loc} में मौसम चेतावनी: {', '.join(triggers)}। खेत की जल निकासी साफ रखें और नुकसान होने पर फोटो लें।",
            "ta": f"{disp_loc} பகுதியில் வானிலை கண்காணிப்பு: {', '.join(triggers)}. வயல் வடிகால் வாய்க்கால்களை சுத்தமாக வைக்கவும்.",
            "te": f"{disp_loc} లో వాతావరణ హెచ్చరిక: {', '.join(triggers)}. పొలంలో నీరు నిల్వ ఉండకుండా కాలువలు శుభ్రంగా ఉంచండి.",
            "mr": f"{disp_loc} मध्ये हवामान सतर्कता: {', '.join(triggers)}. शेतातील पाण्याचा निचरा मोकळा ठेवा.",
        }
    else:
        msg_map = {
            "en": f"Safe conditions in {disp_loc} ({temp_c}°C, {rain_today} mm rain today, {gust_kmh} km/h wind gusts). No extreme weather-loss trigger active today.",
            "kn": f"{disp_loc} ನಲ್ಲಿ ಸುರಕ್ಷಿತ ಹವಾಮಾನವಿದೆ ({temp_c}°C, ಇಂದು {rain_today} ಮಿ.ಮೀ ಮಳೆ). ಇಂದು ಯಾವುದೇ ತೀವ್ರ ಹವಾಮಾನ ಹಾನಿ ಎಚ್ಚರಿಕೆ ಇಲ್ಲ.",
            "hi": f"{disp_loc} में मौसम सुरक्षित है ({temp_c}°C, आज {rain_today} मिमी बारिश)। आज कोई गंभीर फसल नुकसान अलर्ट नहीं है।",
            "ta": f"{disp_loc} பகுதியில் வானிலை பாதுகாப்பாக உள்ளது ({temp_c}°C, இன்று {rain_today} மி.மீ மழை). தீவிர சேத எச்சரிக்கை இல்லை.",
            "te": f"{disp_loc} లో వాతావరణం సురక్షితంగా ఉంది ({temp_c}°C, నేడు {rain_today} మి.మీ వర్షం). తీవ్రమైన పంట నష్ట హెచ్చరిక లేదు.",
            "mr": f"{disp_loc} मध्ये हवामान सुरक्षित आहे ({temp_c}°C, आज {rain_today} मिमी पाऊस). कोणताही गंभीर नुकसान इशारा नाही.",
        }

    advisory = msg_map.get(lang, msg_map["en"])
    coords = weather_data.get("coordinates") or {}

    return {
        "status": "success",
        "is_live_data": weather_data.get("is_live_data") is True,
        "location": disp_loc,
        "coordinates": coords,
        "alert_level": alert_level,
        "event_code": event_code,
        "triggers": triggers,
        "telemetry": {
            "weather_condition": weather_data.get("weather_condition", ""),
            "weather_code": w_code,
            "temperature_c": temp_c,
            "rain_today_mm": rain_today,
            "rain_tomorrow_mm": rain_tom,
            "wind_speed_kmh": wind_kmh,
            "wind_gusts_kmh": gust_kmh,
            "last_updated": weather_data.get("last_updated", ""),
            "source": weather_data.get("source", "Open-Meteo"),
        },
        "advisory": advisory,
        "speech_text": advisory,
        "helpline": PMFBY_HELPLINE,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Timestamped Claim Evidence Dossier
# ─────────────────────────────────────────────────────────────────────────────
def create_claim_dossier(
    user_id: str,
    location_query: str = "",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    policy_id: Optional[str] = None,
    photo_url: str = "",
    notes: str = "",
    language: str = "en",
    db_path: str = DEFAULT_USERS_DB,
    weather_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Bundle field damage photo, GPS, timestamp, and live weather log into a claim dossier."""
    init_insurance_db(db_path)
    uid = (user_id or "guest").strip() or "guest"

    alert_res = evaluate_weather_claim_alert(
        location_query=location_query,
        lat=lat,
        lon=lon,
        language=language,
        weather_data=weather_data,
    )

    if alert_res.get("status") == "success":
        coords = alert_res.get("coordinates") or {}
        final_lat = lat if lat is not None else coords.get("latitude")
        final_lon = lon if lon is not None else coords.get("longitude")
        weather_event = alert_res.get("event_code", "CROP_DAMAGE_REPORT")
        snap = {
            "location": alert_res.get("location", location_query),
            "alert_level": alert_res.get("alert_level"),
            "triggers": alert_res.get("triggers", []),
            "telemetry": alert_res.get("telemetry", {}),
        }
    else:
        final_lat = lat
        final_lon = lon
        weather_event = "MANUAL_FIELD_DAMAGE"
        snap = {
            "location": location_query or "Location not resolved",
            "alert_level": "MANUAL",
            "triggers": [],
            "telemetry": {"note": alert_res.get("message", "Weather snapshot unavailable")},
        }

    claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"
    now_dt = datetime.now(timezone.utc)
    deadline_dt = now_dt + timedelta(hours=72)
    now_iso = now_dt.isoformat()

    clean_notes = (notes or "").strip()[:500]
    with closing(_connect(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO insurance_claims (
                id, user_id, policy_id, weather_event, photo_path,
                gps_lat, gps_lon, weather_snapshot_json, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim_id,
                uid,
                policy_id or None,
                weather_event,
                photo_url or "",
                final_lat,
                final_lon,
                json.dumps(snap, ensure_ascii=False),
                clean_notes,
                now_iso,
            ),
        )
        conn.commit()

    dl = deadline_dt.strftime("%d %b %Y %H:%M UTC")
    checklist_map = {
        "en": [
            f"Report localized crop loss within 72 hours (by {dl}).",
            f"Call Krishi Rakshak Helpline {PMFBY_HELPLINE}, use the Crop Insurance App, or inform your bank/CSC.",
            "Keep this Claim Reference, field GPS coordinates, weather snapshot, and damage photos ready for the loss assessor.",
            "Do not clear the damaged crop before joint field inspection unless instructed by the agriculture officer.",
        ],
        "kn": [
            f"ಬೆಳೆ ಹಾನಿಯನ್ನು 72 ಗಂಟೆಗಳ ಒಳಗೆ ({dl} ಒಳಗಾಗಿ) ವರದಿ ಮಾಡಿ.",
            f"ಕೃಷಿ ರಕ್ಷಕ್ ಸಹಾಯವಾಣಿ {PMFBY_HELPLINE} ಗೆ ಕರೆ ಮಾಡಿ, Crop Insurance ಆ್ಯಪ್ ಅಥವಾ ನಿಮ್ಮ ಬ್ಯಾಂಕ್/CSC ಗೆ ತಿಳಿಸಿ.",
            "ತಪಾಸಣಾಧಿಕಾರಿಗಾಗಿ ಈ ಕ್ಲೈಮ್ ಸಂಖ್ಯೆ, GPS, ಹವಾಮಾನ ದಾಖಲೆ ಮತ್ತು ಫೋಟೋಗಳನ್ನು ಸಿದ್ಧವಾಗಿಡಿ.",
            "ಕೃಷಿ ಅಧಿಕಾರಿಗಳ ಪರಿಶೀಲನೆ ಮುಗಿಯುವವರೆಗೆ ಹಾನಿಗೊಳಗಾದ ಬೆಳೆಯನ್ನು ತೆರವುಗೊಳಿಸಬೇಡಿ.",
        ],
        "hi": [
            f"फसल नुकसान की सूचना 72 घंटे के भीतर ({dl} तक) दर्ज करें।",
            f"कृषि रक्षक हेल्पलाइन {PMFBY_HELPLINE} पर कॉल करें, Crop Insurance ऐप या अपने बैंक/CSC को सूचित करें।",
            "सर्वे अधिकारी के लिए यह क्लेम नंबर, GPS स्थान, मौसम रिपोर्ट और नुकसान की फोटो संभालकर रखें।",
            "कृषि अधिकारी के संयुक्त निरीक्षण से पहले खराब फसल को खेत से न हटाएं।",
        ],
        "ta": [
            f"பயிர் சேதத்தை 72 மணி நேரத்திற்குள் ({dl} முன்) புகார் செய்யுங்கள்.",
            f"கிருஷி ரக்ஷக் உதவி எண் {PMFBY_HELPLINE} ஐ அழைக்கவும் அல்லது வங்கி/CSC மூலம் தெரிவிக்கவும்.",
            "இந்த உரிமைகோரல் எண், GPS, வானிலை பதிவு மற்றும் புகைப்படங்களை ஆய்வாளருக்காக வைத்திருங்கள்.",
            "வேளாண் அதிகாரி ஆய்வு செய்யும் வரை சேதமடைந்த பயிரை அகற்ற வேண்டாம்.",
        ],
        "te": [
            f"పంట నష్టాన్ని 72 గంటలలోపు ({dl} లోపు) నమోదు చేయండి.",
            f"కృషి రక్షక్ హెల్ప్‌లైన్ {PMFBY_HELPLINE} కు కాల్ చేయండి లేదా మీ బ్యాంక్/CSC కి తెలియజేయండి.",
            "ఈ క్లెయిమ్ నంబర్, GPS వివరాలు, వాతావరణ రికార్డు మరియు ఫోటోలను అధికారికి చూపించడానికి సిద్ధంగా ఉంచండి.",
            "వ్యవసాయ అధికారి పరిశీలన పూర్తయ్యే వరకు దెబ్బతిన్న పంటను తొలగించవద్దు.",
        ],
        "mr": [
            f"पीक नुकसानीची तक्रार 72 तासांत ({dl} पूर्वी) नोंदवा.",
            f"कृषी रक्षक हेल्पलाइन {PMFBY_HELPLINE} वर कॉल करा किंवा बँक/CSC कडे माहिती द्या.",
            "हा क्लेम क्रमांक, GPS स्थान, हवामान नोंद आणि नुकसान फोटो तपासणी अधिकाऱ्यासाठी जपून ठेवा.",
            "कृषी अधिकाऱ्यांच्या पाहणीपूर्वी नुकसान झालेले पीक शेतातून काढू नका.",
        ],
    }
    lang_c = (language or "en").strip().lower()
    checklist = checklist_map.get(lang_c, checklist_map["en"])

    return {
        "status": "success",
        "claim": {
            "claim_ref": claim_id,
            "user_id": uid,
            "policy_id": policy_id or None,
            "weather_event": weather_event,
            "photo_url": photo_url or "",
            "gps_lat": final_lat,
            "gps_lon": final_lon,
            "weather_snapshot": snap,
            "notes": clean_notes,
            "created_at": now_iso,
            "report_deadline_utc": deadline_dt.isoformat(),
            "checklist": checklist,
        },
    }


def list_claim_dossiers(user_id: str, db_path: str = DEFAULT_USERS_DB) -> List[Dict[str, Any]]:
    init_insurance_db(db_path)
    uid = (user_id or "guest").strip() or "guest"
    with closing(_connect(db_path)) as conn:
        rows = conn.execute(
            "SELECT * FROM insurance_claims WHERE user_id = ? ORDER BY created_at DESC",
            (uid,),
        ).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        try:
            item["weather_snapshot"] = json.loads(item.pop("weather_snapshot_json", "{}"))
        except Exception:
            item["weather_snapshot"] = {}
        out.append(item)
    return out
