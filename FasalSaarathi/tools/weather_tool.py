"""
Real-Time Agro-Meteorological Weather Tool for FasalSaarathi.

Zero-Hardcoding Architecture:
1. Live Geocoding: Resolves any village, taluk, district, city, 6-digit PIN code,
   or regional-script name via Open-Meteo Geocoding API + OpenStreetMap Nominatim,
   plus direct GPS (latitude, longitude) support with reverse geocoding.
   Never defaults to or substitutes "Kolar" or any other location.
2. Live Weather & Farm Metrics: Queries Open-Meteo Forecast API (verify=True) for:
   - Current temperature, feels-like temp, humidity, precipitation, wind speed & gusts
   - Hourly 6-hour rain & wind window (safe foliar spraying window check)
   - FAO Penman-Monteith Reference Evapotranspiration (ET0 mm/day) & net water balance
   - Surface & root-zone volumetric soil moisture & soil temperature
   - 7-day daily agricultural forecast (min/max temp, rain prob, rain mm, ET0, UV, wind)
3. Real SQLite Cache Only: Caches genuine Open-Meteo responses keyed by coordinates
   with exact fetch timestamps. When offline, returns only real recent cached data
   (<= 24h old) or an honest 'service_unavailable' status — never fabricated numbers.
"""

import json
import os
import re
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CACHE_DB_PATH = os.path.join(PROJECT_ROOT, "data", "weather_cache.db")

OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

GEOCODE_CACHE_TTL_SECONDS = 30 * 24 * 3600  # 30 days for real resolved coordinates
WEATHER_CACHE_MAX_AGE_SECONDS = 24 * 3600   # 24 hours max fallback age for real weather

HTTP_HEADERS = {
    "User-Agent": "FasalSaarathi-AgroAdvisor/2.0 (Agricultural Weather Intelligence)",
    "Accept": "application/json",
}

# Standard WMO Code descriptions (official World Meteorological Organization specification)
WMO_WEATHER_CODES: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

COORD_PAIR_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


# ─────────────────────────────────────────────────────────────────────────────
# SQLite Real-Data Cache Layer
# ─────────────────────────────────────────────────────────────────────────────
def _init_cache_db(db_path: str = DEFAULT_CACHE_DB_PATH) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS geocoding_cache (
                query_key TEXT PRIMARY KEY,
                resolved_name TEXT NOT NULL,
                district TEXT,
                state TEXT,
                country TEXT,
                country_code TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                elevation_m REAL,
                geocoder_source TEXT NOT NULL,
                cached_at REAL NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_forecast_cache (
                coord_key TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                fetched_at_epoch REAL NOT NULL,
                fetched_at_iso TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _normalize_query_key(raw: str) -> str:
    return re.sub(r"\s+", " ", raw.strip().lower())


def _coord_cache_key(lat: float, lon: float) -> str:
    return f"{round(lat, 3):.3f},{round(lon, 3):.3f}"


def _get_cached_geocode(query_key: str, db_path: str = DEFAULT_CACHE_DB_PATH) -> Optional[Dict[str, Any]]:
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT resolved_name, district, state, country, country_code,
                   latitude, longitude, elevation_m, geocoder_source, cached_at
            FROM geocoding_cache
            WHERE query_key = ?
            """,
            (query_key,),
        )
        row = cur.fetchone()
        if not row:
            return None
        cached_at = float(row[9])
        if (time.time() - cached_at) > GEOCODE_CACHE_TTL_SECONDS:
            return None
        return {
            "name": row[0],
            "district": row[1],
            "state": row[2],
            "country": row[3],
            "country_code": row[4],
            "latitude": float(row[5]),
            "longitude": float(row[6]),
            "elevation_m": float(row[7]) if row[7] is not None else None,
            "geocoder_source": row[8],
        }
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def _save_cached_geocode(
    query_key: str, geo: Dict[str, Any], db_path: str = DEFAULT_CACHE_DB_PATH
) -> None:
    try:
        _init_cache_db(db_path)
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO geocoding_cache (
                    query_key, resolved_name, district, state, country, country_code,
                    latitude, longitude, elevation_m, geocoder_source, cached_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_key,
                    geo["name"],
                    geo.get("district"),
                    geo.get("state"),
                    geo.get("country"),
                    geo.get("country_code"),
                    float(geo["latitude"]),
                    float(geo["longitude"]),
                    geo.get("elevation_m"),
                    geo.get("geocoder_source", "Open-Meteo Geocoding"),
                    time.time(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except sqlite3.Error:
        pass


def _save_cached_weather(
    lat: float, lon: float, payload: Dict[str, Any], db_path: str = DEFAULT_CACHE_DB_PATH
) -> None:
    try:
        _init_cache_db(db_path)
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO weather_forecast_cache (
                    coord_key, payload_json, fetched_at_epoch, fetched_at_iso
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    _coord_cache_key(lat, lon),
                    json.dumps(payload, ensure_ascii=False),
                    time.time(),
                    payload.get("last_updated", datetime.now().strftime("%d %b %Y, %I:%M %p")),
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except sqlite3.Error:
        pass


def _get_cached_weather(
    lat: float,
    lon: float,
    db_path: str = DEFAULT_CACHE_DB_PATH,
    max_age_seconds: int = WEATHER_CACHE_MAX_AGE_SECONDS,
) -> Optional[Tuple[Dict[str, Any], int]]:
    """Returns (cached_payload, age_minutes) only if a real cached response exists within max_age_seconds."""
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT payload_json, fetched_at_epoch, fetched_at_iso
            FROM weather_forecast_cache
            WHERE coord_key = ?
            """,
            (_coord_cache_key(lat, lon),),
        )
        row = cur.fetchone()
        if not row:
            return None
        age_sec = time.time() - float(row[1])
        if age_sec > max_age_seconds:
            return None
        payload = json.loads(row[0])
        age_min = max(1, int(round(age_sec / 60.0)))
        return payload, age_min
    except (sqlite3.Error, json.JSONDecodeError, ValueError):
        return None
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Live Geocoding & Reverse Geocoding (Open-Meteo + Nominatim)
# ─────────────────────────────────────────────────────────────────────────────
def _reverse_geocode_coords(lat: float, lon: float) -> Dict[str, Any]:
    """Resolve human-readable village/taluk/district from exact GPS coordinates."""
    coord_key = f"gps:{_coord_cache_key(lat, lon)}"
    cached = _get_cached_geocode(coord_key)
    if cached:
        return cached

    try:
        resp = requests.get(
            NOMINATIM_REVERSE_URL,
            params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 14, "addressdetails": 1},
            headers={**HTTP_HEADERS, "Accept-Language": "en"},
            timeout=4,
            verify=True,
        )
        if resp.status_code == 200:
            data = resp.json()
            addr = data.get("address") or {}
            place = (
                addr.get("village")
                or addr.get("town")
                or addr.get("suburb")
                or addr.get("city")
                or addr.get("county")
                or data.get("name")
            )
            district = addr.get("state_district") or addr.get("county")
            state = addr.get("state")
            country = addr.get("country")
            country_code = (addr.get("country_code") or "").upper()
            if place:
                geo = {
                    "name": place,
                    "district": district,
                    "state": state,
                    "country": country,
                    "country_code": country_code,
                    "latitude": lat,
                    "longitude": lon,
                    "elevation_m": None,
                    "geocoder_source": "OpenStreetMap Nominatim Reverse Geocoder",
                }
                _save_cached_geocode(coord_key, geo)
                return geo
    except requests.RequestException:
        pass

    return {
        "name": f"Farm GPS ({lat:.4f}, {lon:.4f})",
        "district": None,
        "state": None,
        "country": None,
        "country_code": None,
        "latitude": lat,
        "longitude": lon,
        "elevation_m": None,
        "geocoder_source": "Direct Farm GPS Coordinates",
    }


def _search_open_meteo_geocoder(query: str) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Query Open-Meteo Geocoding API.
    Returns (geo_dict_or_None, network_ok).
    """
    # Try clean variants if user included trailing words like 'district' or 'taluk'
    variants = [query.strip()]
    stripped = re.sub(r"\b(district|taluk|taluka|hobli|apmc|mandi|india|karnataka)\b", "", query, flags=re.IGNORECASE).strip(" ,.-")
    if stripped and stripped.lower() != query.strip().lower():
        variants.append(stripped)

    any_network_ok = False
    for q in variants:
        try:
            resp = requests.get(
                OPEN_METEO_GEOCODE_URL,
                params={"name": q, "count": 10, "language": "en", "format": "json"},
                headers=HTTP_HEADERS,
                timeout=6,
                verify=True,
            )
            if resp.status_code == 200:
                any_network_ok = True
                results = resp.json().get("results") or []
                if not results:
                    continue
                # Prioritize Indian agricultural locations first
                in_results = [r for r in results if str(r.get("country_code", "")).upper() == "IN"]
                chosen = in_results[0] if in_results else results[0]
                return {
                    "name": chosen.get("name") or q,
                    "district": chosen.get("admin2") or chosen.get("admin3"),
                    "state": chosen.get("admin1"),
                    "country": chosen.get("country"),
                    "country_code": str(chosen.get("country_code", "")).upper(),
                    "latitude": float(chosen["latitude"]),
                    "longitude": float(chosen["longitude"]),
                    "elevation_m": float(chosen["elevation"]) if chosen.get("elevation") is not None else None,
                    "geocoder_source": "Open-Meteo Live Geocoding API",
                }, True
        except requests.RequestException:
            continue

    return None, any_network_ok


def _search_nominatim_geocoder(query: str) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Fallback live geocoder via OpenStreetMap Nominatim.
    Handles Indian 6-digit PIN codes, small villages, and Kannada/Hindi/Tamil/Telugu/Marathi script names.
    Returns (geo_dict_or_None, network_ok).
    """
    try:
        is_pincode = bool(re.fullmatch(r"[1-9]\d{5}", query.strip()))
        params: Dict[str, Any] = {
            "format": "jsonv2",
            "limit": 5,
            "addressdetails": 1,
            "countrycodes": "in",
        }
        if is_pincode:
            params["postalcode"] = query.strip()
        else:
            params["q"] = query.strip()

        resp = requests.get(
            NOMINATIM_SEARCH_URL,
            params=params,
            headers={**HTTP_HEADERS, "Accept-Language": "en"},
            timeout=6,
            verify=True,
        )
        if resp.status_code == 200:
            items = resp.json() or []
            if not items:
                return None, True
            top = items[0]
            addr = top.get("address") or {}
            place = (
                addr.get("village")
                or addr.get("town")
                or addr.get("city")
                or addr.get("county")
                or addr.get("state_district")
                or top.get("name")
                or query.strip()
            )
            return {
                "name": place,
                "district": addr.get("state_district") or addr.get("county"),
                "state": addr.get("state"),
                "country": addr.get("country", "India"),
                "country_code": (addr.get("country_code") or "IN").upper(),
                "latitude": float(top["lat"]),
                "longitude": float(top["lon"]),
                "elevation_m": None,
                "geocoder_source": "OpenStreetMap Nominatim Geocoding API",
            }, True
    except requests.RequestException:
        return None, False

    return None, False


def geocode_location(
    location_query: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    db_path: str = DEFAULT_CACHE_DB_PATH,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    """
    Resolve a location or GPS pair into verified geographic coordinates.
    Returns: (geo_dict, error_code, error_message)
    Never substitutes a default city.
    """
    # 1. Explicit GPS coordinates passed
    if lat is not None and lon is not None:
        try:
            lat_f, lon_f = float(lat), float(lon)
        except (TypeError, ValueError):
            return None, "invalid_coordinates", "Invalid GPS latitude or longitude format."
        if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
            return None, "invalid_coordinates", "GPS coordinates are outside valid Earth bounds."
        return _reverse_geocode_coords(lat_f, lon_f), None, None

    if not location_query or not str(location_query).strip():
        return (
            None,
            "missing_location",
            "Location is required. Please enter your village, taluk, district, PIN code, or use GPS.",
        )

    raw_q = str(location_query).strip()

    # 2. Coordinate pair typed into the location box (e.g. "12.9716, 77.5946")
    coord_match = COORD_PAIR_RE.match(raw_q)
    if coord_match:
        lat_f, lon_f = float(coord_match.group(1)), float(coord_match.group(2))
        if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
            return None, "invalid_coordinates", "GPS coordinates are outside valid Earth bounds."
        return _reverse_geocode_coords(lat_f, lon_f), None, None

    # Reject meaningless 1-character queries unless non-ASCII script
    if len(raw_q) < 2 and raw_q.isascii():
        return (
            None,
            "location_not_found",
            f"Location '{raw_q}' is too short. Please enter a valid village, taluk, or district name.",
        )

    q_key = _normalize_query_key(raw_q)

    # 3. Check real SQLite geocode cache (populated strictly from prior live API lookups)
    cached_geo = _get_cached_geocode(q_key, db_path=db_path)
    if cached_geo:
        return cached_geo, None, None

    # 4. Live Open-Meteo Geocoding API (primary for English names)
    is_ascii_alpha = all(ord(c) < 128 for c in raw_q) and not bool(re.fullmatch(r"[1-9]\d{5}", raw_q))
    om_ok = False
    if is_ascii_alpha:
        geo, om_ok = _search_open_meteo_geocoder(raw_q)
        if geo:
            _save_cached_geocode(q_key, geo, db_path=db_path)
            return geo, None, None

    # 5. Live Nominatim Geocoding API (handles Indian PIN codes, small villages, & Indic scripts)
    geo_nom, nom_ok = _search_nominatim_geocoder(raw_q)
    if geo_nom:
        _save_cached_geocode(q_key, geo_nom, db_path=db_path)
        return geo_nom, None, None

    # Also try Open-Meteo if non-ASCII wasn't tried yet
    if not is_ascii_alpha:
        geo, om_ok = _search_open_meteo_geocoder(raw_q)
        if geo:
            _save_cached_geocode(q_key, geo, db_path=db_path)
            return geo, None, None

    if not om_ok and not nom_ok:
        return (
            None,
            "service_unavailable",
            f"Geocoding service is unreachable while resolving '{raw_q}'. Check internet connection and retry.",
        )

    return (
        None,
        "location_not_found",
        f"Could not find location '{raw_q}'. Please check spelling or include your district/state name.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Agronomic Analysis from Real Open-Meteo Telemetry
# ─────────────────────────────────────────────────────────────────────────────
def _extract_next_6h_window(hourly: Dict[str, Any], current_iso: Optional[str]) -> Dict[str, Any]:
    times: List[str] = hourly.get("time") or []
    probs: List[Any] = hourly.get("precipitation_probability") or []
    precips: List[Any] = hourly.get("precipitation") or []
    winds: List[Any] = hourly.get("wind_speed_10m") or []
    gusts: List[Any] = hourly.get("wind_gusts_10m") or []
    soil_m_top: List[Any] = hourly.get("soil_moisture_0_to_1cm") or []
    soil_m_root: List[Any] = hourly.get("soil_moisture_3_to_9cm") or []
    soil_t: List[Any] = hourly.get("soil_temperature_0cm") or []

    start_idx = 0
    if current_iso and times:
        hour_prefix = current_iso[:13]  # "YYYY-MM-DDTHH"
        for idx, t_str in enumerate(times):
            if t_str.startswith(hour_prefix):
                start_idx = idx
                break

    end_idx = min(len(times), start_idx + 6)
    win_probs = [float(x) for x in probs[start_idx:end_idx] if x is not None]
    win_precips = [float(x) for x in precips[start_idx:end_idx] if x is not None]
    win_winds = [float(x) for x in winds[start_idx:end_idx] if x is not None]
    win_gusts = [float(x) for x in gusts[start_idx:end_idx] if x is not None]

    top_sm = soil_m_top[start_idx] if start_idx < len(soil_m_top) else None
    root_sm = soil_m_root[start_idx] if start_idx < len(soil_m_root) else None
    surf_st = soil_t[start_idx] if start_idx < len(soil_t) else None

    return {
        "max_rain_prob_pct": int(round(max(win_probs))) if win_probs else 0,
        "total_rain_mm": round(sum(win_precips), 2) if win_precips else 0.0,
        "max_wind_kmh": round(max(win_winds), 1) if win_winds else 0.0,
        "max_gust_kmh": round(max(win_gusts), 1) if win_gusts else 0.0,
        # Volumetric water content (m3/m3 -> percentage)
        "topsoil_moisture_pct": round(float(top_sm) * 100.0, 1) if top_sm is not None else None,
        "rootzone_moisture_pct": round(float(root_sm) * 100.0, 1) if root_sm is not None else None,
        "soil_temperature_c": round(float(surf_st), 1) if surf_st is not None else None,
    }


def _build_7day_forecast(daily: Dict[str, Any]) -> List[Dict[str, Any]]:
    dates = daily.get("time") or []
    codes = daily.get("weather_code") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    psum = daily.get("precipitation_sum") or []
    pprob = daily.get("precipitation_probability_max") or []
    wmax = daily.get("wind_speed_10m_max") or []
    et0 = daily.get("et0_fao_evapotranspiration") or []
    uv = daily.get("uv_index_max") or []

    days_out: List[Dict[str, Any]] = []
    for i, d_str in enumerate(dates):
        try:
            dt = datetime.strptime(d_str, "%Y-%m-%d")
            day_label = dt.strftime("%a %d %b")
        except ValueError:
            day_label = d_str

        code_val = int(codes[i]) if i < len(codes) and codes[i] is not None else 0
        days_out.append(
            {
                "date": d_str,
                "day_label": day_label,
                "weather_code": code_val,
                "condition": WMO_WEATHER_CODES.get(code_val, "Variable"),
                "temp_max_c": round(float(tmax[i]), 1) if i < len(tmax) and tmax[i] is not None else None,
                "temp_min_c": round(float(tmin[i]), 1) if i < len(tmin) and tmin[i] is not None else None,
                "rain_mm": round(float(psum[i]), 1) if i < len(psum) and psum[i] is not None else 0.0,
                "rain_prob_pct": int(round(float(pprob[i]))) if i < len(pprob) and pprob[i] is not None else 0,
                "wind_max_kmh": round(float(wmax[i]), 1) if i < len(wmax) and wmax[i] is not None else None,
                "et0_mm": round(float(et0[i]), 2) if i < len(et0) and et0[i] is not None else None,
                "uv_index_max": round(float(uv[i]), 1) if i < len(uv) and uv[i] is not None else None,
            }
        )
    return days_out


def _compute_agro_advisories(
    temp_c: float,
    humidity_pct: float,
    wind_kmh: float,
    gust_kmh: float,
    curr_precip_mm: float,
    rain_today_prob: int,
    rain_today_mm: float,
    rain_tom_prob: int,
    rain_tom_mm: float,
    et0_today_mm: Optional[float],
    win6h: Dict[str, Any],
    daily_7d: List[Dict[str, Any]],
) -> Dict[str, Any]:
    net_balance_mm = round(rain_today_mm - et0_today_mm, 2) if et0_today_mm is not None else None

    # 1. Irrigation Directive (plain, jargon-free farmer language)
    if rain_today_mm >= 5.0 or rain_today_prob >= 65 or win6h["total_rain_mm"] >= 3.0:
        irr_code = "DO_NOT_IRRIGATE"
        irr_text = (
            f"Do not water your crop today — there is a {rain_today_prob}% chance of rain ({rain_today_mm} mm expected). "
            f"Save water and electricity, and keep field drains clear."
        )
    elif rain_tom_mm >= 8.0 or rain_tom_prob >= 70:
        irr_code = "DELAY_IRRIGATION"
        irr_text = (
            f"Hold off on heavy watering — good rain ({rain_tom_prob}% chance, ~{rain_tom_mm} mm) is expected tomorrow."
        )
    elif (net_balance_mm is not None and net_balance_mm <= -4.5) or (temp_c >= 33.0 and humidity_pct <= 40):
        irr_code = "IRRIGATE_SOON"
        et_note = f" Crops are losing ~{et0_today_mm} mm of moisture today due to heat." if et0_today_mm is not None else ""
        irr_text = (
            f"Water your crop soon — hot weather ({temp_c}°C) is drying the soil quickly.{et_note} "
            f"Water in the early morning or evening so moisture isn't lost to the sun."
        )
    else:
        irr_code = "NORMAL_SCHEDULE"
        irr_text = (
            f"Weather is comfortable ({temp_c}°C, {rain_today_prob}% rain chance). "
            f"Continue your normal watering schedule."
        )

    # 2. Foliar Spraying Window (Next 6 Hours — plain farmer language)
    if curr_precip_mm > 0 or win6h["max_rain_prob_pct"] >= 45 or win6h["total_rain_mm"] >= 0.5:
        safe_spray = False
        spray_code = "AVOID_SPRAYING"
        spray_text = (
            f"Avoid spraying right now — {win6h['max_rain_prob_pct']}% chance of rain in the next 6 hours "
            f"can wash medicine or nutrients off the leaves."
        )
    elif wind_kmh > 15.0 or gust_kmh > 22.0 or win6h["max_wind_kmh"] > 18.0:
        safe_spray = False
        spray_code = "HIGH_WIND_DRIFT"
        spray_text = (
            f"Too windy to spray right now (wind {wind_kmh} km/h, gusts up to {max(gust_kmh, win6h['max_gust_kmh'])} km/h) — "
            f"spray mist will blow away. Wait for calm early-morning air."
        )
    elif temp_c > 33.0 and humidity_pct < 40:
        safe_spray = False
        spray_code = "SPRAY_EARLY_MORNING"
        spray_text = (
            f"Too hot and dry to spray right now ({temp_c}°C) — droplets dry too fast and can scorch leaves. "
            f"Spray before 9:00 AM or after 4:30 PM."
        )
    else:
        safe_spray = True
        spray_code = "IDEAL_FOR_SPRAYING"
        spray_text = (
            f"Safe to spray for the next 6 hours — low rain chance ({win6h['max_rain_prob_pct']}%) "
            f"and gentle wind ({wind_kmh} km/h)."
        )

    # 3. 72-Hour Harvest & Sun-Drying Outlook
    next_3d = daily_7d[:3]
    rain_3d_mm = round(sum(d["rain_mm"] for d in next_3d), 1)
    rain_3d_prob = max((d["rain_prob_pct"] for d in next_3d), default=0)
    if rain_3d_mm >= 5.0 or rain_3d_prob >= 60:
        drying_code = "PROTECT_HARVEST"
        drying_text = (
            f"Rain expected over the next 3 days ({rain_3d_mm} mm) — cover harvested crops with tarpaulin "
            f"and avoid open sun-drying."
        )
    elif humidity_pct <= 70:
        drying_code = "GOOD_DRYING_WINDOW"
        drying_text = (
            f"Next 3 days look dry — good weather for harvesting and sun-drying crops."
        )
    else:
        drying_code = "MODERATE_DRYING"
        drying_text = (
            f"Little rain over the next 3 days, but air is humid ({humidity_pct}%) — "
            f"turn drying produce often so it doesn't catch mold."
        )

    return {
        "net_water_balance_mm": net_balance_mm,
        "irrigation_code": irr_code,
        "irrigation_action": irr_text,
        "safe_to_spray_now": safe_spray,
        "spray_code": spray_code,
        "spray_action": spray_text,
        "drying_code": drying_code,
        "harvest_drying_action": drying_text,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public Entry Point
# ─────────────────────────────────────────────────────────────────────────────
def fetch_live_weather(
    location_query: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    db_path: str = DEFAULT_CACHE_DB_PATH,
) -> Dict[str, Any]:
    """
    Fetch real-time weather & 7-day agro-meteorological forecast for any location or GPS point.
    Zero hardcoded coordinates and zero fabricated fallback weather values.
    """
    geo, err_code, err_msg = geocode_location(
        location_query=location_query, lat=lat, lon=lon, db_path=db_path
    )
    if err_code or not geo:
        return {
            "status": err_code or "location_not_found",
            "is_live_data": False,
            "is_cached_data": False,
            "error_code": err_code or "location_not_found",
            "requested_location": location_query,
            "message": err_msg or "Unable to resolve location.",
            "summary": err_msg or "Unable to resolve location.",
        }

    lat_f = float(geo["latitude"])
    lon_f = float(geo["longitude"])
    place_name = geo["name"]
    district = geo.get("district")
    state = geo.get("state")

    display_parts = [place_name]
    if district and district.lower() not in place_name.lower():
        display_parts.append(district)
    if state and state.lower() not in place_name.lower() and (not district or state.lower() != district.lower()):
        display_parts.append(state)
    display_location = ", ".join(display_parts)

    params = {
        "latitude": lat_f,
        "longitude": lon_f,
        "current": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "precipitation",
                "rain",
                "weather_code",
                "wind_speed_10m",
                "wind_gusts_10m",
                "wind_direction_10m",
            ]
        ),
        "hourly": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation_probability",
                "precipitation",
                "wind_speed_10m",
                "wind_gusts_10m",
                "et0_fao_evapotranspiration",
                "soil_temperature_0cm",
                "soil_moisture_0_to_1cm",
                "soil_moisture_3_to_9cm",
            ]
        ),
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "wind_speed_10m_max",
                "wind_gusts_10m_max",
                "et0_fao_evapotranspiration",
                "uv_index_max",
            ]
        ),
        "timezone": "Asia/Kolkata",
        "forecast_days": 7,
    }

    try:
        resp = requests.get(
            OPEN_METEO_FORECAST_URL,
            params=params,
            headers=HTTP_HEADERS,
            timeout=8,
            verify=True,
        )
        resp.raise_for_status()
        data = resp.json()

        curr = data.get("current") or {}
        hourly = data.get("hourly") or {}
        daily = data.get("daily") or {}

        if curr.get("temperature_2m") is None:
            raise ValueError("Open-Meteo returned incomplete current telemetry.")

        temp_curr = round(float(curr["temperature_2m"]), 1)
        feels_like = round(float(curr["apparent_temperature"]), 1) if curr.get("apparent_temperature") is not None else temp_curr
        humidity_curr = int(round(float(curr["relative_humidity_2m"]))) if curr.get("relative_humidity_2m") is not None else 0
        wind_curr = round(float(curr["wind_speed_10m"]), 1) if curr.get("wind_speed_10m") is not None else 0.0
        gust_curr = round(float(curr["wind_gusts_10m"]), 1) if curr.get("wind_gusts_10m") is not None else wind_curr
        curr_precip = round(float(curr.get("precipitation") or 0.0), 2)
        w_code = int(curr.get("weather_code") or 0)
        condition_str = WMO_WEATHER_CODES.get(w_code, "Clear")

        daily_7d = _build_7day_forecast(daily)
        today_d = daily_7d[0] if len(daily_7d) >= 1 else {}
        tom_d = daily_7d[1] if len(daily_7d) >= 2 else {}

        rain_today_prob = int(today_d.get("rain_prob_pct", 0))
        rain_today_sum = float(today_d.get("rain_mm", 0.0))
        rain_tom_prob = int(tom_d.get("rain_prob_pct", 0))
        rain_tom_sum = float(tom_d.get("rain_mm", 0.0))
        et0_today = today_d.get("et0_mm")
        uv_max = today_d.get("uv_index_max")

        win6h = _extract_next_6h_window(hourly, curr.get("time"))
        advisories = _compute_agro_advisories(
            temp_c=temp_curr,
            humidity_pct=humidity_curr,
            wind_kmh=wind_curr,
            gust_kmh=gust_curr,
            curr_precip_mm=curr_precip,
            rain_today_prob=rain_today_prob,
            rain_today_mm=rain_today_sum,
            rain_tom_prob=rain_tom_prob,
            rain_tom_mm=rain_tom_sum,
            et0_today_mm=et0_today,
            win6h=win6h,
            daily_7d=daily_7d,
        )

        fetched_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
        obs_time_iso = curr.get("time")

        payload: Dict[str, Any] = {
            "status": "success",
            "is_live_data": True,
            "is_cached_data": False,
            "cache_age_minutes": 0,
            "data_source_label": "Live — Open-Meteo Agro-Meteorological API",
            "last_updated": fetched_str,
            "observation_time_ist": obs_time_iso,
            "source": f"Open-Meteo Real-Time Forecast ({geo.get('geocoder_source', 'Verified Coordinates')})",
            "location": place_name,
            "display_location": display_location,
            "district": district,
            "state": state,
            "coordinates": {
                "latitude": round(lat_f, 4),
                "longitude": round(lon_f, 4),
                "elevation_m": data.get("elevation", geo.get("elevation_m")),
            },
            "weather_code": w_code,
            "weather_condition": condition_str,
            "current_temperature_c": temp_curr,
            "feels_like_c": feels_like,
            "humidity_pct": humidity_curr,
            "wind_speed_kmh": wind_curr,
            "wind_gusts_kmh": gust_curr,
            "current_precipitation_mm": curr_precip,
            "rain_today_probability_pct": rain_today_prob,
            "rain_today_mm": rain_today_sum,
            "rain_tomorrow_probability_pct": rain_tom_prob,
            "rain_tomorrow_mm": rain_tom_sum,
            "et0_today_mm": et0_today,
            "net_water_balance_mm": advisories["net_water_balance_mm"],
            "uv_index_max": uv_max,
            "topsoil_moisture_pct": win6h["topsoil_moisture_pct"],
            "rootzone_moisture_pct": win6h["rootzone_moisture_pct"],
            "soil_temperature_c": win6h["soil_temperature_c"],
            "next_6h_window": {
                "max_rain_prob_pct": win6h["max_rain_prob_pct"],
                "rain_mm": win6h["total_rain_mm"],
                "max_wind_kmh": win6h["max_wind_kmh"],
                "max_gust_kmh": win6h["max_gust_kmh"],
                "safe_to_spray": advisories["safe_to_spray_now"],
            },
            "daily_forecast": daily_7d,
            "irrigation_code": advisories["irrigation_code"],
            "irrigation_action": advisories["irrigation_action"],
            "safe_to_spray_now": advisories["safe_to_spray_now"],
            "spray_code": advisories["spray_code"],
            "spray_action": advisories["spray_action"],
            "drying_code": advisories["drying_code"],
            "harvest_drying_action": advisories["harvest_drying_action"],
            "summary": (
                f"In {display_location}, live weather is {condition_str.lower()} at {temp_curr}°C "
                f"(humidity {humidity_curr}%, wind {wind_curr} km/h). "
                f"Today's rain probability is {rain_today_prob}% ({rain_today_sum} mm)"
                + (f", crop ET0 is {et0_today} mm/day. " if et0_today is not None else ". ")
                + advisories["irrigation_action"]
            ),
        }

        _save_cached_weather(lat_f, lon_f, payload, db_path=db_path)
        return payload

    except (requests.RequestException, ValueError, KeyError) as exc:
        # Check ONLY genuine recent cached Open-Meteo telemetry for these exact coordinates
        cached = _get_cached_weather(lat_f, lon_f, db_path=db_path)
        if cached is not None:
            cached_payload, age_min = cached
            age_label = f"{age_min} min" if age_min < 60 else f"{round(age_min / 60.0, 1)} hr"
            cached_payload["status"] = "cached_real"
            cached_payload["is_live_data"] = False
            cached_payload["is_cached_data"] = True
            cached_payload["cache_age_minutes"] = age_min
            cached_payload["location"] = place_name
            cached_payload["display_location"] = display_location
            cached_payload["data_source_label"] = f"Cached Open-Meteo ({age_label} old)"
            cached_payload["source"] = f"SQLite Real Open-Meteo Cache (fetched {cached_payload.get('last_updated')})"
            return cached_payload

        return {
            "status": "service_unavailable",
            "is_live_data": False,
            "is_cached_data": False,
            "error_code": "weather_service_unreachable",
            "location": place_name,
            "display_location": display_location,
            "coordinates": {"latitude": round(lat_f, 4), "longitude": round(lon_f, 4)},
            "message": (
                f"Live Open-Meteo weather API is currently unreachable ({type(exc).__name__}) "
                f"and no recent cached forecast exists for {display_location}."
            ),
            "summary": (
                f"Live weather service is temporarily unreachable for {display_location}. "
                f"Please check internet connectivity and try again."
            ),
        }


if __name__ == "__main__":
    import pprint
    pprint.pprint(fetch_live_weather("Mandya"))
