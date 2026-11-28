"""
Animal Husbandry & Dairy Module Router — Pan-India Multi-State & Multilingual.
Covers:
1. Dairy milk procurement rate comparison (KMF Nandini, Amul, Sanchi, Vijaya, Verka, Saras, Gokul, Aavin, Milma, Sudha, Mother Dairy, etc.)
2. Weather-matched high-yield cow and buffalo breeds tailored to state & climate
3. Targeted feed & nutrition planner (dry vs lactating) with regional fodder tips
4. Breeding & sire semen selection guide
5. Livestock disease & behavior advisor with immediate first aid and voice link
6. State cattle markets & veterinary doctor directories
7. SQLite caching keyed by (state, language) with TTL for instant offline/repeated access
"""
from datetime import datetime, timedelta
import json
import math
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import or_, text
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator

from database import get_db, engine
import models
import language_config

router = APIRouter(prefix="/api/dairy", tags=["dairy"])

CACHE_TTL_SECONDS = 3600  # 1 hour TTL for dairy data cache


# ============================================================================
# STATE RESOLUTION & NORMALIZATION
# ============================================================================

STATE_CENTROIDS = {
    "Madhya Pradesh": (22.7196, 75.8577),
    "Karnataka": (12.9716, 77.5946),
    "Maharashtra": (18.5204, 73.8567),
    "Telangana": (17.3850, 78.4867),
    "Andhra Pradesh": (16.3067, 80.4365),
    "Tamil Nadu": (11.0168, 76.9558),
    "Kerala": (10.5276, 76.2144),
    "Punjab": (30.9010, 75.8573),
    "Haryana": (29.6857, 76.9905),
    "Gujarat": (23.0225, 72.5714),
    "Rajasthan": (26.9124, 75.7873),
    "Uttar Pradesh": (26.8467, 80.9462),
    "Bihar": (25.5941, 85.1376),
    "West Bengal": (22.5726, 88.3639),
    "Odisha": (20.2961, 85.8245),
}

CITY_STATE_LOOKUP = {
    # Madhya Pradesh
    "indore": "Madhya Pradesh", "bhopal": "Madhya Pradesh", "ujjain": "Madhya Pradesh",
    "gwalior": "Madhya Pradesh", "jabalpur": "Madhya Pradesh", "dewas": "Madhya Pradesh",
    "sehore": "Madhya Pradesh", "khargone": "Madhya Pradesh", "khandwa": "Madhya Pradesh",
    "malwa": "Madhya Pradesh", "nimar": "Madhya Pradesh", "satna": "Madhya Pradesh",
    "rewa": "Madhya Pradesh", "sagar": "Madhya Pradesh", "ratlam": "Madhya Pradesh",
    # Karnataka
    "bengaluru": "Karnataka", "bangalore": "Karnataka", "shivamogga": "Karnataka",
    "shimoga": "Karnataka", "davanagere": "Karnataka", "mysuru": "Karnataka",
    "mysore": "Karnataka", "hassan": "Karnataka", "belagavi": "Karnataka",
    "belgaum": "Karnataka", "dharwad": "Karnataka", "hubli": "Karnataka",
    "kalaburagi": "Karnataka", "gulbarga": "Karnataka", "mangaluru": "Karnataka",
    "mangalore": "Karnataka", "tumakuru": "Karnataka", "mandya": "Karnataka",
    "chikkamagaluru": "Karnataka", "ballari": "Karnataka", "bellary": "Karnataka",
    "raichur": "Karnataka", "kolar": "Karnataka", "udupi": "Karnataka",
    # Telangana
    "hyderabad": "Telangana", "secunderabad": "Telangana", "rangareddy": "Telangana",
    "warangal": "Telangana", "karimnagar": "Telangana", "nalgonda": "Telangana",
    "khammam": "Telangana", "nizamabad": "Telangana", "mahabubnagar": "Telangana",
    # Andhra Pradesh
    "amaravati": "Andhra Pradesh", "vijayawada": "Andhra Pradesh",
    "visakhapatnam": "Andhra Pradesh", "vizag": "Andhra Pradesh", "guntur": "Andhra Pradesh",
    "ongole": "Andhra Pradesh", "tirupati": "Andhra Pradesh", "nellore": "Andhra Pradesh",
    "kurnool": "Andhra Pradesh", "kadapa": "Andhra Pradesh", "kakinada": "Andhra Pradesh",
    "rajahmundry": "Andhra Pradesh", "anantapur": "Andhra Pradesh",
    # Maharashtra
    "mumbai": "Maharashtra", "pune": "Maharashtra", "nashik": "Maharashtra",
    "nagpur": "Maharashtra", "kolhapur": "Maharashtra", "solapur": "Maharashtra",
    "ahmednagar": "Maharashtra", "satara": "Maharashtra", "sangli": "Maharashtra",
    "aurangabad": "Maharashtra", "chhatrapati sambhajinagar": "Maharashtra",
    "jalgaon": "Maharashtra", "amravati": "Maharashtra", "baramati": "Maharashtra",
    # Punjab
    "ludhiana": "Punjab", "amritsar": "Punjab", "jalandhar": "Punjab",
    "patiala": "Punjab", "bathinda": "Punjab", "mohali": "Punjab", "khanna": "Punjab",
    "jagraon": "Punjab",
    # Haryana
    "karnal": "Haryana", "hisar": "Haryana", "rohtak": "Haryana",
    "panipat": "Haryana", "ambala": "Haryana", "gurugram": "Haryana",
    "gurgaon": "Haryana", "faridabad": "Haryana", "sonipat": "Haryana", "sirsa": "Haryana",
    # Gujarat
    "ahmedabad": "Gujarat", "surat": "Gujarat", "vadodara": "Gujarat",
    "rajkot": "Gujarat", "anand": "Gujarat", "mehsana": "Gujarat",
    "bhavnagar": "Gujarat", "jamnagar": "Gujarat", "gandhinagar": "Gujarat",
    "banaskantha": "Gujarat", "kutch": "Gujarat",
    # Rajasthan
    "jaipur": "Rajasthan", "jodhpur": "Rajasthan", "udaipur": "Rajasthan",
    "kota": "Rajasthan", "bikaner": "Rajasthan", "ajmer": "Rajasthan",
    "alwar": "Rajasthan", "bhilwara": "Rajasthan", "pushkar": "Rajasthan",
    # Tamil Nadu
    "chennai": "Tamil Nadu", "coimbatore": "Tamil Nadu", "madurai": "Tamil Nadu",
    "salem": "Tamil Nadu", "tiruchirappalli": "Tamil Nadu", "trichy": "Tamil Nadu",
    "erode": "Tamil Nadu", "tirunelveli": "Tamil Nadu", "vellore": "Tamil Nadu",
    "pollachi": "Tamil Nadu", "thanjavur": "Tamil Nadu", "tiruppur": "Tamil Nadu", "kangayam": "Tamil Nadu",
    # Kerala
    "thiruvananthapuram": "Kerala", "trivandrum": "Kerala", "kochi": "Kerala",
    "cochin": "Kerala", "kozhikode": "Kerala", "calicut": "Kerala",
    "thrissur": "Kerala", "palakkad": "Kerala", "kollam": "Kerala", "kannur": "Kerala",
    # Uttar Pradesh
    "lucknow": "Uttar Pradesh", "kanpur": "Uttar Pradesh", "varanasi": "Uttar Pradesh",
    "agra": "Uttar Pradesh", "meerut": "Uttar Pradesh", "prayagraj": "Uttar Pradesh",
    "allahabad": "Uttar Pradesh", "bareilly": "Uttar Pradesh", "aligarh": "Uttar Pradesh",
    "gorakhpur": "Uttar Pradesh", "noida": "Uttar Pradesh",
    # Bihar
    "patna": "Bihar", "gaya": "Bihar", "bhagalpur": "Bihar",
    "muzaffarpur": "Bihar", "purnia": "Bihar", "sonepur": "Bihar",
    # West Bengal
    "kolkata": "West Bengal", "calcutta": "West Bengal", "howrah": "West Bengal",
    "hooghly": "West Bengal", "durgapur": "West Bengal", "asansol": "West Bengal",
    "siliguri": "West Bengal",
    # Odisha
    "bhubaneswar": "Odisha", "cuttack": "Odisha", "rourkela": "Odisha", "puri": "Odisha",
}


def _norm_lang(language: Optional[str]) -> str:
    """Normalizes any input language code or name to standard 2-letter or BCP-47."""
    if not language:
        return "en"
    clean = language.strip().lower()
    short = clean.split("-")[0]
    if short in ("kn", "hi", "te", "ta", "mr", "ml", "bn", "gu", "pa", "en"):
        return short
    for code, cfg in language_config.SUPPORTED_LANGUAGES.items():
        if clean in cfg.get("aliases", []):
            return str(cfg.get("short_code", "en"))
    return "en"


def _resolve_state(
    state: Optional[str] = None,
    district: Optional[str] = None,
    location_name: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> str:
    """
    Robust Indian state resolver that accepts state name, district, location_name,
    or lat/lon coordinates.
    """
    # 1. Direct state name check
    if state and state.strip() and state.strip().lower() not in ("all", "india", "undefined", "null"):
        s = state.strip().lower()
        if "madhya" in s or s == "mp":
            return "Madhya Pradesh"
        if "telangana" in s or s == "ts" or s == "tg":
            return "Telangana"
        if "andhra" in s or s == "ap":
            return "Andhra Pradesh"
        if "maharashtra" in s or s == "mh":
            return "Maharashtra"
        if "punjab" in s or s == "pb":
            return "Punjab"
        if "haryana" in s or s == "hr":
            return "Haryana"
        if "gujarat" in s or s == "gj":
            return "Gujarat"
        if "uttar" in s or s == "up":
            return "Uttar Pradesh"
        if "tamil" in s or s == "tn":
            return "Tamil Nadu"
        if "rajasthan" in s or s == "rj":
            return "Rajasthan"
        if "kerala" in s or s == "kl":
            return "Kerala"
        if "karnataka" in s or s == "ka":
            return "Karnataka"
        if "bihar" in s or s == "br":
            return "Bihar"
        if "bengal" in s or s == "wb":
            return "West Bengal"
        if "odisha" in s or "orissa" in s:
            return "Odisha"
        return state.strip().title()

    # 2. Check location_name or district keywords
    text_to_check = f"{location_name or ''} {district or ''}".lower()
    for st_name in STATE_CENTROIDS:
        if st_name.lower() in text_to_check:
            return st_name
    if "mp" in text_to_check.split() or "m.p." in text_to_check:
        return "Madhya Pradesh"
    if "ts" in text_to_check.split() or "tg" in text_to_check:
        return "Telangana"
    if "ap" in text_to_check.split() or "a.p." in text_to_check:
        return "Andhra Pradesh"
    for city, st in CITY_STATE_LOOKUP.items():
        if city in text_to_check:
            return st

    # 3. Check coordinates against state centroids
    if lat is not None and lon is not None:
        best_state = "Karnataka"
        min_dist = float("inf")
        for st_name, (clat, clon) in STATE_CENTROIDS.items():
            dist = math.hypot(lat - clat, lon - clon)
            if dist < min_dist:
                min_dist = dist
                best_state = st_name
        return best_state

    return "Karnataka"


# ============================================================================
# SQLITE CACHING WITH TTL
# ============================================================================

def _cache_get(endpoint: str, state: str, language: str) -> Optional[Any]:
    """Retrieve unexpired cached JSON from dairy_cache."""
    cache_key = f"{endpoint}:{state}:{language}".lower()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT data_json, expires_at FROM dairy_cache WHERE cache_key = :k"),
                {"k": cache_key}
            ).fetchone()
            if row and row[0]:
                exp = row[1]
                if isinstance(exp, str):
                    try:
                        exp = datetime.fromisoformat(exp)
                    except Exception:
                        exp = None
                if exp is None or exp > datetime.utcnow():
                    return json.loads(row[0])
    except Exception:
        pass
    return None


def _cache_set(endpoint: str, state: str, language: str, data: Any, ttl_seconds: int = CACHE_TTL_SECONDS) -> None:
    """Write data to dairy_cache table with TTL."""
    cache_key = f"{endpoint}:{state}:{language}".lower()
    expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    data_json = json.dumps(data)
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    CREATE TABLE IF NOT EXISTS dairy_cache (
                        cache_key VARCHAR(150) PRIMARY KEY,
                        endpoint VARCHAR(50),
                        state VARCHAR(60),
                        language VARCHAR(20),
                        data_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP
                    )
                """)
            )
            conn.execute(
                text("""
                    INSERT INTO dairy_cache (cache_key, endpoint, state, language, data_json, expires_at)
                    VALUES (:k, :ep, :st, :lg, :dj, :exp)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        data_json = :dj,
                        expires_at = :exp
                """),
                {
                    "k": cache_key,
                    "ep": endpoint,
                    "st": state,
                    "lg": language,
                    "dj": data_json,
                    "exp": expires_at.isoformat(),
                }
            )
    except Exception:
        pass


# ============================================================================
# COMPREHENSIVE MULTI-STATE DAIRY PROFILES
# ============================================================================

STATE_DAIRY_PROFILES: Dict[str, Dict[str, Any]] = {
    "Madhya Pradesh": {
        "cooperative_name": "Sanchi (MPCDF)",
        "cooperative_banner": "Sanchi MPCDF Procurement Benchmark: ₹36.50/L Base Cow Milk (FAT 3.5% / SNF 8.5%) & ₹53.00/L Buffalo Milk (FAT 6.0% / SNF 9.0%)",
        "incentive_scheme": "MP Rajya Dairy Sahakari Protsahan",
        "govt_incentive": 0.0,
        "dairies": [
            {"dairy_name": "Sanchi (MPCDF)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 36.5, "fat_rate_factor": 4.2, "snf_rate_factor": 2.6, "govt_incentive": 0.0, "notes": "MPCDF Sanchi cooperative benchmark (Indore, Ujjain, Bhopal, Malwa)"},
            {"dairy_name": "Sanchi (MPCDF)", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 53.0, "fat_rate_factor": 5.5, "snf_rate_factor": 3.0, "govt_incentive": 0.0, "notes": "MPCDF Sanchi high-fat buffalo milk rate"},
            {"dairy_name": "Amul (MP Procurement)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 36.0, "fat_rate_factor": 4.1, "snf_rate_factor": 2.5, "govt_incentive": 0.0, "notes": "Amul Malwa & Nimar village collection center"},
            {"dairy_name": "Mother Dairy", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 35.5, "fat_rate_factor": 4.0, "snf_rate_factor": 2.4, "govt_incentive": 0.0, "notes": "Direct farm-gate chilled procurement"},
            {"dairy_name": "Amul (MP Procurement)", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 52.5, "fat_rate_factor": 5.4, "snf_rate_factor": 2.9, "govt_incentive": 0.0, "notes": "Bhadawari & Murrah high-fat milk incentive"},
        ],
        "recommended_breeds": ["Malvi", "Nimari", "Gir", "Murrah", "Bhadawari", "HF/Jersey Cross"],
        "fodder_tip": "Malwa & Nimar zone: Prioritize Berseem (winter green fodder), Jowar/Sorghum stover, Wheat bhusa, and Soybean straw with Mustard/Soybean oilcake.",
        "cattle_market_note": "Major weekly mandis: Sanwer (Indore), Ujjain, Dewas, Sehore & Khargone Nimar fair. Pashu Sanjeevini Helpline: 1962.",
        "sire_options": ["Gir Bull Semen", "Malvi Bull Semen", "Murrah Progeny Semen", "HF Cross Straws", "Jersey Cross Straws"],
        "seasonal_alerts": ["FMD (खुरपका-मुंहपका) vaccination due pre-monsoon", "Haemorrhagic Septicaemia (HS) alert in low-lying zones", "Lumpy Skin Disease (LSD) booster", "Summer heat stress cooling for crossbreds"],
    },
    "Karnataka": {
        "cooperative_name": "KMF Nandini",
        "cooperative_banner": "KMF Nandini Payout: ₹42.00/L Base + ₹5.00/L Ksheera Dhare DBT Bonus = ₹47.00/L Total Effective Cow Milk Payout",
        "incentive_scheme": "Ksheera Dhare Direct Benefit Transfer (₹5/L)",
        "govt_incentive": 5.0,
        "dairies": [
            {"dairy_name": "KMF Nandini (BAMUL/KMF)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 42.0, "fat_rate_factor": 4.5, "snf_rate_factor": 2.8, "govt_incentive": 5.0, "notes": "Karnataka Milk Federation standard rate + ₹5/L Ksheera Dhare direct subsidy"},
            {"dairy_name": "KMF Nandini (BAMUL/KMF)", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 54.0, "fat_rate_factor": 5.8, "snf_rate_factor": 3.2, "govt_incentive": 5.0, "notes": "High-fat Murrah & Surti buffalo milk rate + ₹5/L subsidy"},
            {"dairy_name": "Dodla Dairy", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 38.0, "fat_rate_factor": 4.2, "snf_rate_factor": 2.6, "govt_incentive": 0.0, "notes": "Private dairy procurement (Kolar, Chikkaballapura, Tumakuru)"},
            {"dairy_name": "Heritage Foods", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 37.5, "fat_rate_factor": 4.1, "snf_rate_factor": 2.5, "govt_incentive": 0.0, "notes": "Commercial dairy collection center"},
            {"dairy_name": "Amul (Karnataka Procurement)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 38.5, "fat_rate_factor": 4.3, "snf_rate_factor": 2.7, "govt_incentive": 0.0, "notes": "North Karnataka / Belagavi border collection"},
        ],
        "recommended_breeds": ["Hallikar", "Malnad Gidda", "HF/Jersey Cross", "Deoni", "Khillari", "Amrithmahal", "Murrah", "Surti"],
        "fodder_tip": "Southern Dry / Malnad zone: Combine Ragi straw, Hybrid Napier (CO-4/CO-5), Maize green fodder, Sugarcane tops, Groundnut cake, and Nandini mineral mixture.",
        "cattle_market_note": "Famous markets: Mandya, Hassan, Tiptur, Shivamogga, Belagavi, Haveri cattle shandies. Pashu Sanjeevini Helpline: 1962.",
        "sire_options": ["Hallikar AI Straw (KAHBI)", "Malnad Gidda Semen", "Deoni Bull Semen", "Murrah Progeny Tested Semen", "HF High-Yield Semen"],
        "seasonal_alerts": ["FMD (ಕಾಲುಬಾಯಿ ಜ್ವರ) booster dose", "Anthrax vigilance in dry pasture regions", "Lumpy Skin Disease (ಚರ್ಮ ಗಂಟು ರೋಗ)", "Summer heat stress cooling for HF cross"],
    },
    "Telangana": {
        "cooperative_name": "Vijaya Dairy (TSDDC)",
        "cooperative_banner": "Vijaya Dairy (TSDDC) Payout: ₹37.00/L Base + ₹4.00/L State Incentive = ₹41.00/L Cow Milk Rate",
        "incentive_scheme": "Telangana State Vijaya Dairy Incentive (₹4/L)",
        "govt_incentive": 4.0,
        "dairies": [
            {"dairy_name": "Vijaya Dairy (TSDDC)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 37.0, "fat_rate_factor": 4.2, "snf_rate_factor": 2.6, "govt_incentive": 4.0, "notes": "TSDDC Vijaya cooperative + ₹4/L state incentive"},
            {"dairy_name": "Vijaya Dairy (TSDDC)", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 55.0, "fat_rate_factor": 5.6, "snf_rate_factor": 3.1, "govt_incentive": 4.0, "notes": "Vijaya Buffalo milk rate + ₹4/L incentive"},
            {"dairy_name": "Heritage Foods", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 38.0, "fat_rate_factor": 4.3, "snf_rate_factor": 2.7, "govt_incentive": 0.0, "notes": "Hyderabad/Rangareddy private procurement"},
            {"dairy_name": "Dodla Dairy", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 54.5, "fat_rate_factor": 5.5, "snf_rate_factor": 3.0, "govt_incentive": 0.0, "notes": "Telangana chilling center rate"},
        ],
        "recommended_breeds": ["Ongole", "Murrah", "Poda Thurpu", "Deoni", "HF/Jersey Cross"],
        "fodder_tip": "Deccan plateau: Use Para grass, Super Napier, Sorghum (Jowar) stover, and Paddy straw with Groundnut/Cottonseed cake.",
        "cattle_market_note": "Hyderabad (Erragadda), Nalgonda, Karimnagar, Warangal cattle markets. Telangana Vet Helpline: 1962.",
        "sire_options": ["Ongole Bull Semen", "Murrah Frozen Semen", "Deoni Pure Semen", "Jersey Cross Semen"],
        "seasonal_alerts": ["FMD (గాలికుంటు వ్యాధి) vaccination", "HS & BQ monsoonal alerts", "Tick-borne theileriosis in crossbreds"],
    },
    "Andhra Pradesh": {
        "cooperative_name": "Vijaya Dairy (APDDCF) / Sangam",
        "cooperative_banner": "APDDCF / Sangam Benchmark: ₹37.50/L Cow Milk & ₹55.50/L Buffalo Milk Benchmark",
        "incentive_scheme": "AP Milk Producer Direct Procurement",
        "govt_incentive": 0.0,
        "dairies": [
            {"dairy_name": "Vijaya Dairy (APDDCF)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 37.5, "fat_rate_factor": 4.2, "snf_rate_factor": 2.6, "govt_incentive": 0.0, "notes": "AP cooperative milk union benchmark"},
            {"dairy_name": "Sangam Dairy (Guntur)", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 55.5, "fat_rate_factor": 5.7, "snf_rate_factor": 3.1, "govt_incentive": 0.0, "notes": "Krishna/Guntur delta high-fat buffalo rate"},
            {"dairy_name": "Heritage Foods", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 38.0, "fat_rate_factor": 4.3, "snf_rate_factor": 2.7, "govt_incentive": 0.0, "notes": "Coastal & Rayalaseema procurement"},
            {"dairy_name": "Tirumala Dairy", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 55.0, "fat_rate_factor": 5.6, "snf_rate_factor": 3.0, "govt_incentive": 0.0, "notes": "Chittoor / Tirupati private dairy"},
        ],
        "recommended_breeds": ["Ongole", "Murrah", "Punganur", "Godavari Buffalo", "HF/Jersey Cross"],
        "fodder_tip": "Coastal / Rayalaseema zone: Super Napier, Hybrid Napier, Paddy straw, Blackgram/Greengram husk, and Cottonseed cake.",
        "cattle_market_note": "Guntur, Ongole, Vijayawada, Tirupati cattle shandies. AP Animal Husbandry: 1962.",
        "sire_options": ["Ongole Elite Bull Semen", "Punganur Preservation Semen", "High Genetic Merit Murrah", "HF Cross"],
        "seasonal_alerts": ["HS (గురక వ్యాధి) coastal delta alert", "FMD timely vaccination", "Mastitis care in high-yield cows"],
    },
    "Maharashtra": {
        "cooperative_name": "Mahanand / Gokul",
        "cooperative_banner": "Gokul & Mahanand Payout: ₹37.50/L Base + ₹5.00/L Maharashtra State Incentive = ₹42.50/L Cow Milk Rate",
        "incentive_scheme": "Maharashtra Cow Milk Subsidy (₹5/L)",
        "govt_incentive": 5.0,
        "dairies": [
            {"dairy_name": "Gokul (Kolhapur Union)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 37.5, "fat_rate_factor": 4.3, "snf_rate_factor": 2.7, "govt_incentive": 5.0, "notes": "Gokul cooperative + Maharashtra ₹5/L cow milk direct subsidy"},
            {"dairy_name": "Mahanand Dairy", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 36.5, "fat_rate_factor": 4.1, "snf_rate_factor": 2.6, "govt_incentive": 5.0, "notes": "State dairy federation rate + ₹5/L incentive"},
            {"dairy_name": "Chitale Dairy", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 57.0, "fat_rate_factor": 5.9, "snf_rate_factor": 3.2, "govt_incentive": 0.0, "notes": "Western Maharashtra premium buffalo procurement"},
            {"dairy_name": "Warana Dairy", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 37.0, "fat_rate_factor": 4.2, "snf_rate_factor": 2.6, "govt_incentive": 5.0, "notes": "Kolhapur/Sangli cooperative + subsidy"},
        ],
        "recommended_breeds": ["Khillari", "Deoni", "Red Kandhari", "Dangi", "Pandharpuri Buffalo", "HF Cross", "Jersey Cross"],
        "fodder_tip": "Western Maharashtra & Marathwada: Lucerne (मेथी घास), Sugarcane tops, Jowar kadbi, Maize silage, and Cottonseed cake.",
        "cattle_market_note": "Baramati, Ghoti (Nashik), Loni (Ahmednagar), Kolhapur cattle bazaars. Maharashtra Helpline: 1962.",
        "sire_options": ["Pandharpuri Buffalo Semen", "Khillari Bull Straws", "Deoni Bull Straws", "High EBV HF Cross"],
        "seasonal_alerts": ["FMD (लाळ्या खुरकूत) vaccination schedule", "Lumpy Skin Disease (LSD) booster", "Black Quarter (एकटांग्या) in humid soils"],
    },
    "Gujarat": {
        "cooperative_name": "Amul (GCMMF)",
        "cooperative_banner": "Amul (GCMMF) / Banas Benchmark: ₹38.50/L Cow Milk & ₹56.50/L Buffalo Milk (Jaffarabadi/Mehsana)",
        "incentive_scheme": "GCMMF Cooperative Dividend & Patronage",
        "govt_incentive": 0.0,
        "dairies": [
            {"dairy_name": "Amul (GCMMF Anand)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 38.5, "fat_rate_factor": 4.4, "snf_rate_factor": 2.8, "govt_incentive": 0.0, "notes": "GCMMF village society standard payout"},
            {"dairy_name": "Amul (GCMMF Anand)", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 56.5, "fat_rate_factor": 5.9, "snf_rate_factor": 3.2, "govt_incentive": 0.0, "notes": "High-fat Mehsana & Jaffarabadi rate"},
            {"dairy_name": "Banas Dairy (Palanpur)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 38.2, "fat_rate_factor": 4.3, "snf_rate_factor": 2.7, "govt_incentive": 0.0, "notes": "North Gujarat largest cooperative union"},
            {"dairy_name": "Dudhsagar Dairy (Mehsana)", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 56.0, "fat_rate_factor": 5.8, "snf_rate_factor": 3.1, "govt_incentive": 0.0, "notes": "Mehsana buffalo procurement benchmark"},
        ],
        "recommended_breeds": ["Gir", "Kankrej", "Jaffarabadi", "Mehsana", "Banni", "HF/Jersey Cross"],
        "fodder_tip": "Saurashtra / North Gujarat: Lucerne (Alfalfa), Bajra/Jowar green fodder, Groundnut haulms, Cottonseed cake, and Amul Dan.",
        "cattle_market_note": "Anand, Mehsana, Bhavnagar, Jasdan (Rajkot) cattle markets. Gujarat Pashupalan Helpline: 1962.",
        "sire_options": ["Pure Gir Bull Semen (NDDB / SAG)", "Kankrej Bull Semen", "Mehsana High-Fat Semen", "Jaffarabadi Semen"],
        "seasonal_alerts": ["FMD (ખરવા-મોવાસા) vaccination", "Brucellosis control in breeding herds", "LSD prevention in Kutch/Saurashtra"],
    },
    "Punjab": {
        "cooperative_name": "Verka (Milkfed Punjab)",
        "cooperative_banner": "Verka (Milkfed Punjab) Benchmark: ₹39.00/L Cow Milk & ₹57.50/L Murrah Buffalo Milk",
        "incentive_scheme": "Punjab State Cooperative Dividend",
        "govt_incentive": 0.0,
        "dairies": [
            {"dairy_name": "Verka (Milkfed Punjab)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 39.0, "fat_rate_factor": 4.5, "snf_rate_factor": 2.8, "govt_incentive": 0.0, "notes": "Milkfed Verka cooperative procurement rate"},
            {"dairy_name": "Verka (Milkfed Punjab)", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 57.5, "fat_rate_factor": 6.0, "snf_rate_factor": 3.3, "govt_incentive": 0.0, "notes": "Murrah and Nili-Ravi high-fat milk procurement"},
            {"dairy_name": "Nestle (Moga Procurement)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 38.5, "fat_rate_factor": 4.4, "snf_rate_factor": 2.7, "govt_incentive": 0.0, "notes": "Moga/Ludhiana commercial farm-gate collection"},
        ],
        "recommended_breeds": ["Sahiwal", "Murrah", "Nili-Ravi", "HF/Jersey Cross"],
        "fodder_tip": "Indo-Gangetic plains: Berseem (winter), Oats, Maize silage, Wheat bhusa, Mustard cake, and balanced mineral mixture.",
        "cattle_market_note": "Jagraon (Ludhiana), Khanna, Vallah (Amritsar) cattle fairs. Punjab Animal Husbandry: 1962.",
        "sire_options": ["Progeny-Tested Sahiwal Semen", "Elite Murrah Bull Semen", "Nili-Ravi Buffalo Semen", "HF Semen"],
        "seasonal_alerts": ["HS (ਗਲਘੋਟੂ) timely monsoon vaccination", "FMD (ਮੂੰਹ-ਖੁਰ) vaccine", "Winter calf pneumonia management"],
    },
    "Haryana": {
        "cooperative_name": "Vita (Haryana Dairy)",
        "cooperative_banner": "Vita (Haryana Dairy) Benchmark: ₹38.50/L Cow Milk & ₹57.00/L Murrah Buffalo Milk",
        "incentive_scheme": "Haryana Dugdh Utpadak Protsahan",
        "govt_incentive": 0.0,
        "dairies": [
            {"dairy_name": "Vita (Haryana Dairy Federation)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 38.5, "fat_rate_factor": 4.4, "snf_rate_factor": 2.7, "govt_incentive": 0.0, "notes": "Haryana cooperative federation rate"},
            {"dairy_name": "Vita (Haryana Dairy Federation)", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 57.0, "fat_rate_factor": 5.9, "snf_rate_factor": 3.2, "govt_incentive": 0.0, "notes": "Murrah heartland buffalo milk benchmark"},
        ],
        "recommended_breeds": ["Sahiwal", "Murrah", "Hariana", "HF/Jersey Cross"],
        "fodder_tip": "Murrah belt: Berseem, Jowar/Bajra, Maize silage, Wheat bhusa, Mustard cake, and Vita mineral mixture.",
        "cattle_market_note": "Karnal, Rohtak, Hisar, Jhajjar Murrah trade mandis. Haryana Vet Helpline: 1962.",
        "sire_options": ["Central Frozen Semen Station Murrah Semen", "Hariana Dual-Purpose Semen", "Sahiwal Semen"],
        "seasonal_alerts": ["FMD (खुरपका) booster", "Haemorrhagic Septicaemia (गलघोंटू) prevention", "Heat stress alleviation in lactating Murrah"],
    },
    "Rajasthan": {
        "cooperative_name": "RCDF Saras",
        "cooperative_banner": "RCDF Saras Payout: ₹37.00/L Base + ₹5.00/L Mukhyamantri Sambal Bonus = ₹42.00/L Cow Milk Rate",
        "incentive_scheme": "Mukhyamantri Dugdh Utpadak Sambal Yojana (₹5/L)",
        "govt_incentive": 5.0,
        "dairies": [
            {"dairy_name": "Saras (RCDF Jaipur)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 37.0, "fat_rate_factor": 4.2, "snf_rate_factor": 2.6, "govt_incentive": 5.0, "notes": "RCDF Saras cooperative + ₹5/L Sambal subsidy directly to bank"},
            {"dairy_name": "Saras (RCDF Jaipur)", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 54.0, "fat_rate_factor": 5.6, "snf_rate_factor": 3.0, "govt_incentive": 5.0, "notes": "Murrah buffalo procurement + ₹5/L Sambal subsidy"},
            {"dairy_name": "Amul (Rajasthan Procurement)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 37.5, "fat_rate_factor": 4.2, "snf_rate_factor": 2.6, "govt_incentive": 0.0, "notes": "Alwar/Bharatpur collection center"},
        ],
        "recommended_breeds": ["Rathi", "Tharparkar", "Gir", "Red Sindhi", "Nagori", "Murrah"],
        "fodder_tip": "Arid / Semi-arid zone: Bajra kadbi, Sevah grass, Guar korma, Groundnut haulms, Mustard cake, and salt supplementation.",
        "cattle_market_note": "Pushkar fair, Nagaur fair, Tilwara (Barmer), Jaipur cattle mandis. Rajasthan Animal Care: 1962.",
        "sire_options": ["Tharparkar Desert Semen", "Rathi Pure Bull Semen", "Gir Semen", "Murrah Buffalo Semen"],
        "seasonal_alerts": ["Lumpy Skin Disease (LSD) vigil", "Enterotoxaemia & FMD immunization", "Extreme summer dehydration precautions"],
    },
    "Tamil Nadu": {
        "cooperative_name": "Aavin (TCMPF)",
        "cooperative_banner": "Aavin (TCMPF) Payout: ₹38.00/L Base + ₹3.00/L State Procurement Bonus = ₹41.00/L Cow Milk Rate",
        "incentive_scheme": "Tamil Nadu Dairy Farmers Incentive (₹3/L)",
        "govt_incentive": 3.0,
        "dairies": [
            {"dairy_name": "Aavin (TCMPF)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 38.0, "fat_rate_factor": 4.2, "snf_rate_factor": 2.7, "govt_incentive": 3.0, "notes": "Aavin cooperative society + ₹3/L state bonus"},
            {"dairy_name": "Aavin (TCMPF)", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 54.0, "fat_rate_factor": 5.5, "snf_rate_factor": 3.0, "govt_incentive": 3.0, "notes": "Murrah & Toda buffalo milk rate + ₹3/L bonus"},
            {"dairy_name": "Hatsun (Arokya)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 37.5, "fat_rate_factor": 4.2, "snf_rate_factor": 2.6, "govt_incentive": 0.0, "notes": "Salem / Coimbatore private collection"},
        ],
        "recommended_breeds": ["Kangayam", "Umblachery", "Bargur", "Alambadi", "Murrah", "HF Cross", "Jersey Cross"],
        "fodder_tip": "Southern zone: CO-4 / CO-5 Cumbu Napier, Cholam (Sorghum), Paddy straw, Groundnut cake, and Aavin mineral mixture.",
        "cattle_market_note": "Pollachi, Erode, Manapparai, Anthiyur cattle shandies. Tamil Nadu Animal Husbandry: 1962.",
        "sire_options": ["Kangayam Bull Semen", "Jersey Cross Elite Semen", "Murrah Semen Straws"],
        "seasonal_alerts": ["FMD (கோமாரி நோய்) vaccination", "Anthrax precautions in dry grazing lands", "Black Quarter (அடைப்பான்) alert"],
    },
    "Kerala": {
        "cooperative_name": "Milma (KCMMF)",
        "cooperative_banner": "Milma (KCMMF) Payout: ₹40.50/L Base + ₹4.00/L Local Body Milk Subsidy = ₹44.50/L Cow Milk Rate",
        "incentive_scheme": "Kerala Local Self Govt Dairy Subsidy",
        "govt_incentive": 4.0,
        "dairies": [
            {"dairy_name": "Milma (KCMMF)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 40.5, "fat_rate_factor": 4.4, "snf_rate_factor": 2.8, "govt_incentive": 4.0, "notes": "Milma cooperative societies + panchayat subsidy"},
            {"dairy_name": "Milma (KCMMF)", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 56.0, "fat_rate_factor": 5.7, "snf_rate_factor": 3.1, "govt_incentive": 4.0, "notes": "Milma high-fat buffalo procurement"},
        ],
        "recommended_breeds": ["Vechur", "Kasaragod Dwarf", "Sunandini", "Malabari", "Murrah"],
        "fodder_tip": "High-rainfall zone: Hybrid Napier, Guinea grass, Paddy straw, Coconut cake, and Milma balanced feed.",
        "cattle_market_note": "Chalakkudy, Vandanmedu, Kuzhalmannam (Palakkad) cattle markets. Kerala Vet Helpline: 1962.",
        "sire_options": ["Sunandini Cross Semen (KLDB Mattupetty)", "Jersey Semen", "Murrah Semen"],
        "seasonal_alerts": ["Mastitis (അകിടുവീക്കം) high-humidity risk", "FMD (കുളമ്പുരോഗം) alert", "Foot rot during monsoon rains"],
    },
    "Uttar Pradesh": {
        "cooperative_name": "Parag (PCDF)",
        "cooperative_banner": "Parag (PCDF) / Mother Dairy Benchmark: ₹36.50/L Cow Milk & ₹54.00/L Buffalo Milk",
        "incentive_scheme": "Gokul Puraskar / PCDF Scheme",
        "govt_incentive": 0.0,
        "dairies": [
            {"dairy_name": "Parag (PCDF Lucknow)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 36.5, "fat_rate_factor": 4.1, "snf_rate_factor": 2.5, "govt_incentive": 0.0, "notes": "UP Pradeshik Cooperative Dairy Federation benchmark"},
            {"dairy_name": "Parag (PCDF Lucknow)", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 54.0, "fat_rate_factor": 5.6, "snf_rate_factor": 3.0, "govt_incentive": 0.0, "notes": "Bhadawari & Murrah buffalo procurement"},
            {"dairy_name": "Mother Dairy / Amul (UP)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 37.0, "fat_rate_factor": 4.2, "snf_rate_factor": 2.6, "govt_incentive": 0.0, "notes": "Western UP & Lucknow chilling centers"},
        ],
        "recommended_breeds": ["Sahiwal", "Gangatiri", "Ponwar", "Murrah", "Bhadawari", "HF Cross"],
        "fodder_tip": "Gangetic plains: Berseem, Green Sorghum, Wheat bhusa, Mustard cake, and Sugarcane tops.",
        "cattle_market_note": "Bateshwar Fair (Agra), Meerut, Lucknow, Varanasi cattle mandis. UP Animal Health: 1962.",
        "sire_options": ["Sahiwal Progeny Semen", "Bhadawari High-Fat Buffalo Semen", "Murrah Semen", "HF Cross"],
        "seasonal_alerts": ["HS (गलघोंटू) pre-monsoon vaccination", "BQ (लंगड़ा बुखार) alert", "FMD immunizations"],
    },
    "Bihar": {
        "cooperative_name": "Sudha (COMFED)",
        "cooperative_banner": "Sudha (COMFED) Payout: ₹36.00/L Base + ₹2.00/L State Milk Bonus = ₹38.00/L Cow Milk Rate",
        "incentive_scheme": "Bihar Rajya Dugdh Protsahan (₹2/L)",
        "govt_incentive": 2.0,
        "dairies": [
            {"dairy_name": "Sudha (COMFED Patna)", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 36.0, "fat_rate_factor": 4.1, "snf_rate_factor": 2.5, "govt_incentive": 2.0, "notes": "COMFED Sudha cooperative + ₹2/L state bonus"},
            {"dairy_name": "Sudha (COMFED Patna)", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 53.5, "fat_rate_factor": 5.5, "snf_rate_factor": 3.0, "govt_incentive": 2.0, "notes": "Sudha high-fat buffalo milk collection"},
        ],
        "recommended_breeds": ["Bachaur", "Sahiwal", "Murrah", "Diara Buffalo", "HF Cross"],
        "fodder_tip": "Middle Gangetic plains: Maize stover, Berseem, Oat grass, Paddy straw, Mustard oilcake, and Sudha Dan.",
        "cattle_market_note": "Sonepur Cattle Fair (Asia's largest), Bihta, Muzaffarpur cattle mandis. Bihar Vet Helpline: 1962.",
        "sire_options": ["Bachaur Preservation Semen", "Sahiwal Semen", "Murrah Buffalo Semen"],
        "seasonal_alerts": ["HS (गलघोंटू) post-flood vigilance", "FMD vaccination", "Foot rot care during floods"],
    },
    "West Bengal": {
        "cooperative_name": "Mother Dairy Calcutta / Benmilk",
        "cooperative_banner": "Benmilk & Mother Dairy Calcutta Benchmark: ₹36.00/L Cow Milk & ₹53.00/L Buffalo Milk",
        "incentive_scheme": "Paschim Banga Dairy Producer Support",
        "govt_incentive": 0.0,
        "dairies": [
            {"dairy_name": "Mother Dairy Calcutta", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 36.0, "fat_rate_factor": 4.1, "snf_rate_factor": 2.5, "govt_incentive": 0.0, "notes": "Kolkata & districts chilling center procurement"},
            {"dairy_name": "Benmilk (WBSCDF)", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 53.0, "fat_rate_factor": 5.4, "snf_rate_factor": 2.9, "govt_incentive": 0.0, "notes": "West Bengal state cooperative dairy federation"},
        ],
        "recommended_breeds": ["Siri", "Bengal Indigenous", "Sahiwal", "Murrah", "HF Cross"],
        "fodder_tip": "Deltaic plain: Hybrid Napier, Paddy straw, Mustard cake, Wheat bran, and mineral mixture.",
        "cattle_market_note": "Beldanga (Murshidabad), Panagarh, Siliguri cattle markets. WB Animal Resource Helpline: 1962.",
        "sire_options": ["Sahiwal Progeny Semen", "Jersey Cross Semen", "Murrah Semen"],
        "seasonal_alerts": ["FMD (খুরপাকা) vaccination", "HS & Liver fluke prevention in waterlogged fields"],
    },
}

# Generic fallback profile for any other Indian state/UT
DEFAULT_STATE_PROFILE: Dict[str, Any] = {
    "cooperative_name": "State Dairy Cooperative Federation",
    "cooperative_banner": "Regional Dairy Cooperative Benchmark: ₹37.00/L Base Cow Milk & ₹54.00/L Buffalo Milk",
    "incentive_scheme": "State Dairy Promotion Benchmark",
    "govt_incentive": 0.0,
    "dairies": [
        {"dairy_name": "State Cooperative Union", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 37.0, "fat_rate_factor": 4.2, "snf_rate_factor": 2.6, "govt_incentive": 0.0, "notes": "State dairy cooperative benchmark"},
        {"dairy_name": "State Cooperative Union", "milk_type": "Buffalo", "base_fat_pct": 6.0, "base_snf_pct": 9.0, "rate_per_litre": 54.0, "fat_rate_factor": 5.6, "snf_rate_factor": 3.0, "govt_incentive": 0.0, "notes": "State buffalo milk benchmark"},
        {"dairy_name": "National Dairy Network", "milk_type": "Cow", "base_fat_pct": 3.5, "base_snf_pct": 8.5, "rate_per_litre": 36.5, "fat_rate_factor": 4.1, "snf_rate_factor": 2.5, "govt_incentive": 0.0, "notes": "Chilled milk collection center"},
    ],
    "recommended_breeds": ["Gir", "Sahiwal", "Murrah", "HF Cross", "Jersey Cross"],
    "fodder_tip": "Balanced ration: 25-30 kg green fodder (Napier/Maize/Berseem), 5-7 kg dry straw, 3-5 kg cattle feed concentrate, and 50g mineral mixture daily.",
    "cattle_market_note": "District headquarters APMC and weekly cattle bazars. Pan-India Pashu Sanjeevini Helpline: 1962.",
    "sire_options": ["High Genetic Merit Sahiwal", "Murrah Semen Straws", "HF Cross Semen"],
    "seasonal_alerts": ["FMD biannual vaccination", "HS & BQ monsoonal alerts", "Seasonal heat stress management"],
}


# ============================================================================
# MULTILINGUAL DICTIONARY FOR DAIRY TERMS
# ============================================================================

DAIRY_I18N: Dict[str, Dict[str, str]] = {
    "optimal_climate": {
        "en": "Optimal Climate", "hi": "उत्कृष्ट जलवायु", "kn": "ಅತ್ಯುತ್ತಮ ವಾತಾವರಣ",
        "te": "అనుకూల వాతావరణం", "ta": "ஏற்ற காலநிலை", "mr": "अनुकूल हवामान",
        "ml": "അനുയോജ്യമായ കാലാവസ്ഥ", "bn": "অনুকূল আবহাওয়া", "gu": "શ્રેષ્ઠ આબોહવા", "pa": "ਅਨੁਕੂਲ ਮੌਸਮ"
    },
    "moderate_tolerance": {
        "en": "Moderate Tolerance", "hi": "मध्यम सहनशीलता", "kn": "ಮಧ್ಯಮ ಸಹಿಷ್ಣುತೆ",
        "te": "మధ్యస్థ సహనశీలత", "ta": "மிதமான தாங்கும் திறன்", "mr": "मध्यम सहनशीलता",
        "ml": "മിതമായ സഹിഷ്ണുത", "bn": "মাঝারি সহনশীলতা", "gu": "મધ્યમ સહિષ્ણુતા", "pa": "ਦਰਮਿਆਨੀ ਸਹਿਣਸ਼ੀਲਤਾ"
    },
    "heat_stress": {
        "en": "Caution: Heat Stress", "hi": "चेतावनी: अत्यधिक ताप तनाव", "kn": "ಎಚ್ಚರಿಕೆ: ತಾಪಮಾನದ ಒತ್ತಡ",
        "te": "హెచ్చరిక: వేడి ఒత్తిడి", "ta": "எச்சரிக்கை: வெப்ப அழுத்தம்", "mr": "सावधान: उष्णतेचा ताण",
        "ml": "മുന്നറിയിപ്പ്: ഉഷ്ണ സമ്മർദ്ദം", "bn": "সতর্কতা: তাপের চাপ", "gu": "ચેતવણી: ગરમીનો તણાવ", "pa": "ਚੇਤਾਵਨੀ: ਗਰਮੀ ਦਾ ਤਣਾਅ"
    },
    "cooling_standard": {
        "en": "Standard shelter and good ventilation are sufficient.",
        "hi": "मानक आश्रय और अच्छा वेंटिलेशन पर्याप्त है।",
        "kn": "ಸಾಮಾನ್ಯ ಕೊಟ್ಟಿಗೆ ಆಶ್ರಯ ಮತ್ತು ಉತ್ತಮ ಗಾಳಿ ಬೆಳಕು ಸಾಕು.",
        "te": "సాధారణ షెడ్డు మరియు మంచి గాలి ప్రసరణ సరిపోతుంది.",
        "ta": "சாதாரண கொட்டகை மற்றும் நல்ல காற்றோட்டம் போதுமானது.",
        "mr": "साधे गोठ्याचे छप्पर आणि उत्तम वायुवीजन पुरेसे आहे.",
        "ml": "സാധാരണ തൊഴുത്തും വായുസഞ്ചാരവും മതിയാകും.",
        "bn": "সাধারণ শেড ও বাতাস চলাচল যথেষ্ট।",
        "gu": "સામાન્ય ગમાણ અને યોગ્ય હવા-ઉજાસ પૂરતો છે.",
        "pa": "ਸਧਾਰਨ ਸ਼ੈੱਡ ਅਤੇ ਹਵਾਦਾਰ ਪ੍ਰਬੰਧ ਕਾਫ਼ੀ ਹਨ।"
    },
    "cooling_moderate": {
        "en": "Ensure evening bathing, adequate green fodder, and shaded loafing area.",
        "hi": "शाम को नहलाएं, पर्याप्त हरा चारा और छायादार स्थान सुनिश्चित करें।",
        "kn": "ಸಂಜೆ ಸ್ನಾನ ಮಾಡಿಸಿ, ಸಾಕಷ್ಟು ಹಸಿರು ಮೇವು ಮತ್ತು ನೆರಳಿನ ವ್ಯವಸ್ಥೆ ಒದಗಿಸಿ.",
        "te": "సాయంత్రం స్నానం చేయించండి, తగినంత పచ్చి గడ్డి మరియు నీడ అందించండి.",
        "ta": "மாலை குளிப்பாட்டவும், போதுமான பசுந்தீவனம் மற்றும் நிழல் தரவும்.",
        "mr": "संध्याकाळी आंघोळ घाला, मुबलक हिरवा चारा व सावली द्या.",
        "ml": "വൈകുന്നേരം കുളിപ്പിക്കുക, ആവശ്യത്തിന് പച്ചപ്പുല്ലും തണലും നൽകുക.",
        "bn": "সন্ধ্যায় স্নান করান, পর্যাপ্ত সবুজ ঘাস ও ছায়াযুক্ত স্থান দিন।",
        "gu": "સાંજે નવડાવો, પૂરતો લીલો ચારો અને છાંયડાની વ્યવસ્થા કરો.",
        "pa": "ਸ਼ਾਮ ਨੂੰ ਨੁਹਾਓ, ਕਾਫ਼ੀ ਹਰਾ ਚਾਰਾ ਅਤੇ ਛਾਂ ਦਾ ਪ੍ਰਬੰਧ ਕਰੋ।"
    },
    "cooling_stress": {
        "en": "High heat stress! Provide ceiling fans, water misting, shaded sheds, and cold drinking water.",
        "hi": "उच्च ताप तनाव! पंखे, पानी का छिड़काव, ठंडे पेयजल और छाया की व्यवस्था करें।",
        "kn": "ಅಧಿಕ ತಾಪಮಾನ! ಫ್ಯಾನ್, ನೀರಿನ ಸಿಂಪಡಣೆ, ತಂಪಾದ ನೀರು ಮತ್ತು ನೆರಳು ಒದಗಿಸಿ.",
        "te": "అధిక వేడి! ఫ్యాన్లు, నీటి తుంపర్లు, చల్లని నీరు మరియు మంచి నీడ కల్పించండి.",
        "ta": "அதிக வெப்ப அழுத்தம்! மின்விசிறி, தண்ணீர் தெளிப்பான், குளிர்ந்த நீர் வழங்கவும்.",
        "mr": "तीव्र उष्णता ताण! पंखे, पाण्याचे फवारे, थंड पाणी व सावलीची व्यवस्था करा.",
        "ml": "കടുത്ത ചൂട്! ഫാനുകൾ, വാട്ടർ സ്പ്രേ, തണുത്ത കുടിവെള്ളം, തണൽ നൽകുക.",
        "bn": "তীব্র গরমের চাপ! ফ্যান, জলের স্প্রে, ঠান্ডা পানীয় জল ও ছায়া দিন।",
        "gu": "તીવ્ર ગરમીનો તણાવ! પંખા, પાણીનો છંટકાવ, ઠંડુ પાણી અને છાંયડો આપો.",
        "pa": "ਵੱਧ ਗਰਮੀ ਦਾ ਤਣਾਅ! ਪੱਖੇ, ਪਾਣੀ ਦਾ ਛਿੜਕਾਅ, ਠੰਢਾ ਪਾਣੀ ਅਤੇ ਛਾਂ ਦਿਓ।"
    },
    "voice_prompt_template": {
        "en": "Tell me about care, high milk yield and disease prevention for {breed} cattle.",
        "hi": "{breed} गाय/भैंस के उचित पालन-पोषण, दूध उत्पादन और रोग रोकथाम की जानकारी दें।",
        "kn": "{breed} ಹಸು/ಎಮ್ಮೆ ಸಾಕಣೆ, ಅಧಿಕ ಹಾಲು ಉತ್ಪಾದನೆ ಮತ್ತು ರೋಗ ತಡೆಗಟ್ಟುವಿಕೆ ಬಗ್ಗೆ ತಿಳಿಸಿ.",
        "te": "{breed} ఆవు/గేదె పోషణ, పాల దిగుబడి మరియు వ్యాధి నివారణ వివరాలు తెలపండి.",
        "ta": "{breed} மாடு/எருமை வளர்ப்பு, பால் உற்பத்தி மற்றும் நோய் தடுப்பு முறை சொல்லுங்கள்.",
        "mr": "{breed} गाय/म्हैस पालन, दूध उत्पादन व रोग प्रतिबंधक उपायांची माहिती सांगा.",
        "ml": "{breed} പശു/എരുമ വളർത്തൽ, പാൽ ഉൽപ്പാദനം, രോഗപ്രതിരോധം എന്നിവയെക്കുറിച്ച് പറയുക.",
        "bn": "{breed} গরু/মহিষ পালন, দুধ উৎপাদন ও রোগ প্রতিরোধ সম্পর্কে বলুন।",
        "gu": "{breed} ગાય/ભેંસ પાલન, દૂધ ઉત્પાદન અને રોગ નિયંત્રણ વિશે જણાવો.",
        "pa": "{breed} ਗਾਂ/ਮੱਝ ਪਾਲਣ, ਦੁੱਧ ਉਤਪਾਦਨ ਅਤੇ ਬਿਮਾਰੀ ਰੋਕਥਾਮ ਬਾਰੇ ਦੱਸੋ।"
    },
}


def _t(key: str, lang: str, **kwargs) -> str:
    """Helper to fetch localized string with optional formatting."""
    d = DAIRY_I18N.get(key, {})
    tmpl = d.get(lang) or d.get("en") or key
    if kwargs:
        try:
            return tmpl.format(**kwargs)
        except Exception:
            return tmpl
    return tmpl


# ============================================================================
# REQUEST MODELS
# ============================================================================

class RateCalculateRequest(BaseModel):
    milk_type: str = "Cow"  # "Cow" or "Buffalo"
    fat_pct: float = 3.5
    snf_pct: float = 8.5
    quantity_litres: float = 10.0
    state: Optional[str] = None
    district: Optional[str] = None
    location_name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    language: Optional[str] = None


class VetDoctorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    doctor_type: str = Field(..., min_length=1, max_length=50)  # "Local Cow Doctor" or "Veterinary Doctor"
    specialization: Optional[str] = Field(None, max_length=200)
    phone: str = Field(..., min_length=3, max_length=50)
    location: str = Field(..., min_length=1, max_length=150)
    availability: Optional[str] = Field(None, max_length=150)
    emergency_available: bool = False

    @field_validator("name", "doctor_type", "phone", "location")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace")
        return cleaned


class VetDoctorOut(BaseModel):
    id: int
    name: str
    doctor_type: str
    specialization: Optional[str] = None
    phone: str
    location: str
    availability: Optional[str] = None
    emergency_available: bool

    class Config:
        from_attributes = True


class CattleListingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    breed: str = Field(..., min_length=1, max_length=100)
    animal_type: str = Field(..., min_length=1, max_length=30)  # "Cow", "Buffalo", "Heifer", "Calf"
    price_inr: float = Field(..., ge=0)
    milk_yield_liters_per_day: float = Field(0.0, ge=0)
    age_years: float = Field(0.0, ge=0)
    location: str = Field(..., min_length=1, max_length=150)
    owner_name: str = Field(..., min_length=1, max_length=150)
    owner_phone: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None

    @field_validator("title", "breed", "animal_type", "location", "owner_name", "owner_phone")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace")
        return cleaned


class CattleListingOut(BaseModel):
    id: int
    title: str
    breed: str
    animal_type: str
    price_inr: float
    milk_yield_liters_per_day: float
    age_years: float
    location: str
    owner_name: str
    owner_phone: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# LOCALIZATION & COMPACT ADVISORY HELPERS
# ============================================================================

STATE_NAMES_LOCALIZED: Dict[str, Dict[str, str]] = {
    "Madhya Pradesh": {"hi": "मध्य प्रदेश", "mr": "मध्य प्रदेश", "kn": "ಮಧ್ಯಪ್ರದೇಶ", "te": "మధ్యప్రదేశ్", "ta": "மத்தியப் பிரதேசம்"},
    "Karnataka": {"hi": "कर्नाटक", "mr": "कर्नाटक", "kn": "ಕರ್ನಾಟಕ", "te": "కర్ణాటక", "ta": "கர்நாடகா"},
    "Telangana": {"hi": "तेलंगाना", "mr": "तेलंगणा", "kn": "ತೆಲಂಗಾಣ", "te": "తెలంగాణ", "ta": "தெலங்கானா"},
    "Andhra Pradesh": {"hi": "आंध्र प्रदेश", "mr": "आंध्र प्रदेश", "kn": "ಆಂಧ್ರಪ್ರದೇಶ", "te": "ఆంధ్రప్రదేశ్", "ta": "ஆந்திரப் பிரதேசம்"},
    "Maharashtra": {"hi": "महाराष्ट्र", "mr": "महाराष्ट्र", "kn": "ಮಹಾರಾಷ್ಟ್ರ", "te": "ಮಹಾರಾಷ್ಟ್ರ", "ta": "மகாராஷ்டிரா"},
    "Gujarat": {"hi": "गुजरात", "mr": "गुजरात", "kn": "ગુજરાત", "te": "గుజరాత్", "ta": "குஜராத்"},
    "Punjab": {"hi": "पंजाब", "mr": "पंजाब", "kn": "ಪಂಜಾಬ್", "te": "పంజాబ్", "ta": "பஞ்சாப்"},
    "Haryana": {"hi": "हरियाणा", "mr": "हरियाणा", "kn": "ಹರಿಯಾಣ", "te": "హర్యానా", "ta": "ஹரியானா"},
    "Rajasthan": {"hi": "राजस्थान", "mr": "राजस्थान", "kn": "ರಾಜಸ್ಥಾನ", "te": "రాజస్థాన్", "ta": "ராஜஸ்தான்"},
    "Tamil Nadu": {"hi": "तमिलनाडु", "mr": "तमिळनाडू", "kn": "ತಮಿಳುನಾಡು", "te": "తమిళనాడు", "ta": "தமிழ்நாடு"},
    "Kerala": {"hi": "केरल", "mr": "केरळ", "kn": "ಕೇರಳ", "te": "కేరళ", "ta": "கேரளா"},
    "Uttar Pradesh": {"hi": "उत्तर प्रदेश", "mr": "उत्तर प्रदेश", "kn": "ಉತ್ತರ ಪ್ರದೇಶ", "te": "ఉత్తర ప్రదేశ್", "ta": "உத்தரப் பிரதேசம்"},
    "Bihar": {"hi": "बिहार", "mr": "बिहार", "kn": "ಬಿಹಾರ", "te": "బీహార్", "ta": "பீகார்"},
    "West Bengal": {"hi": "पश्चिम बंगाल", "mr": "पश्चिम बंगाल", "kn": "ಪಶ್ಚಿಮ ಬಂಗಾಳ", "te": "పశ్చిమ బెంగాల్", "ta": "மேற்கு வங்கம்"},
}

ADVISORY_TITLES: Dict[str, str] = {
    "en": "{state} Dairy & Livestock Advisory",
    "hi": "{state} पशुपालन एवं डेयरी परामर्श",
    "kn": "{state} ಪಶುಸಂಗೋಪನೆ ಮತ್ತು ಡೇರಿ ಸಲಹೆಗಾರ",
    "te": "{state} పశుసంవర్ಧక & డెయిరీ సలహాదారు",
    "ta": "{state} கால்நடை பராமரிப்பு மற்றும் பால்வள ஆலோசனை",
    "mr": "{state} पशुसंवर्धन आणि दुग्ध व्यवसाय सल्लागार",
}

ADVISORY_SUBTITLES: Dict[str, str] = {
    "en": "Milk rates, climate-suited breeds, balanced nutrition, sire selection, and veterinary alerts for {location}.",
    "hi": "{location} के लिए दूध दरें, अनुकूल नस्लें, संतुलित पोषण, सांड चयन एवं पशु स्वास्थ्य अलर्ट।",
    "kn": "{location}ಗಾಗಿ ಹಾಲು ಖರೀದಿ ದರಗಳು, ಸೂಕ್ತ ತಳಿಗಳು, ಪೌಷ್ಟಿಕ ಆಹಾರ, ತಳಿ ಸುಧಾರಣೆ ಮತ್ತು ಜಾನುವಾರು ಆರೋಗ್ಯ ಎಚ್ಚರಿಕೆಗಳು.",
    "te": "{location} కొరకు పాల ధరలు, అనుకూల జాతులు, సమతుల్య పోషణ, వీర్యం ఎంపిక మరియు ఆరోగ్య హెచ్చరికలు.",
    "ta": "{location}க்கான பால் கொள்முதல் விலை, தகுந்த இனங்கள், சமச்சீர் தீவனம் மற்றும் கால்நடை மருத்துவ எச்சரிக்கைகள்.",
    "mr": "{location} साठी दूध दर, अनुकूल जाती, संतुलित पोषण, वीर्य निवड आणि पशु आरोग्य सूचना.",
}


def _extract_milk_rates(profile: Dict[str, Any]) -> Dict[str, Any]:
    coop = profile.get("cooperative_name", "State Cooperative Federation")
    cow_rate = None
    buffalo_rate = None
    for d in profile.get("dairies", []):
        mtype = d.get("milk_type", "").lower()
        effective = round(d.get("rate_per_litre", 0.0) + d.get("govt_incentive", 0.0), 2)
        if "cow" in mtype and cow_rate is None:
            cow_rate = effective
        elif "buffalo" in mtype and buffalo_rate is None:
            buffalo_rate = effective
    return {
        "cooperative": coop,
        "cooperative_name": coop,
        "cow_rate": cow_rate or 38.0,
        "buffalo_rate": buffalo_rate or 55.0,
        "unit": "₹/L",
    }


# ============================================================================
# CORE DAIRY ENDPOINTS (STATE-AWARE & LOCALIZED)
# ============================================================================

@router.get("")
@router.get("/")
@router.get("/advisory")
def get_dairy_advisory(
    state: Optional[str] = Query(None, description="Target state"),
    location_name: Optional[str] = Query(None, description="Location name"),
    language: str = Query("en-IN", description="Language code"),
    district: Optional[str] = Query("", description="Target district"),
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
    temp_c: Optional[float] = Query(None, description="Ambient temperature"),
    db: Optional[Session] = Depends(get_db),
):
    """
    Compact state-specific Animal Husbandry & Dairy Advisory endpoint.
    Accepts state, location_name, and language.
    Infers state from location_name if omitted (Indore -> Madhya Pradesh, Hyderabad -> Telangana, Bengaluru -> Karnataka).
    Cached in SQLite by (state, language).
    """
    norm_st = _resolve_state(state, district, location_name, lat, lon)
    lang_code = language or "en-IN"
    lang_key = _norm_lang(lang_code)

    # Cache lookup by (state, language)
    cached = _cache_get("advisory", norm_st, lang_code)
    if cached:
        return cached

    profile = STATE_DAIRY_PROFILES.get(norm_st, DEFAULT_STATE_PROFILE)
    loc_display = location_name or district or norm_st
    loc_state = STATE_NAMES_LOCALIZED.get(norm_st, {}).get(lang_key, norm_st)

    title = ADVISORY_TITLES.get(lang_key, ADVISORY_TITLES["en"]).format(state=loc_state)
    subtitle = ADVISORY_SUBTITLES.get(lang_key, ADVISORY_SUBTITLES["en"]).format(location=loc_display)
    milk_rates_data = _extract_milk_rates(profile)

    result = {
        "title": title,
        "subtitle": subtitle,
        "state": norm_st,
        "location_name": loc_display,
        "language": lang_code,
        "breeds": profile.get("recommended_breeds", []),
        "milk_rates": milk_rates_data,
        "nutrition": profile.get("fodder_tip", ""),
        "sire_guide": profile.get("sire_options", []),
        "health_alerts": profile.get("seasonal_alerts", []),
        "cattle_markets": profile.get("cattle_market_note", ""),
        # Legacy compatibility aliases
        "cooperative_name": milk_rates_data["cooperative"],
        "cooperative_banner": profile.get("cooperative_banner"),
        "fodder_tip": profile.get("fodder_tip"),
        "cattle_market_note": profile.get("cattle_market_note"),
        "recommended_breeds": profile.get("recommended_breeds", []),
        "sire_options": profile.get("sire_options", []),
        "seasonal_alerts": profile.get("seasonal_alerts", []),
    }

    _cache_set("advisory", norm_st, lang_code, result)
    return result


@router.get("/procurement-rates")
@router.get("/milk-rates")
def get_procurement_rates(
    milk_type: Optional[str] = Query(None, description="Cow or Buffalo"),
    state: str = Query("Karnataka", description="Target state"),
    district: str = Query("", description="Target district"),
    location_name: str = Query("", description="Location name"),
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
    language: str = Query("en-IN", description="Language code"),
    db: Session = Depends(get_db),
):
    """
    Returns state-specific milk procurement rates across major cooperatives and private dairies.
    """
    norm_st = _resolve_state(state, district, location_name, lat, lon)
    norm_lg = _norm_lang(language)
    cached = _cache_get(f"rates:{milk_type or 'all'}", norm_st, norm_lg)
    if cached:
        return cached

    profile = STATE_DAIRY_PROFILES.get(norm_st, DEFAULT_STATE_PROFILE)
    res = []

    # If state profile has explicit dairies defined, use them
    if profile.get("dairies"):
        for idx, r in enumerate(profile["dairies"], start=1):
            if milk_type and milk_type.lower() not in r["milk_type"].lower():
                continue
            total_rate = round(r["rate_per_litre"] + r["govt_incentive"], 2)
            res.append({
                "id": 1000 + idx,
                "dairy_name": r["dairy_name"],
                "brand_logo": None,
                "slab_name": f"{norm_st} Standard",
                "milk_type": r["milk_type"],
                "base_fat_pct": r["base_fat_pct"],
                "base_snf_pct": r["base_snf_pct"],
                "base_rate_per_litre": r["rate_per_litre"],
                "fat_rate_factor": r["fat_rate_factor"],
                "snf_rate_factor": r["snf_rate_factor"],
                "govt_incentive": r["govt_incentive"],
                "total_effective_rate": total_rate,
                "notes": r["notes"],
            })
    else:
        # Fallback to database rates
        q = db.query(models.DairyProcurementRate)
        if milk_type:
            q = q.filter(models.DairyProcurementRate.milk_type.ilike(f"%{milk_type}%"))
        rates = q.all()
        for r in rates:
            total_rate = round(r.rate_per_litre + r.govt_incentive, 2)
            res.append({
                "id": r.id,
                "dairy_name": r.dairy_name,
                "brand_logo": r.brand_logo,
                "slab_name": r.slab_name,
                "milk_type": r.milk_type,
                "base_fat_pct": r.base_fat_pct,
                "base_snf_pct": r.base_snf_pct,
                "base_rate_per_litre": r.rate_per_litre,
                "fat_rate_factor": r.fat_rate_factor,
                "snf_rate_factor": r.snf_rate_factor,
                "govt_incentive": r.govt_incentive,
                "total_effective_rate": total_rate,
                "notes": r.notes,
            })

    _cache_set(f"rates:{milk_type or 'all'}", norm_st, norm_lg, res)
    return res


@router.post("/calculate-payout")
def calculate_milk_payout(req: RateCalculateRequest, db: Session = Depends(get_db)):
    """
    Interactive milk payout calculator.
    Computes payout per liter and total earnings based on Fat % and SNF %
    across all dairies for the active state.
    """
    norm_st = _resolve_state(req.state, req.district, req.location_name, req.lat, req.lon)
    profile = STATE_DAIRY_PROFILES.get(norm_st, DEFAULT_STATE_PROFILE)
    
    if profile.get("dairies"):
        rates_data = [r for r in profile["dairies"] if req.milk_type.lower() in r["milk_type"].lower()]
    else:
        db_rates = db.query(models.DairyProcurementRate).filter(
            models.DairyProcurementRate.milk_type.ilike(f"%{req.milk_type}%")
        ).all()
        rates_data = [
            {
                "dairy_name": r.dairy_name,
                "base_fat_pct": r.base_fat_pct,
                "base_snf_pct": r.base_snf_pct,
                "rate_per_litre": r.rate_per_litre,
                "fat_rate_factor": r.fat_rate_factor,
                "snf_rate_factor": r.snf_rate_factor,
                "govt_incentive": r.govt_incentive,
            }
            for r in db_rates
        ]

    comparison = []
    best_dairy = None
    max_payout = 0

    for r in rates_data:
        fat_diff = req.fat_pct - r["base_fat_pct"]
        snf_diff = req.snf_pct - r["base_snf_pct"]

        adjusted_base = r["rate_per_litre"] + (fat_diff * r["fat_rate_factor"]) + (snf_diff * r["snf_rate_factor"])
        adjusted_base = max(adjusted_base, 20.0)  # price floor

        effective_rate = round(adjusted_base + r["govt_incentive"], 2)
        total_amount = round(effective_rate * req.quantity_litres, 2)

        if total_amount > max_payout:
            max_payout = total_amount
            best_dairy = r["dairy_name"]

        comparison.append({
            "dairy_name": r["dairy_name"],
            "base_rate": r["rate_per_litre"],
            "fat_adjustment": round(fat_diff * r["fat_rate_factor"], 2),
            "snf_adjustment": round(snf_diff * r["snf_rate_factor"], 2),
            "govt_incentive": r["govt_incentive"],
            "rate_per_litre": effective_rate,
            "total_payout": total_amount,
            "is_highest": False,
        })

    for c in comparison:
        if c["dairy_name"] == best_dairy:
            c["is_highest"] = True

    return {
        "input": req.dict(),
        "state": norm_st,
        "best_dairy": best_dairy,
        "max_payout": max_payout,
        "results": comparison,
    }


@router.get("/breeds")
def get_breeds(
    temp_c: Optional[float] = Query(None, description="Ambient temperature in °C"),
    animal_type: Optional[str] = Query(None, description="Cow or Buffalo"),
    state: str = Query("Karnataka", description="Target state"),
    district: str = Query("", description="Target district"),
    location_name: str = Query("", description="Location name"),
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
    language: str = Query("en-IN", description="Language code"),
    db: Session = Depends(get_db),
):
    """
    Returns climate-matched cow and buffalo breeds tailored to the active state and temperature,
    localized in the requested language.
    """
    norm_st = _resolve_state(state, district, location_name, lat, lon)
    norm_lg = _norm_lang(language)
    current_temp = temp_c if temp_c is not None else 27.0

    profile = STATE_DAIRY_PROFILES.get(norm_st, DEFAULT_STATE_PROFILE)
    regional_breed_names = [rb.lower() for rb in profile.get("recommended_breeds", [])]

    q = db.query(models.LivestockBreed)
    if animal_type and animal_type.strip().lower() != "all":
        q = q.filter(models.LivestockBreed.animal_type.ilike(f"%{animal_type.strip()}%"))
    breeds = q.all()

    res = []
    for b in breeds:
        # Dynamic climate suitability calculation
        if current_temp > b.max_temp_c:
            suitability_en = "Caution: Heat Stress"
            suitability_score = "low"
            cooling_advice = _t("cooling_stress", norm_lg)
        elif b.min_temp_c <= current_temp <= (b.max_temp_c - 3):
            suitability_en = "Optimal Climate"
            suitability_score = "high"
            cooling_advice = _t("cooling_standard", norm_lg)
        else:
            suitability_en = "Moderate Tolerance"
            suitability_score = "medium"
            cooling_advice = _t("cooling_moderate", norm_lg)

        suitability_localized = (
            _t("optimal_climate", norm_lg) if suitability_score == "high"
            else _t("heat_stress", norm_lg) if suitability_score == "low"
            else _t("moderate_tolerance", norm_lg)
        )

        is_regional = any(rb in b.breed_name.lower() for rb in regional_breed_names)
        voice_query_text = _t("voice_prompt_template", norm_lg, breed=b.breed_name)

        res.append({
            "id": b.id,
            "breed_name": b.breed_name,
            "breed_localized": b.breed_kannada if norm_lg == "kn" else None,
            "animal_type": b.animal_type,
            "origin": b.origin,
            "avg_yield_litres": b.avg_yield_litres,
            "peak_yield_litres": b.peak_yield_litres,
            "fat_pct": b.fat_pct,
            "climate_zone": b.climate_zone,
            "heat_tolerance": b.heat_tolerance,
            "drought_resistance": b.drought_resistance,
            "disease_resistance": b.disease_resistance,
            "feeding_requirement": b.feeding_requirement,
            "description": b.description,
            "is_regional_recommended": is_regional,
            "recommended_state": norm_st if is_regional else None,
            "voice_query_text": voice_query_text,
            "weather_match": {
                "current_temp": current_temp,
                "suitability": suitability_en if norm_lg == "en" else suitability_localized,
                "suitability_score": suitability_score,
                "cooling_advice": cooling_advice,
            },
        })

    # Sort regional recommended breeds first, then by avg yield descending
    res.sort(key=lambda item: (not item["is_regional_recommended"], -item["avg_yield_litres"]))
    return res


@router.get("/feed-plans")
@router.get("/nutrition")
def get_feed_plans(
    animal_type: Optional[str] = Query(None, description="Cow or Buffalo"),
    stage: Optional[str] = Query(None, description="Dry or Lactating"),
    state: str = Query("Karnataka", description="Target state"),
    district: str = Query("", description="Target district"),
    location_name: str = Query("", description="Location name"),
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
    language: str = Query("en-IN", description="Language code"),
    db: Session = Depends(get_db),
):
    """
    Returns targeted daily rations enriched with region-specific green/dry fodder recommendations.
    """
    norm_st = _resolve_state(state, district, location_name, lat, lon)
    norm_lg = _norm_lang(language)
    profile = STATE_DAIRY_PROFILES.get(norm_st, DEFAULT_STATE_PROFILE)
    fodder_tip = profile.get("fodder_tip")

    q = db.query(models.FeedPlan)
    if animal_type and animal_type.strip().lower() != "all":
        q = q.filter(models.FeedPlan.animal_type.ilike(f"%{animal_type.strip()}%"))
    if stage and stage.strip().lower() != "all":
        q = q.filter(models.FeedPlan.stage.ilike(f"%{stage.strip()}%"))
    plans = q.all()

    res = []
    for p in plans:
        total_roughage = p.green_fodder_kg + p.dry_fodder_kg
        tips = f"{p.schedule_tips} | {fodder_tip}" if fodder_tip else p.schedule_tips
        res.append({
            "id": p.id,
            "plan_title": p.plan_title,
            "plan_title_localized": p.plan_title_kannada if norm_lg == "kn" else None,
            "animal_type": p.animal_type,
            "stage": p.stage,
            "state": norm_st,
            "body_weight_kg": p.body_weight_kg,
            "target_yield_litres": p.target_yield_litres,
            "green_fodder_kg": p.green_fodder_kg,
            "dry_fodder_kg": p.dry_fodder_kg,
            "concentrate_kg": p.concentrate_kg,
            "mineral_mixture_g": p.mineral_mixture_g,
            "bypass_fat_g": p.bypass_fat_g,
            "salt_g": p.salt_g,
            "water_litres": p.water_litres,
            "total_roughage_kg": total_roughage,
            "schedule_tips": tips,
            "regional_fodder_tip": fodder_tip,
        })
    return res


@router.get("/breeding-guide")
@router.get("/sire-guide")
def get_breeding_guide(
    dam_breed: Optional[str] = Query(None, description="Selected Cow or Buffalo breed"),
    state: str = Query("Karnataka", description="Target state"),
    language: str = Query("en-IN", description="Language code"),
    db: Session = Depends(get_db),
):
    """
    Breeding & Sire Semen Selection Guide.
    Matches mother cow/buffalo with AI bull semen suited to the active state.
    """
    norm_st = _resolve_state(state)
    norm_lg = _norm_lang(language)
    profile = STATE_DAIRY_PROFILES.get(norm_st, DEFAULT_STATE_PROFILE)
    regional_sires = profile.get("sire_options", [])

    q = db.query(models.SireGuide)
    if dam_breed and dam_breed.strip().lower() != "all":
        q = q.filter(models.SireGuide.dam_breed.ilike(f"%{dam_breed.strip()}%"))
    guides = q.all()

    res = []
    for g in guides:
        is_regional = any(rs.lower() in g.recommended_sire.lower() for rs in regional_sires)
        res.append({
            "id": g.id,
            "dam_breed": g.dam_breed,
            "dam_breed_localized": g.dam_breed_kannada if norm_lg == "kn" else None,
            "recommended_sire": g.recommended_sire,
            "recommended_sire_localized": g.recommended_sire_kannada if norm_lg == "kn" else None,
            "purpose": g.purpose,
            "expected_gain": g.expected_gain,
            "inbreeding_caution": g.inbreeding_caution,
            "veterinary_tip": g.veterinary_tip,
            "is_regional_match": is_regional,
            "target_state": norm_st,
        })

    # Sort regional matches first
    res.sort(key=lambda item: (not item["is_regional_match"], item["id"]))
    return res


@router.get("/disease-advisor")
@router.get("/health")
def get_disease_advisor(
    symptom: Optional[str] = Query(None, description="Search symptom keyword"),
    state: str = Query("Karnataka", description="Target state"),
    language: str = Query("en-IN", description="Language code"),
    db: Session = Depends(get_db),
):
    """
    Quick symptom and behavior variation advisor for livestock with state-specific alerts.
    """
    norm_st = _resolve_state(state)
    norm_lg = _norm_lang(language)
    profile = STATE_DAIRY_PROFILES.get(norm_st, DEFAULT_STATE_PROFILE)
    seasonal_alerts = profile.get("seasonal_alerts", [])

    q = db.query(models.LivestockDisease)
    if symptom and symptom.strip():
        term = symptom.strip()
        q = q.filter(
            (models.LivestockDisease.symptom_key.ilike(f"%{term}%")) |
            (models.LivestockDisease.symptom_display.ilike(f"%{term}%")) |
            (models.LivestockDisease.suspected_condition.ilike(f"%{term}%"))
        )
    diseases = q.all()

    res = []
    for d in diseases:
        res.append({
            "id": d.id,
            "symptom_key": d.symptom_key,
            "symptom_display": d.symptom_display,
            "symptom_localized": d.symptom_kannada if norm_lg == "kn" else None,
            "suspected_condition": d.suspected_condition,
            "suspected_localized": d.suspected_kannada if norm_lg == "kn" else None,
            "urgency_level": d.urgency_level,
            "immediate_first_aid": d.immediate_first_aid,
            "avoid_doing": d.avoid_doing,
            "recommended_query": d.recommended_query,
            "state_seasonal_alerts": seasonal_alerts,
        })
    return res


@router.get("/cattle-market")
def get_cattle_market_info(
    state: str = Query("Karnataka", description="Target state"),
    language: str = Query("en-IN", description="Language code"),
):
    """
    Returns state-specific cattle market information, major mandis, and trading guidelines.
    """
    norm_st = _resolve_state(state)
    profile = STATE_DAIRY_PROFILES.get(norm_st, DEFAULT_STATE_PROFILE)
    return {
        "state": norm_st,
        "cooperative_name": profile.get("cooperative_name"),
        "cattle_market_note": profile.get("cattle_market_note"),
        "recommended_breeds": profile.get("recommended_breeds", []),
        "helpline": "1962 (Pashu Sanjeevini Pan-India)",
    }


# ============================================================================
# VETERINARY DOCTORS & CATTLE MARKETPLACE LISTINGS
# ============================================================================

@router.get("/doctors", response_model=List[VetDoctorOut])
def get_vet_doctors(
    doctor_type: Optional[str] = Query(None, description="Local Cow Doctor or Veterinary Doctor"),
    search: Optional[str] = Query(None, description="Search by name, specialization, location, or phone"),
    db: Session = Depends(get_db),
):
    """Return local cow doctors and veterinary doctors, with optional filtering."""
    q = db.query(models.VetDoctor)

    if doctor_type and doctor_type.strip().lower() != "all":
        q = q.filter(models.VetDoctor.doctor_type.ilike(f"%{doctor_type.strip()}%"))

    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.filter(
            or_(
                models.VetDoctor.name.ilike(term),
                models.VetDoctor.specialization.ilike(term),
                models.VetDoctor.location.ilike(term),
                models.VetDoctor.phone.ilike(term),
            )
        )

    return q.order_by(models.VetDoctor.emergency_available.desc(), models.VetDoctor.id.desc()).all()


@router.post("/doctors", response_model=VetDoctorOut, status_code=201)
def create_vet_doctor(payload: VetDoctorCreate, db: Session = Depends(get_db)):
    """Add a new local cow doctor or veterinary doctor."""
    doctor = models.VetDoctor(
        name=payload.name,
        doctor_type=payload.doctor_type,
        specialization=payload.specialization.strip() if payload.specialization else None,
        phone=payload.phone,
        location=payload.location,
        availability=payload.availability.strip() if payload.availability else None,
        emergency_available=payload.emergency_available,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


_MULTI_STATE_CATTLE_SEED = [
    # Tamil Nadu (Coimbatore / Kongu & Delta)
    {"title": "Pure Kangayam Breeding Bull & Cow", "breed": "Kangayam", "animal_type": "Cow", "price_inr": 54000, "milk_yield_liters_per_day": 6.5, "age_years": 4.0, "location": "Kangayam, Coimbatore, Tamil Nadu", "owner_name": "Palanisamy Gounder", "owner_phone": "9842104455", "description": "Authentic Kongu Kangayam breed from Kangayam/Coimbatore belt, vaccinated."},
    {"title": "Bargur Native Cow (Erode / Coimbatore)", "breed": "Bargur", "animal_type": "Cow", "price_inr": 42000, "milk_yield_liters_per_day": 5.5, "age_years": 3.5, "location": "Erode, Coimbatore, Tamil Nadu", "owner_name": "Natarajan K", "owner_phone": "9842207788", "description": "Hardy Bargur hill-adapted cow, low maintenance and disease resistant."},
    {"title": "HF Cross High-Yield Dairy Cow (Pollachi)", "breed": "HF Cross", "animal_type": "Cow", "price_inr": 78000, "milk_yield_liters_per_day": 22.0, "age_years": 4.0, "location": "Pollachi, Coimbatore, Tamil Nadu", "owner_name": "Senthil Kumar", "owner_phone": "9842305566", "description": "22L/day peak yield HF Cross suited for Pollachi/Coimbatore dairy farms."},
    {"title": "Umblachery Dairy Cow (Thanjavur)", "breed": "Umblachery", "animal_type": "Cow", "price_inr": 44000, "milk_yield_liters_per_day": 7.0, "age_years": 3.5, "location": "Thanjavur, Tamil Nadu", "owner_name": "Muruganandam S", "owner_phone": "9842101122", "description": "Well-adapted coastal delta Umblachery cow, FMD vaccinated."},
    {"title": "Murrah High-Fat Buffalo (Salem)", "breed": "Murrah Buffalo", "animal_type": "Buffalo", "price_inr": 86000, "milk_yield_liters_per_day": 15.5, "age_years": 4.5, "location": "Salem, Tamil Nadu", "owner_name": "Karthikeyan R", "owner_phone": "9842203344", "description": "7.5% fat Murrah buffalo supplying to Aavin Salem."},
    # Madhya Pradesh
    {"title": "Malvi Dual-Purpose Cow (Indore)", "breed": "Malvi", "animal_type": "Cow", "price_inr": 48000, "milk_yield_liters_per_day": 8.0, "age_years": 4.0, "location": "Indore, Madhya Pradesh", "owner_name": "Ramesh Patidar", "owner_phone": "9826101122", "description": "Healthy Malvi cow from Malwa plateau, FMD vaccinated."},
    {"title": "Nimari & Gir Cross Milking Cow", "breed": "Gir", "animal_type": "Cow", "price_inr": 65000, "milk_yield_liters_per_day": 14.0, "age_years": 4.5, "location": "Ujjain, Madhya Pradesh", "owner_name": "Mahendra Singh", "owner_phone": "9826203344", "description": "14L/day A2 milk Gir cow with calf at foot."},
    # Telangana
    {"title": "Ongole & Murrah High-Fat Buffalo", "breed": "Murrah Buffalo", "animal_type": "Buffalo", "price_inr": 88000, "milk_yield_liters_per_day": 16.0, "age_years": 5.0, "location": "Hyderabad, Telangana", "owner_name": "Srinivas Reddy", "owner_phone": "9848101122", "description": "7.8% fat Murrah buffalo, Vijaya Dairy tested."},
    {"title": "Pure Ongole Cow with Bull Calf", "breed": "Ongole", "animal_type": "Cow", "price_inr": 58000, "milk_yield_liters_per_day": 9.5, "age_years": 4.0, "location": "Warangal, Telangana", "owner_name": "Venkatesh Rao", "owner_phone": "9848203344", "description": "Heat-tolerant Ongole cow from Warangal."},
    # Maharashtra
    {"title": "Khillari & Pandharpuri Buffalo", "breed": "Pandharpuri", "animal_type": "Buffalo", "price_inr": 82000, "milk_yield_liters_per_day": 13.5, "age_years": 4.5, "location": "Kolhapur, Maharashtra", "owner_name": "Shivaji Patil", "owner_phone": "9822101122", "description": "High-SNF Pandharpuri buffalo supplying to Gokul Dairy."},
    {"title": "Khillari Cow (Pune / Baramati)", "breed": "Khillari", "animal_type": "Cow", "price_inr": 49000, "milk_yield_liters_per_day": 7.5, "age_years": 4.0, "location": "Pune, Maharashtra", "owner_name": "Ajit Pawar", "owner_phone": "9822203344", "description": "Disease-resistant Khillari cow, dewormed."},
    # Gujarat
    {"title": "Pure Gir A2 Cow (Anand)", "breed": "Gir", "animal_type": "Cow", "price_inr": 78000, "milk_yield_liters_per_day": 16.5, "age_years": 4.0, "location": "Anand, Gujarat", "owner_name": "Bharat Patel", "owner_phone": "9825101122", "description": "Pedigree Gir cow with 16.5L/day A2 milk."},
    {"title": "Jaffarabadi Heavy Milking Buffalo", "breed": "Jaffarabadi", "animal_type": "Buffalo", "price_inr": 95000, "milk_yield_liters_per_day": 18.0, "age_years": 5.0, "location": "Rajkot, Gujarat", "owner_name": "Kishore Jadeja", "owner_phone": "9825203344", "description": "8.2% fat Jaffarabadi buffalo from Saurashtra."},
    # Punjab
    {"title": "Sahiwal Pedigree Cow (Ludhiana)", "breed": "Sahiwal", "animal_type": "Cow", "price_inr": 72000, "milk_yield_liters_per_day": 17.0, "age_years": 4.0, "location": "Ludhiana, Punjab", "owner_name": "Gurpreet Singh", "owner_phone": "9814101122", "description": "17L/day Sahiwal cow, Verka cooperative member."},
    {"title": "Nili-Ravi / Murrah Buffalo", "breed": "Murrah Buffalo", "animal_type": "Buffalo", "price_inr": 92000, "milk_yield_liters_per_day": 19.0, "age_years": 5.0, "location": "Ludhiana, Punjab", "owner_name": "Harjinder Gill", "owner_phone": "9814203344", "description": "19L/day Murrah buffalo, Khanna Mandi verified."},
]


def _ensure_multi_state_cattle(db: Session) -> None:
    existing_titles = {
        row[0] for row in db.query(models.CattleListing.title).all()
    }
    added = False
    for item in _MULTI_STATE_CATTLE_SEED:
        if item["title"] not in existing_titles:
            db.add(models.CattleListing(**item))
            added = True
    if added:
        db.commit()


@router.get("/cattle", response_model=List[CattleListingOut])
def get_cattle_listings(
    state: Optional[str] = Query(None, description="Target state"),
    district: Optional[str] = Query("", description="Target district"),
    location_name: Optional[str] = Query("", description="Location name"),
    breed: Optional[str] = Query(None, description="Filter by breed"),
    animal_type: Optional[str] = Query(None, description="Cow, Buffalo, Heifer, or Calf"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    sort_by: Optional[str] = Query(None, description="price_asc, price_desc, milk_desc, or newest"),
    db: Session = Depends(get_db),
):
    """Return state-aware cattle marketplace listings with optional breed/price filtering and sorting."""
    _ensure_multi_state_cattle(db)
    q = db.query(models.CattleListing)

    if breed and breed.strip().lower() != "all":
        q = q.filter(models.CattleListing.breed.ilike(f"%{breed.strip()}%"))

    if animal_type and animal_type.strip().lower() != "all":
        q = q.filter(models.CattleListing.animal_type.ilike(f"%{animal_type.strip()}%"))

    if min_price is not None:
        q = q.filter(models.CattleListing.price_inr >= min_price)

    if max_price is not None:
        q = q.filter(models.CattleListing.price_inr <= max_price)

    if sort_by == "price_asc":
        q = q.order_by(models.CattleListing.price_inr.asc())
    elif sort_by == "price_desc":
        q = q.order_by(models.CattleListing.price_inr.desc())
    elif sort_by == "milk_desc":
        q = q.order_by(models.CattleListing.milk_yield_liters_per_day.desc())
    else:
        q = q.order_by(models.CattleListing.created_at.desc(), models.CattleListing.id.desc())

    listings = q.all()

    if state or (location_name and location_name.strip()):
        norm_st = _resolve_state(state, district or "", location_name or "")
        state_cities = [
            city for city, st in CITY_STATE_LOOKUP.items() if st == norm_st
        ]
        loc_terms = [norm_st.lower()] + state_cities

        def _matches_state(item) -> bool:
            loc = (item.location or "").lower()
            return any(term in loc for term in loc_terms)

        filtered = [item for item in listings if _matches_state(item)]
        # Prioritize matching district / location_name first
        focus_terms = [t.strip().lower() for t in (district, location_name) if t and t.strip()]
        if focus_terms:
            filtered.sort(
                key=lambda item: not any(ft in (item.location or "").lower() for ft in focus_terms)
            )
        return filtered

    return listings


@router.post("/cattle", response_model=CattleListingOut, status_code=201)
def create_cattle_listing(payload: CattleListingCreate, db: Session = Depends(get_db)):
    """Create a new cattle marketplace listing."""
    listing = models.CattleListing(
        title=payload.title,
        breed=payload.breed,
        animal_type=payload.animal_type,
        price_inr=payload.price_inr,
        milk_yield_liters_per_day=payload.milk_yield_liters_per_day,
        age_years=payload.age_years,
        location=payload.location,
        owner_name=payload.owner_name,
        owner_phone=payload.owner_phone,
        description=payload.description.strip() if payload.description else None,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/cattle/{listing_id}")
def delete_cattle_listing(listing_id: int, db: Session = Depends(get_db)):
    """Delete a cattle marketplace listing by ID."""
    listing = db.query(models.CattleListing).filter(models.CattleListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Cattle listing not found")
    db.delete(listing)
    db.commit()
    return {"success": True, "deleted_id": listing_id}
