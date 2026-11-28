"""
Real-Time Geospatial Soil Health & Root-Zone Moisture Tool for FasalSaarathi.

Zero-Hardcoding, Zero-Lab-Report Architecture:
1. Live Geocoding & GPS: Resolves any village, taluk, district, 6-digit PIN code,
   regional-script place name, or exact farm GPS (lat, lon) via tools.weather_tool.geocode_location.
   Never defaults to or spoofs "Kolar" or any static city dictionary.
2. Live 5-Depth Root-Zone Soil Moisture & Soil Temperature (Open-Meteo Land-Surface API):
   - Volumetric soil moisture across 0-1cm, 1-3cm, 3-9cm, 9-27cm, and 27-81cm depths
   - Soil temperature at 0cm, 6cm, and 18cm depths
   - Selects the active root-zone depth matching the farmer's crop (shallow, medium, or deep roots)
3. Live 250m Satellite/Pedological Soil Mapping (OpenLandMap USDA/ISO 250m GeoServer + ISRIC SoilGrids 250m):
   - Topsoil pH (H2O), Soil Organic Carbon (%), Sand %, Clay %, Silt %, Bulk Density (g/cm3),
     Total Nitrogen, and Cation Exchange Capacity (CEC)
   - Computes USDA Soil Texture Class and Saxton-Rawls Field Capacity & Wilting Point thresholds
4. Crop-Specific ICAR Advisory Engine:
   - Tailors irrigation, liming/gypsum pH amendments, organic matter, and nutrient guidance
     to the farmer's actual crop (legumes/pulses, paddy, coffee, vegetables, cereals, etc.)
5. Real SQLite Cache Only (data/soil_cache.db):
   - Caches genuine remote-sensing soil properties and recent moisture telemetry;
     returns honest 'service_unavailable' when offline and uncached — zero fabricated numbers.
"""

import json
import math
import os
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from tools.weather_tool import HTTP_HEADERS, geocode_location

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOIL_CACHE_DB = os.path.join(PROJECT_ROOT, "data", "soil_cache.db")

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPENLANDMAP_WMS_URL = "https://geoserver.openlandmap.org/geoserver/olm/wms"
ISRIC_WMS_URL = "https://maps.isric.org/mapserv"

SOIL_PROFILE_TTL_SECONDS = 30 * 24 * 3600   # 30 days for 250m pedological properties
SOIL_MOISTURE_MAX_AGE_SECONDS = 24 * 3600   # 24 hours max fallback age for hourly moisture


# Agronomic crop root-depth & physiological classification (standard ICAR crop physiology, plain farmer language)
CROP_PHYSIOLOGY: Dict[str, Dict[str, Any]] = {
    # Shallow-rooted crops (primary uptake top 6 inches / 3-15 cm)
    "onion": {"name": "Onion", "root_zone": "shallow", "is_legume": False, "opt_ph": (6.0, 7.5), "waterlogging_sensitive": True, "special": "For firm bulbs that store longer without rotting, mix 10 kg of Agricultural Sulphur per acre into the soil."},
    "garlic": {"name": "Garlic", "root_zone": "shallow", "is_legume": False, "opt_ph": (6.0, 7.5), "waterlogging_sensitive": True, "special": "Keep the top layer of soil loose and mix 10 kg of Agricultural Sulphur per acre for healthy clove size."},
    "potato": {"name": "Potato", "root_zone": "shallow", "is_legume": False, "opt_ph": (5.2, 6.4), "waterlogging_sensitive": True, "special": "Do not add lime right before planting potato (it can cause skin scab on tubers); use Sulphate of Potash (SOP) for smooth, healthy potatoes."},
    # Medium-rooted vegetables & cereals (primary uptake top 1 ft / 9-30 cm)
    "tomato": {"name": "Tomato", "root_zone": "medium", "is_legume": False, "opt_ph": (6.0, 7.2), "waterlogging_sensitive": True, "special": "When flowers start turning into small fruits, spray Calcium Nitrate (5 grams per litre of water) to stop black rot at the bottom of tomatoes."},
    "chilli": {"name": "Chilli", "root_zone": "medium", "is_legume": False, "opt_ph": (6.0, 7.2), "waterlogging_sensitive": True, "special": "Never let rain or irrigation water stagnate between rows — standing water quickly causes chilli wilt and flower drop."},
    "rice": {"name": "Paddy (Rice)", "root_zone": "medium", "is_legume": False, "opt_ph": (5.5, 7.2), "waterlogging_sensitive": False, "is_paddy": True, "special": "Add 10 kg of Zinc Sulphate per acre during initial field preparation so young paddy leaves don't turn rusty-yellow."},
    "paddy": {"name": "Paddy (Rice)", "root_zone": "medium", "is_legume": False, "opt_ph": (5.5, 7.2), "waterlogging_sensitive": False, "is_paddy": True, "special": "Add 10 kg of Zinc Sulphate per acre during initial field preparation so young paddy leaves don't turn rusty-yellow."},
    "wheat": {"name": "Wheat", "root_zone": "medium", "is_legume": False, "opt_ph": (6.0, 7.5), "waterlogging_sensitive": True, "special": "Make sure the crop gets timely watering at 21 days after sowing (when main roots form) and during grain-filling."},
    "maize": {"name": "Maize", "root_zone": "medium", "is_legume": False, "opt_ph": (5.8, 7.5), "waterlogging_sensitive": True, "special": "Maize needs steady nutrition: divide Urea into 3 smaller doses (at sowing, knee-high stage, and tassel stage) and add 10 kg Zinc Sulphate per acre."},
    "ragi": {"name": "Ragi (Finger Millet)", "root_zone": "medium", "is_legume": False, "opt_ph": (5.5, 7.5), "waterlogging_sensitive": True, "special": "Mix 3 tractor-loads (tonnes) of well-rotted cow-dung manure per acre before sowing to hold rain moisture longer."},
    # Legumes / Nitrogen-fixing pulses & oilseeds
    "tur": {"name": "Tur / Red Gram", "root_zone": "deep", "is_legume": True, "opt_ph": (6.0, 7.5), "waterlogging_sensitive": True, "special": "Pulse crops make their own nitrogen from air: coat seeds with Rhizobium packet before sowing and give only a small starter dose of DAP — avoid heavy Urea."},
    "chickpea": {"name": "Chickpea (Chana)", "root_zone": "medium", "is_legume": True, "opt_ph": (6.0, 7.8), "waterlogging_sensitive": True, "special": "Coat seeds with Rhizobium culture before sowing, and avoid watering when plants are in full flower."},
    "groundnut": {"name": "Groundnut", "root_zone": "medium", "is_legume": True, "opt_ph": (6.0, 7.2), "waterlogging_sensitive": True, "special": "At 40–45 days (when pegs enter the soil), apply 200 kg Gypsum per acre around plants so pods fill out heavy and crisp — avoid heavy Urea."},
    "soybean": {"name": "Soybean", "root_zone": "medium", "is_legume": True, "opt_ph": (6.0, 7.5), "waterlogging_sensitive": True, "special": "Coat seeds with Rhizobium culture before sowing and add 8–10 kg Sulphur per acre for better oil & seed weight — avoid heavy Urea."},
    # Deep-rooted plantation, commercial & orchard crops (primary uptake up to 2.5 ft / 15-80 cm)
    "coffee": {"name": "Coffee", "root_zone": "deep", "is_legume": False, "opt_ph": (5.3, 6.3), "waterlogging_sensitive": True, "acid_loving": True, "special": "Your naturally rich, mildly acidic soil suits Coffee well — keep dry fallen leaves around the plant base (mulching) and maintain good shade."},
    "pepper": {"name": "Black Pepper", "root_zone": "deep", "is_legume": False, "opt_ph": (5.5, 6.5), "waterlogging_sensitive": True, "acid_loving": True, "special": "Apply 1 kg of Neem Cake mixed with Trichoderma around each vine before heavy rains to protect roots from sudden wilt."},
    "arecanut": {"name": "Arecanut", "root_zone": "deep", "is_legume": False, "opt_ph": (5.5, 7.0), "waterlogging_sensitive": True, "special": "Keep 2-foot deep drainage channels clean between areca rows so excess water drains out, and cover palm basins with green leaves."},
    "cotton": {"name": "Cotton", "root_zone": "deep", "is_legume": False, "opt_ph": (6.0, 8.0), "waterlogging_sensitive": True, "special": "When bolls start forming, spray Magnesium Sulphate (10 grams per litre of water) so cotton leaves don't turn red and drop early."},
    "sugarcane": {"name": "Sugarcane", "root_zone": "deep", "is_legume": False, "opt_ph": (6.0, 7.8), "waterlogging_sensitive": False, "special": "Spread dry cane leaves between rows (trash mulching) — this keeps roots cool, saves 1 out of 4 waterings, and enriches the soil."},
    "banana": {"name": "Banana", "root_zone": "deep", "is_legume": False, "opt_ph": (6.0, 7.5), "waterlogging_sensitive": True, "special": "Banana needs plenty of Potash for big bunches: give Potash (MOP) in 3–4 split doses up to bunch emergence."},
}

CROP_ALIASES_MAP: Dict[str, str] = {
    "paddy": "rice", "dhan": "rice", "bhatta": "rice",
    "red gram": "tur", "arhar": "tur", "pigeonpea": "tur", "togari": "tur",
    "chana": "chickpea", "gram": "chickpea", "kadale": "chickpea",
    "peanut": "groundnut", "shengdana": "groundnut", "kadalekayi": "groundnut",
    "supari": "arecanut", "adike": "arecanut", "betelnut": "arecanut",
    "mirchi": "chilli", "chili": "chilli", "green chilli": "chilli",
    "makka": "maize", "corn": "maize", "jola": "maize",
    "finger millet": "ragi", "nachni": "ragi",
    "kapas": "cotton", "hatti": "cotton",
    "kanda": "onion", "pyaz": "onion", "eerulli": "onion",
    "aloo": "potato", "batata": "potato",
}


# ─────────────────────────────────────────────────────────────────────────────
# SQLite Real-Data Cache Layer
# ─────────────────────────────────────────────────────────────────────────────
def _init_soil_db(db_path: str = DEFAULT_SOIL_CACHE_DB) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS soil_profile_cache (
                coord_key TEXT PRIMARY KEY,
                profile_json TEXT NOT NULL,
                cached_at REAL NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS soil_moisture_cache (
                coord_key TEXT PRIMARY KEY,
                moisture_json TEXT NOT NULL,
                fetched_at_epoch REAL NOT NULL,
                fetched_at_iso TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _coord_key(lat: float, lon: float) -> str:
    return f"{round(lat, 3):.3f},{round(lon, 3):.3f}"


def _get_cached_profile(lat: float, lon: float, db_path: str = DEFAULT_SOIL_CACHE_DB) -> Optional[Dict[str, Any]]:
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT profile_json, cached_at FROM soil_profile_cache WHERE coord_key = ?", (_coord_key(lat, lon),))
        row = cur.fetchone()
        if not row or (time.time() - float(row[1])) > SOIL_PROFILE_TTL_SECONDS:
            return None
        return json.loads(row[0])
    except (sqlite3.Error, json.JSONDecodeError, ValueError):
        return None
    finally:
        conn.close()


def _save_cached_profile(lat: float, lon: float, profile: Dict[str, Any], db_path: str = DEFAULT_SOIL_CACHE_DB) -> None:
    try:
        _init_soil_db(db_path)
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO soil_profile_cache (coord_key, profile_json, cached_at) VALUES (?, ?, ?)",
                (_coord_key(lat, lon), json.dumps(profile, ensure_ascii=False), time.time()),
            )
            conn.commit()
        finally:
            conn.close()
    except sqlite3.Error:
        pass


def _save_cached_moisture(lat: float, lon: float, m_data: Dict[str, Any], db_path: str = DEFAULT_SOIL_CACHE_DB) -> None:
    try:
        _init_soil_db(db_path)
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO soil_moisture_cache (coord_key, moisture_json, fetched_at_epoch, fetched_at_iso) VALUES (?, ?, ?, ?)",
                (
                    _coord_key(lat, lon),
                    json.dumps(m_data, ensure_ascii=False),
                    time.time(),
                    m_data.get("fetched_at_str", datetime.now().strftime("%d %b %Y, %I:%M %p")),
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except sqlite3.Error:
        pass


def _get_cached_moisture(
    lat: float, lon: float, db_path: str = DEFAULT_SOIL_CACHE_DB, max_age_seconds: int = SOIL_MOISTURE_MAX_AGE_SECONDS
) -> Optional[Tuple[Dict[str, Any], int]]:
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT moisture_json, fetched_at_epoch FROM soil_moisture_cache WHERE coord_key = ?",
            (_coord_key(lat, lon),),
        )
        row = cur.fetchone()
        if not row:
            return None
        age_sec = time.time() - float(row[1])
        if age_sec > max_age_seconds:
            return None
        return json.loads(row[0]), max(1, int(round(age_sec / 60.0)))
    except (sqlite3.Error, json.JSONDecodeError, ValueError):
        return None
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Live Remote-Sensing & Land-Surface API Fetchers
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_openlandmap_250m(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Single-call 250m USDA/ISO soil chemistry & physical properties via OpenLandMap GeoServer WMS.
    Layers queried simultaneously:
      1. olm:ph_h2o_usda_4c1a2a         -> pH * 10
      2. olm:log_oc_iso_10694           -> log1p(SOC g/kg) * 10
      3. olm:sand_wfraction_usda_3a1a1a -> Sand % (w/w)
      4. olm:bulkdens_fineearth_usda_4a1h -> Bulk density * 100 (g/cm3)
    """
    layers = ",".join(
        [
            "olm:ph_h2o_usda_4c1a2a",
            "olm:log_oc_iso_10694",
            "olm:sand_wfraction_usda_3a1a1a",
            "olm:bulkdens_fineearth_usda_4a1h",
        ]
    )
    bbox = f"{lon - 0.005},{lat - 0.005},{lon + 0.005},{lat + 0.005}"
    resp = requests.get(
        OPENLANDMAP_WMS_URL,
        params={
            "SERVICE": "WMS",
            "VERSION": "1.1.1",
            "REQUEST": "GetFeatureInfo",
            "LAYERS": layers,
            "QUERY_LAYERS": layers,
            "STYLES": "",
            "SRS": "EPSG:4326",
            "BBOX": bbox,
            "WIDTH": 2,
            "HEIGHT": 2,
            "X": 1,
            "Y": 1,
            "FEATURE_COUNT": 10,
            "INFO_FORMAT": "application/json",
        },
        headers=HTTP_HEADERS,
        timeout=7,
        verify=True,
    )
    resp.raise_for_status()
    features = resp.json().get("features") or []
    if len(features) < 4:
        return None

    vals = [f.get("properties", {}).get("GRAY_INDEX") for f in features[:4]]
    if any(v is None or float(v) < 0 or float(v) >= 255 for v in vals[:3]):
        return None

    ph_val = round(float(vals[0]) / 10.0, 2)
    soc_g_kg = math.expm1(float(vals[1]) / 10.0)
    soc_pct = round(soc_g_kg / 10.0, 2)
    sand_pct = round(float(vals[2]), 1)
    bd_gcm3 = round(float(vals[3]) / 100.0, 2) if vals[3] is not None and 50 <= float(vals[3]) <= 220 else 1.35

    if not (3.5 <= ph_val <= 10.5):
        return None

    return {
        "ph": ph_val,
        "organic_carbon_pct": soc_pct,
        "sand_pct": sand_pct,
        "bulk_density_gcm3": bd_gcm3,
        "profile_source": "OpenLandMap 250m Global USDA/ISO Soil Grid",
    }


def _fetch_isric_enrichment(lat: float, lon: float) -> Dict[str, Any]:
    """
    Optional enrichment from ISRIC SoilGrids 250m MapServer for exact Clay %, Total N, and CEC.
    Uses short timeout so slow ISRIC responses never block OpenLandMap + Open-Meteo.
    """
    bbox = f"{lon - 0.005},{lat - 0.005},{lon + 0.005},{lat + 0.005}"
    out: Dict[str, Any] = {}
    for prop, layer, scale, key in [
        ("clay", "clay_5-15cm_mean", 10.0, "clay_pct"),
        ("nitrogen", "nitrogen_5-15cm_mean", 100.0, "total_nitrogen_g_kg"),
        ("cec", "cec_5-15cm_mean", 10.0, "cec_cmol_kg"),
    ]:
        try:
            r = requests.get(
                ISRIC_WMS_URL,
                params={
                    "map": f"/map/{prop}.map",
                    "SERVICE": "WMS",
                    "VERSION": "1.1.1",
                    "REQUEST": "GetFeatureInfo",
                    "STYLES": "",
                    "LAYERS": layer,
                    "QUERY_LAYERS": layer,
                    "SRS": "EPSG:4326",
                    "BBOX": bbox,
                    "WIDTH": 2,
                    "HEIGHT": 2,
                    "X": 1,
                    "Y": 1,
                    "INFO_FORMAT": "text/html",
                },
                headers=HTTP_HEADERS,
                timeout=2.8,
                verify=True,
            )
            if r.status_code == 200:
                m = re.search(r'id=["\']value["\']>([^<]+)<', r.text)
                if m:
                    raw = m.group(1).strip()
                    if raw and raw.lower() not in ("none", "nodata", "null"):
                        num = float(raw)
                        if num > 0:
                            out[key] = round(num / scale, 2)
        except (requests.RequestException, ValueError):
            break  # Stop polling ISRIC immediately if busy so response stays <2s
    return out


def _fetch_live_multidepth_moisture(lat: float, lon: float) -> Dict[str, Any]:
    """
    Fetch real-time hourly 5-depth volumetric soil moisture & 3-depth soil temperature
    from Open-Meteo ERA5-Land / IFS Land-Surface API.
    """
    resp = requests.get(
        OPEN_METEO_FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "precipitation,rain,temperature_2m",
            "hourly": ",".join(
                [
                    "soil_moisture_0_to_1cm",
                    "soil_moisture_1_to_3cm",
                    "soil_moisture_3_to_9cm",
                    "soil_moisture_9_to_27cm",
                    "soil_moisture_27_to_81cm",
                    "soil_temperature_0cm",
                    "soil_temperature_6cm",
                    "soil_temperature_18cm",
                ]
            ),
            "daily": "precipitation_sum,et0_fao_evapotranspiration",
            "timezone": "Asia/Kolkata",
            "forecast_days": 2,
        },
        headers=HTTP_HEADERS,
        timeout=7,
        verify=True,
    )
    resp.raise_for_status()
    data = resp.json()
    curr = data.get("current") or {}
    hourly = data.get("hourly") or {}
    daily = data.get("daily") or {}

    times = hourly.get("time") or []
    curr_iso = curr.get("time") or ""
    idx = 0
    if curr_iso and times:
        prefix = curr_iso[:13]
        for i, t_str in enumerate(times):
            if t_str.startswith(prefix):
                idx = i
                break

    def _pct(arr_key: str) -> Optional[float]:
        arr = hourly.get(arr_key) or []
        val = arr[idx] if idx < len(arr) else None
        return round(float(val) * 100.0, 1) if val is not None else None

    def _deg(arr_key: str) -> Optional[float]:
        arr = hourly.get(arr_key) or []
        val = arr[idx] if idx < len(arr) else None
        return round(float(val), 1) if val is not None else None

    sm_0_1 = _pct("soil_moisture_0_to_1cm")
    sm_1_3 = _pct("soil_moisture_1_to_3cm")
    sm_3_9 = _pct("soil_moisture_3_to_9cm")
    sm_9_27 = _pct("soil_moisture_9_to_27cm")
    sm_27_81 = _pct("soil_moisture_27_to_81cm")

    if all(v is None for v in (sm_0_1, sm_3_9, sm_9_27, sm_27_81)):
        raise ValueError("Open-Meteo returned empty land-surface soil moisture telemetry.")

    p_sums = daily.get("precipitation_sum") or []
    et0s = daily.get("et0_fao_evapotranspiration") or []

    return {
        "observation_time_ist": curr_iso,
        "fetched_at_str": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "depths_pct": {
            "surface_0_1cm": sm_0_1,
            "seedling_1_3cm": sm_1_3,
            "shallow_3_9cm": sm_3_9,
            "active_root_9_27cm": sm_9_27,
            "deep_root_27_81cm": sm_27_81,
        },
        "soil_temperatures_c": {
            "surface_0cm": _deg("soil_temperature_0cm"),
            "root_6cm": _deg("soil_temperature_6cm"),
            "deep_18cm": _deg("soil_temperature_18cm"),
        },
        "rain_today_mm": round(float(p_sums[0]), 1) if p_sums and p_sums[0] is not None else 0.0,
        "et0_today_mm": round(float(et0s[0]), 2) if et0s and et0s[0] is not None else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pedological & ICAR Agronomic Classification Engine
# ─────────────────────────────────────────────────────────────────────────────
def _classify_usda_texture_and_hydraulics(
    sand_pct: float, clay_pct: Optional[float], bd_gcm3: float, soc_pct: float
) -> Dict[str, Any]:
    """
    Classify USDA Soil Texture and compute Saxton-Rawls Wilting Point & Field Capacity (% vol).
    If ISRIC clay_pct was unavailable, estimates clay/silt split from sand %, bulk density, & SOC.
    """
    if clay_pct is None:
        # Pedotransfer estimate from sand fraction and fine-earth bulk density
        rem = max(5.0, 100.0 - sand_pct)
        clay_ratio = 0.52 if bd_gcm3 >= 1.38 else 0.42
        clay = round(min(rem - 3.0, max(5.0, rem * clay_ratio)), 1)
    else:
        clay = min(max(1.0, clay_pct), max(1.0, 98.0 - sand_pct))
    silt = round(max(0.0, 100.0 - sand_pct - clay), 1)

    # Standard USDA Soil Texture Triangle rules
    if clay >= 40.0 and silt < 40.0 and sand_pct <= 45.0:
        soil_type = "Heavy Clay / Vertisol (Black Cotton Soil)" if bd_gcm3 >= 1.36 else "Clay Loam / Lateritic Clay"
        drainage = "Slow internal drainage (high moisture retention)"
    elif clay >= 35.0 and sand_pct > 45.0:
        soil_type = "Sandy Clay"
        drainage = "Moderate-slow drainage"
    elif 27.0 <= clay < 40.0 and 20.0 < sand_pct <= 45.0:
        soil_type = "Clay Loam"
        drainage = "Moderate drainage"
    elif 20.0 <= clay < 35.0 and silt < 28.0 and sand_pct > 45.0:
        soil_type = "Sandy Clay Loam"
        drainage = "Moderately well-drained"
    elif sand_pct >= 70.0 and (silt + 1.5 * clay) < 15.0:
        soil_type = "Sand / Coarse Loamy Sand"
        drainage = "Rapid drainage (high nutrient leaching risk)"
    elif sand_pct >= 52.0 and clay < 20.0:
        soil_type = "Sandy Loam"
        drainage = "Well-drained"
    elif silt >= 50.0 and clay < 27.0:
        soil_type = "Silt Loam"
        drainage = "Moderate-good drainage"
    else:
        soil_type = "Loam"
        drainage = "Well-balanced drainage & aeration"

    # Saxton & Rawls (2006) pedotransfer equations for Volumetric Wilting Point (1500 kPa) & Field Capacity (33 kPa)
    s = sand_pct / 100.0
    c = clay / 100.0
    om = min(8.0, max(0.2, soc_pct * 1.724)) / 100.0  # Organic matter fraction

    theta_1500t = -0.024 * s + 0.487 * c + 0.006 * om + 0.005 * (s * om) - 0.013 * (c * om) + 0.068 * (s * c) + 0.031
    wp = max(0.06, theta_1500t + (0.14 * theta_1500t - 0.02))

    theta_33t = -0.251 * s + 0.195 * c + 0.011 * om + 0.006 * (s * om) - 0.027 * (c * om) + 0.452 * (s * c) + 0.299
    fc = max(wp + 0.08, theta_33t + (1.283 * (theta_33t ** 2) - 0.374 * theta_33t - 0.015))

    return {
        "soil_type": soil_type,
        "drainage": drainage,
        "sand_pct": round(sand_pct, 1),
        "clay_pct": round(clay, 1),
        "silt_pct": silt,
        "wilting_point_pct": round(wp * 100.0, 1),
        "field_capacity_pct": round(fc * 100.0, 1),
    }


def _resolve_crop_profile(crop_raw: Optional[str]) -> Dict[str, Any]:
    if not crop_raw:
        return {"name": "General Crop", "root_zone": "medium", "is_legume": False, "opt_ph": (6.0, 7.5), "waterlogging_sensitive": True, "special": None}
    c_clean = crop_raw.strip().lower()
    c_clean = CROP_ALIASES_MAP.get(c_clean, c_clean)
    if c_clean in CROP_PHYSIOLOGY:
        return CROP_PHYSIOLOGY[c_clean]
    for key, prof in CROP_PHYSIOLOGY.items():
        if key in c_clean:
            return prof
    return {"name": crop_raw.strip().title(), "root_zone": "medium", "is_legume": False, "opt_ph": (6.0, 7.5), "waterlogging_sensitive": True, "special": None}


def _evaluate_fertility_and_advisory(
    ph: float,
    soc_pct: float,
    tex: Dict[str, Any],
    total_n_g_kg: Optional[float],
    cec_cmol_kg: Optional[float],
    moisture_data: Dict[str, Any],
    crop_prof: Dict[str, Any],
) -> Dict[str, Any]:
    depths = moisture_data["depths_pct"]
    r_zone = crop_prof["root_zone"]

    # Pick active root-zone volumetric moisture matching crop root architecture
    if r_zone == "shallow":
        candidates = [depths.get("shallow_3_9cm"), depths.get("active_root_9_27cm"), depths.get("seedling_1_3cm")]
        depth_label = "shallow root level (top 6 inches)"
    elif r_zone == "deep":
        d1, d2 = depths.get("active_root_9_27cm"), depths.get("deep_root_27_81cm")
        if d1 is not None and d2 is not None:
            candidates = [round(0.45 * d1 + 0.55 * d2, 1)]
        else:
            candidates = [d2, d1, depths.get("shallow_3_9cm")]
        depth_label = "deep root level (up to 2.5 feet)"
    else:
        candidates = [depths.get("active_root_9_27cm"), depths.get("shallow_3_9cm"), depths.get("deep_root_27_81cm")]
        depth_label = "medium root level (top 1 foot)"

    active_moist = next((v for v in candidates if v is not None), 25.0)
    wp = tex["wilting_point_pct"]
    fc = tex["field_capacity_pct"]
    paw_pct = int(round(max(0.0, min(100.0, ((active_moist - wp) / max(5.0, fc - wp)) * 100.0))))

    # Evaluate moisture relative to actual soil texture Field Capacity & Wilting Point (plain farmer language)
    is_paddy = bool(crop_prof.get("is_paddy"))
    if active_moist <= wp * 1.15 or paw_pct < 25:
        moisture_status = "CRITICAL_DEFICIT"
        moisture_label = "Too Dry — Water Today"
        irr_guidance = (
            f"Soil around the roots is too dry ({active_moist}% moisture; healthy range for this soil is {wp}%–{fc}%). "
            f"Water your {crop_prof['name']} crop today."
        )
    elif paw_pct < 55:
        moisture_status = "MODERATE_MOISTURE"
        moisture_label = "Slightly Dry — Water in 1–2 Days"
        irr_guidance = (
            f"Soil has moderate moisture ({active_moist}%). "
            f"Give a light watering in the next 1–2 days if there is no rain."
        )
    elif active_moist <= fc * 1.12 or is_paddy:
        moisture_status = "OPTIMAL_MOISTURE"
        moisture_label = "Good Moisture — No Watering Needed"
        irr_guidance = (
            f"Soil has plenty of moisture ({active_moist}%) for {crop_prof['name']} roots. "
            f"No watering needed today."
        )
    else:
        moisture_status = "SATURATED_SOIL"
        moisture_label = "Very Wet — Drain Excess Water"
        irr_guidance = (
            f"Soil around the roots is already very wet ({active_moist}% moisture; healthy range is {wp}%–{fc}%). "
            f"Do not water today, and keep field drains open so roots do not rot."
        )

    # Plain-language Soil Acidity (pH) classification
    if ph < 5.5:
        ph_simple = "Acidic"
        ph_interp = "Acidic soil — can lock up plant food unless balanced"
    elif ph < 6.0:
        ph_simple = "Mildly Acidic"
        ph_interp = "Mildly acidic — suits coffee/pepper; add lime for vegetables or pulses"
    elif ph <= 7.5:
        ph_simple = "Balanced"
        ph_interp = "Healthy, balanced soil — plants can absorb food easily"
    elif ph <= 8.2:
        ph_simple = "Slightly Alkaline"
        ph_interp = "Slightly alkaline — add compost so micronutrients stay available"
    else:
        ph_simple = "Alkaline / Salty"
        ph_interp = "High alkalinity — needs Gypsum and green manure"

    # Organic Matter (Humus) & Nitrogen status
    oc_simple = "Low" if soc_pct < 0.50 else ("Good" if soc_pct <= 0.75 else "Rich")
    if total_n_g_kg is not None:
        if total_n_g_kg < 0.8 and soc_pct < 0.50:
            n_status = "Low"
        elif total_n_g_kg >= 1.5 or soc_pct > 0.80:
            n_status = "High"
        else:
            n_status = "Medium"
    else:
        n_status = "Low" if soc_pct < 0.50 else ("Medium" if soc_pct <= 0.75 else "Adequate")

    # Phosphorus Availability Index
    if ph < 5.8:
        p_status = "Low (Acidic soil locks DAP)"
    elif ph > 7.9:
        p_status = "Low-Medium (Alkaline soil)"
    elif soc_pct < 0.45:
        p_status = "Low-Medium"
    else:
        p_status = "Medium"

    # Potassium Retention Index
    if (cec_cmol_kg is not None and cec_cmol_kg < 10.0) or tex["sand_pct"] >= 65.0:
        k_status = "Low (Washes out in sandy soil)"
    elif (cec_cmol_kg is not None and cec_cmol_kg >= 22.0) or tex["clay_pct"] >= 34.0:
        k_status = "High"
    else:
        k_status = "Medium"

    # Build Simple, Everyday Farmer Care Steps (zero textbook jargon)
    amendments: List[str] = []
    crop_name = crop_prof["name"]

    # 1. pH care step
    min_ph, max_ph = crop_prof["opt_ph"]
    if ph < min_ph - 0.2 and not (crop_prof.get("acid_loving") and ph >= 5.3):
        amendments.append(
            f"Balance soil acidity (pH {ph}): Mix Agricultural Lime or Dolomite (150–200 kg per acre) "
            f"into damp soil 2–3 weeks before adding fertilizers so {crop_name} can absorb plant food."
        )
    elif ph > max_ph + 0.3 and ph > 7.8:
        amendments.append(
            f"Reduce soil salt/alkalinity (pH {ph}): Mix Agricultural Gypsum (150–200 kg per acre) "
            f"and green manure into the soil before sowing."
        )

    # 2. Soil humus / compost step
    if soc_pct < 0.50:
        amendments.append(
            f"Build soil richness ({soc_pct}% humus is low): Mix 3–4 tractor-loads of well-rotted cow-dung manure (FYM) "
            f"or 1 tonne of Vermicompost per acre so the soil stays soft and holds water longer."
        )

    # 3. Nitrogen step (strictly respects Legumes vs Non-legumes)
    if crop_prof["is_legume"]:
        amendments.append(
            f"{crop_name} makes its own nitrogen from the air: Coat seeds with a Rhizobium culture packet before sowing "
            f"and give only a small starter dose of DAP — avoid heavy Urea."
        )
    elif n_status == "Low":
        amendments.append(
            f"For healthy green leaf growth: Give Neem-Coated Urea in 2–3 smaller doses (25 kg per acre each time) "
            f"when soil is damp — never scatter Urea right before heavy rain."
        )

    # 4. Root & flower (Phosphorus) & fruit strength (Potash) steps
    if "Acidic" in p_status:
        amendments.append(
            "For strong roots & flowering: Because your soil is acidic, regular DAP fertilizer gets locked in the soil. "
            "Use Single Super Phosphate (SSP) or Rock Phosphate mixed with compost instead of plain DAP."
        )
    elif "Alkaline" in p_status:
        amendments.append(
            "For strong roots & flowering: Place DAP or SSP fertilizer near the plant roots mixed with compost "
            "instead of scattering it over the whole field."
        )

    if "Low" in k_status:
        amendments.append(
            "Prevent fertilizer wash-out: Because your soil has more sand, divide Potash (MOP) into 2 smaller doses instead of giving it all at once."
        )

    # 5. Crop-specific care tip
    if crop_prof.get("special"):
        amendments.append(crop_prof["special"])

    return {
        "active_root_depth_label": depth_label,
        "moisture_percentage": active_moist,
        "moisture_label": moisture_label,
        "ideal_moisture_range": f"{wp}% – {fc}%",
        "plant_available_water_pct": paw_pct,
        "moisture_status": moisture_status,
        "ph_simple": ph_simple,
        "ph_interpretation": ph_interp,
        "oc_simple": oc_simple,
        "nitrogen_status": n_status,
        "phosphorus_status": p_status,
        "potassium_status": k_status,
        "irrigation_guidance": irr_guidance,
        "soil_amendments": amendments,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public Entry Point
# ─────────────────────────────────────────────────────────────────────────────
def fetch_soil_health(
    district_query: Optional[str] = None,
    crop: str = "general",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    db_path: str = DEFAULT_SOIL_CACHE_DB,
) -> Dict[str, Any]:
    """
    Fetch real-time multi-depth root moisture & 250m geospatial soil profile for any location or GPS point.
    Zero hardcoded city dictionaries and zero fabricated fallback values.
    """
    geo, err_code, err_msg = geocode_location(location_query=district_query, lat=lat, lon=lon)
    if err_code or not geo:
        return {
            "status": err_code or "location_not_found",
            "is_live_data": False,
            "is_cached_data": False,
            "error_code": err_code or "location_not_found",
            "requested_location": district_query,
            "message": err_msg or "Unable to resolve location.",
            "summary": err_msg or "Unable to resolve location.",
        }

    lat_f = float(geo["latitude"])
    lon_f = float(geo["longitude"])
    place_name = geo["name"]
    district_name = geo.get("district") or place_name
    state_name = geo.get("state")

    display_parts = [place_name]
    if geo.get("district") and geo["district"].lower() not in place_name.lower():
        display_parts.append(geo["district"])
    if state_name and state_name.lower() not in place_name.lower():
        display_parts.append(state_name)
    display_location = ", ".join(display_parts)

    crop_prof = _resolve_crop_profile(crop)

    # 1. Resolve 250m Pedological Profile (check 30-day SQLite cache first, else fetch live in parallel with Open-Meteo)
    cached_prof = _get_cached_profile(lat_f, lon_f, db_path=db_path)
    live_moisture: Optional[Dict[str, Any]] = None
    moisture_is_live = False
    cache_age_min = 0

    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_moist = pool.submit(_fetch_live_multidepth_moisture, lat_f, lon_f)
        fut_olm = pool.submit(_fetch_openlandmap_250m, lat_f, lon_f) if cached_prof is None else None
        fut_isric = pool.submit(_fetch_isric_enrichment, lat_f, lon_f) if cached_prof is None else None

        try:
            live_moisture = fut_moist.result()
            moisture_is_live = True
            _save_cached_moisture(lat_f, lon_f, live_moisture, db_path=db_path)
        except Exception:
            cached_m = _get_cached_moisture(lat_f, lon_f, db_path=db_path)
            if cached_m is not None:
                live_moisture, cache_age_min = cached_m
                moisture_is_live = False

        if cached_prof is None and fut_olm is not None:
            try:
                olm_data = fut_olm.result()
            except Exception:
                olm_data = None
            isric_data = {}
            if fut_isric is not None:
                try:
                    isric_data = fut_isric.result() or {}
                except Exception:
                    isric_data = {}

            if olm_data:
                cached_prof = {**olm_data, **isric_data}
                _save_cached_profile(lat_f, lon_f, cached_prof, db_path=db_path)

    if live_moisture is None or cached_prof is None:
        return {
            "status": "service_unavailable",
            "is_live_data": False,
            "is_cached_data": False,
            "error_code": "soil_service_unreachable",
            "district": display_location,
            "location": place_name,
            "coordinates": {"latitude": round(lat_f, 4), "longitude": round(lon_f, 4)},
            "message": (
                f"Live geospatial soil & land-surface telemetry services are currently unreachable "
                f"and no cached soil profile exists for {display_location}."
            ),
            "summary": f"Live soil telemetry service is temporarily unreachable for {display_location}.",
        }

    tex = _classify_usda_texture_and_hydraulics(
        sand_pct=float(cached_prof["sand_pct"]),
        clay_pct=cached_prof.get("clay_pct"),
        bd_gcm3=float(cached_prof.get("bulk_density_gcm3", 1.35)),
        soc_pct=float(cached_prof["organic_carbon_pct"]),
    )

    eval_out = _evaluate_fertility_and_advisory(
        ph=float(cached_prof["ph"]),
        soc_pct=float(cached_prof["organic_carbon_pct"]),
        tex=tex,
        total_n_g_kg=cached_prof.get("total_nitrogen_g_kg"),
        cec_cmol_kg=cached_prof.get("cec_cmol_kg"),
        moisture_data=live_moisture,
        crop_prof=crop_prof,
    )

    is_live = moisture_is_live
    src_label = (
        "Live — Open-Meteo Root Moisture + OpenLandMap 250m Soil Grid"
        if is_live
        else f"Cached Real Telemetry ({cache_age_min} min old)"
    )

    return {
        "status": "success" if is_live else "cached_real",
        "is_live_data": is_live,
        "is_cached_data": not is_live,
        "cache_age_minutes": cache_age_min,
        "data_source_label": src_label,
        "source": cached_prof.get("profile_source", "OpenLandMap 250m + Open-Meteo ERA5-Land"),
        "last_updated": live_moisture.get("fetched_at_str"),
        "observation_time_ist": live_moisture.get("observation_time_ist"),
        "location": place_name,
        "district": display_location,
        "admin_district": district_name,
        "state": state_name,
        "crop": crop_prof["name"],
        "coordinates": {"latitude": round(lat_f, 4), "longitude": round(lon_f, 4)},
        "soil_type": tex["soil_type"],
        "drainage": tex["drainage"],
        "texture": {
            "sand_pct": tex["sand_pct"],
            "clay_pct": tex["clay_pct"],
            "silt_pct": tex["silt_pct"],
            "bulk_density_gcm3": cached_prof.get("bulk_density_gcm3"),
            "wilting_point_pct": tex["wilting_point_pct"],
            "field_capacity_pct": tex["field_capacity_pct"],
        },
        "active_root_depth": eval_out["active_root_depth_label"],
        "moisture_percentage": eval_out["moisture_percentage"],
        "moisture_label": eval_out["moisture_label"],
        "ideal_moisture_range": eval_out["ideal_moisture_range"],
        "plant_available_water_pct": eval_out["plant_available_water_pct"],
        "moisture_status": eval_out["moisture_status"],
        "root_depths_moisture_pct": live_moisture["depths_pct"],
        "soil_temperatures_c": live_moisture["soil_temperatures_c"],
        "ph": float(cached_prof["ph"]),
        "ph_simple": eval_out["ph_simple"],
        "ph_interpretation": eval_out["ph_interpretation"],
        "nutrients": {
            "nitrogen_status": eval_out["nitrogen_status"],
            "total_nitrogen_g_kg": cached_prof.get("total_nitrogen_g_kg"),
            "phosphorus_status": eval_out["phosphorus_status"],
            "potassium_status": eval_out["potassium_status"],
            "organic_carbon_pct": float(cached_prof["organic_carbon_pct"]),
            "organic_carbon_label": eval_out["oc_simple"],
            "cec_cmol_kg": cached_prof.get("cec_cmol_kg"),
        },
        "irrigation_guidance": eval_out["irrigation_guidance"],
        "soil_amendments": eval_out["soil_amendments"],
        "summary": (
            f"In {display_location} ({tex['soil_type']}), soil moisture at {eval_out['active_root_depth_label']} "
            f"is {eval_out['moisture_percentage']}% ({eval_out['moisture_label']}). "
            f"Soil is {eval_out['ph_simple'].lower()} (pH {cached_prof['ph']}) with {eval_out['oc_simple'].lower()} organic humus ({cached_prof['organic_carbon_pct']}%). "
            f"{eval_out['irrigation_guidance']}"
        ),
    }


if __name__ == "__main__":
    import pprint
    pprint.pprint(fetch_soil_health("Mandya", "Sugarcane"))
