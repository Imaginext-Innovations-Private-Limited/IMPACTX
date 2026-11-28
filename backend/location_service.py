"""
Shared Location Memory, Nominatim Reverse-Geocoding, Live Open-Meteo Weather,
and Cached APMC Mandi Context Injection Helpers.
"""
from datetime import datetime
import logging
from typing import Optional, Dict, Any, Tuple
import httpx
from sqlalchemy import or_

from database import SessionLocal
import models

logger = logging.getLogger("location_service")

KARNATAKA_DISTRICT_COORDS: Dict[str, Tuple[float, float, str, str]] = {
    "bengaluru": (12.9716, 77.5946, "Bengaluru Urban", "Karnataka"),
    "bangalore": (12.9716, 77.5946, "Bengaluru Urban", "Karnataka"),
    "shimoga": (13.9299, 75.5681, "Shivamogga", "Karnataka"),
    "shivamogga": (13.9299, 75.5681, "Shivamogga", "Karnataka"),
    "davangere": (14.4644, 75.9218, "Davanagere", "Karnataka"),
    "davanagere": (14.4644, 75.9218, "Davanagere", "Karnataka"),
    "dharwad": (15.4589, 75.0078, "Dharwad", "Karnataka"),
    "hubli": (15.3647, 75.1240, "Dharwad", "Karnataka"),
    "mysuru": (12.2958, 76.6394, "Mysuru", "Karnataka"),
    "mysore": (12.2958, 76.6394, "Mysuru", "Karnataka"),
    "belagavi": (15.8497, 74.4977, "Belagavi", "Karnataka"),
    "belgaum": (15.8497, 74.4977, "Belagavi", "Karnataka"),
    "hassan": (13.0033, 76.1004, "Hassan", "Karnataka"),
    "tumakuru": (13.3379, 77.1173, "Tumakuru", "Karnataka"),
    "tumkur": (13.3379, 77.1173, "Tumakuru", "Karnataka"),
    "kalaburagi": (17.3297, 76.8343, "Kalaburagi", "Karnataka"),
    "gulbarga": (17.3297, 76.8343, "Kalaburagi", "Karnataka"),
    "ballari": (15.1394, 76.9214, "Ballari", "Karnataka"),
    "bellary": (15.1394, 76.9214, "Ballari", "Karnataka"),
    "chikkamagaluru": (13.3161, 75.7720, "Chikkamagaluru", "Karnataka"),
    "mangaluru": (12.9141, 74.8560, "Dakshina Kannada", "Karnataka"),
    "mangalore": (12.9141, 74.8560, "Dakshina Kannada", "Karnataka"),
    "mandya": (12.5218, 76.8951, "Mandya", "Karnataka"),
    "udupi": (13.3409, 74.7421, "Udupi", "Karnataka"),
    "raichur": (16.2120, 77.3439, "Raichur", "Karnataka"),
    "bidar": (17.9104, 77.5199, "Bidar", "Karnataka"),
    "kolar": (13.1362, 78.1291, "Kolar", "Karnataka"),
    "chitradurga": (14.2251, 76.3980, "Chitradurga", "Karnataka"),
    "haveri": (14.7951, 75.3991, "Haveri", "Karnataka"),
    "gadag": (15.4315, 75.6355, "Gadag", "Karnataka"),
    "bagalkot": (16.1691, 75.6615, "Bagalkot", "Karnataka"),
    "vijayapura": (16.8302, 75.7100, "Vijayapura", "Karnataka"),
    "bijapur": (16.8302, 75.7100, "Vijayapura", "Karnataka"),
    "sirsi": (14.6196, 74.8354, "Uttara Kannada", "Karnataka"),
    "karwar": (14.8136, 74.1297, "Uttara Kannada", "Karnataka"),
    "kodagu": (12.3375, 75.8069, "Kodagu", "Karnataka"),
    "madikeri": (12.4244, 75.7382, "Kodagu", "Karnataka"),
    "pune": (18.5204, 73.8567, "Pune", "Maharashtra"),
    "nashik": (19.9975, 73.7898, "Nashik", "Maharashtra"),
    "nagpur": (21.1458, 79.0882, "Nagpur", "Maharashtra"),
    "coimbatore": (11.0168, 76.9558, "Coimbatore", "Tamil Nadu"),
    "thanjavur": (10.7870, 79.1378, "Thanjavur", "Tamil Nadu"),
    "hyderabad": (17.3850, 78.4867, "Rangareddy", "Telangana"),
    "warangal": (17.9689, 79.5941, "Warangal", "Telangana"),
    "guntur": (16.3067, 80.4365, "Guntur", "Andhra Pradesh"),
    "thrissur": (10.5276, 76.2144, "Thrissur", "Kerala"),
    "lucknow": (26.8467, 80.9462, "Lucknow", "Uttar Pradesh"),
    "ludhiana": (30.9010, 75.8573, "Ludhiana", "Punjab"),
    "karnal": (29.6857, 76.9905, "Karnal", "Haryana"),
    "indore": (22.7196, 75.8577, "Indore", "Madhya Pradesh"),
    "ahmedabad": (23.0225, 72.5714, "Ahmedabad", "Gujarat"),
    "rajkot": (22.3039, 70.8022, "Rajkot", "Gujarat"),
    "kolkata": (22.9000, 88.3900, "Hooghly", "West Bengal"),
    "jaipur": (26.9124, 75.7873, "Jaipur", "Rajasthan"),
    "patna": (25.5941, 85.1376, "Patna", "Bihar"),
    "cuttack": (20.4625, 85.8830, "Cuttack", "Odisha"),
}

NOMINATIM_HEADERS = {
    "User-Agent": "FarmAdvisor-KrishiMitra/1.0 (agricultural-advisory-bot)"
}

WMO_DESC = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
}


def get_saved_user_location(user_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Fetch saved UserLocation from SQLite by user_id or phone_number."""
    if not user_id:
        return None
    db = SessionLocal()
    try:
        rec = (
            db.query(models.UserLocation)
            .filter(
                or_(
                    models.UserLocation.user_id == user_id,
                    models.UserLocation.phone_number == user_id,
                )
            )
            .first()
        )
        if not rec:
            return None
        return {
            "user_id": rec.user_id,
            "phone_number": rec.phone_number,
            "latitude": rec.latitude,
            "longitude": rec.longitude,
            "district": rec.district,
            "state": rec.state,
            "location_name": rec.location_name or rec.district or (f"{rec.latitude:.4f}, {rec.longitude:.4f}" if rec.latitude is not None and rec.longitude is not None else None),
            "language_code": rec.language_code,
            "awaiting_language_choice": bool(rec.awaiting_language_choice),
            "updated_at": rec.updated_at.isoformat() if rec.updated_at else None,
        }
    except Exception as exc:
        logger.error("[LocationService] Failed fetching UserLocation for %s: %s", user_id, exc, exc_info=True)
        return None
    finally:
        db.close()


def save_user_location(
    user_id: str,
    latitude: float,
    longitude: float,
    district: Optional[str] = None,
    state: Optional[str] = None,
    location_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    language_code: Optional[str] = None,
    awaiting_language_choice: Optional[bool] = None,
) -> Dict[str, Any]:
    """Upsert UserLocation in SQLite."""
    db = SessionLocal()
    try:
        rec = (
            db.query(models.UserLocation)
            .filter(
                or_(
                    models.UserLocation.user_id == user_id,
                    models.UserLocation.phone_number == (phone_number or user_id),
                )
            )
            .first()
        )
        if rec:
            rec.latitude = float(latitude)
            rec.longitude = float(longitude)
            if district:
                rec.district = district
            if state:
                rec.state = state
            if location_name:
                rec.location_name = location_name
            if phone_number:
                rec.phone_number = phone_number
            if language_code is not None:
                rec.language_code = language_code
            if awaiting_language_choice is not None:
                rec.awaiting_language_choice = awaiting_language_choice
            rec.updated_at = datetime.utcnow()
        else:
            rec = models.UserLocation(
                user_id=user_id,
                phone_number=phone_number or user_id,
                latitude=float(latitude),
                longitude=float(longitude),
                district=district,
                state=state,
                location_name=location_name or district,
                updated_at=datetime.utcnow(),
            )
            db.add(rec)
        db.commit()
        db.refresh(rec)
        return {
            "user_id": rec.user_id,
            "phone_number": rec.phone_number,
            "latitude": rec.latitude,
            "longitude": rec.longitude,
            "district": rec.district,
            "state": rec.state,
            "location_name": rec.location_name or rec.district or f"{rec.latitude:.4f}, {rec.longitude:.4f}",
        }
    finally:
        db.close()


def get_whatsapp_state(phone_number: str) -> Dict[str, Any]:
    """Fetch WhatsApp user state (preferred language, awaiting_location, pending_question)."""
    db = SessionLocal()
    try:
        st = (
            db.query(models.WhatsAppUserState)
            .filter(models.WhatsAppUserState.phone_number == phone_number)
            .first()
        )
        if not st:
            return {
                "phone_number": phone_number,
                "preferred_language": "kn-IN",
                "awaiting_location": False,
                "pending_question": None,
            }
        return {
            "phone_number": st.phone_number,
            "preferred_language": st.preferred_language or "kn-IN",
            "awaiting_location": bool(st.awaiting_location),
            "pending_question": st.pending_question,
        }
    finally:
        db.close()


def update_whatsapp_state(
    phone_number: str,
    preferred_language: Optional[str] = None,
    awaiting_location: Optional[bool] = None,
    pending_question: Optional[str] = None,
    clear_pending: bool = False,
) -> None:
    """Update WhatsApp user state in SQLite."""
    db = SessionLocal()
    try:
        st = (
            db.query(models.WhatsAppUserState)
            .filter(models.WhatsAppUserState.phone_number == phone_number)
            .first()
        )
        if not st:
            st = models.WhatsAppUserState(phone_number=phone_number)
            db.add(st)
        if preferred_language:
            st.preferred_language = preferred_language
        if awaiting_location is not None:
            st.awaiting_location = awaiting_location
        if clear_pending:
            st.pending_question = None
            st.awaiting_location = False
        elif pending_question is not None:
            st.pending_question = pending_question
        st.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


async def reverse_geocode_nominatim(lat: float, lon: float) -> Dict[str, Any]:
    """
    Reverse-geocode latitude/longitude into district, taluk/village, and state
    via OpenStreetMap Nominatim.
    """
    url = (
        f"https://nominatim.openstreetmap.org/reverse"
        f"?format=jsonv2&lat={lat}&lon={lon}&zoom=10&addressdetails=1"
    )
    try:
        timeout = httpx.Timeout(connect=3.0, read=5.0, write=5.0, pool=6.0)
        async with httpx.AsyncClient(timeout=timeout, headers=NOMINATIM_HEADERS) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            addr = data.get("address", {})
            taluk = (
                addr.get("suburb")
                or addr.get("village")
                or addr.get("town")
                or addr.get("city")
                or addr.get("county")
                or ""
            )
            district = (
                addr.get("state_district")
                or addr.get("county")
                or addr.get("city")
                or taluk
                or "Unknown District"
            )
            # Clean trailing " district" for readability
            district_clean = district.replace(" District", "").replace(" district", "").strip()
            state = addr.get("state") or "Karnataka"
            parts = [p for p in [taluk if taluk and taluk.lower() != district_clean.lower() else "", district_clean, state] if p]
            display_name = ", ".join(parts) if parts else f"{lat:.4f}, {lon:.4f}"
            return {
                "taluk": taluk,
                "district": district_clean,
                "state": state,
                "location_name": display_name,
            }
    except Exception as exc:
        logger.error("[Location] Nominatim reverse-geocode failed for (%.4f, %.4f): %s", lat, lon, exc)
        print(f"[Location ERROR] Nominatim reverse-geocode failed: {exc}", flush=True)
        return {
            "taluk": "",
            "district": f"{lat:.4f}, {lon:.4f}",
            "state": "",
            "location_name": f"{lat:.4f}, {lon:.4f}",
        }


async def geocode_place_nominatim(place_query: str) -> Optional[Dict[str, Any]]:
    """
    Forward-geocode a village/taluk/district name using local Karnataka coords first,
    then OpenStreetMap Nominatim search.
    """
    cleaned = (place_query or "").strip()
    if not cleaned:
        return None

    low = cleaned.lower()
    for key, (lat, lon, dist, st) in KARNATAKA_DISTRICT_COORDS.items():
        if key == low or key in low.split():
            return {
                "latitude": lat,
                "longitude": lon,
                "district": dist,
                "state": st,
                "location_name": f"{dist}, {st}",
            }

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{cleaned}, India",
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 1,
    }
    try:
        timeout = httpx.Timeout(connect=3.0, read=5.0, write=5.0, pool=6.0)
        async with httpx.AsyncClient(timeout=timeout, headers=NOMINATIM_HEADERS) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            results = resp.json()
            if not results:
                return None
            top = results[0]
            lat = float(top["lat"])
            lon = float(top["lon"])
            addr = top.get("address", {})
            taluk = addr.get("village") or addr.get("town") or addr.get("city") or addr.get("county") or ""
            district = (
                addr.get("state_district")
                or addr.get("county")
                or addr.get("city")
                or taluk
                or cleaned
            )
            district_clean = district.replace(" District", "").replace(" district", "").strip()
            state = addr.get("state") or "Karnataka"
            parts = [p for p in [taluk if taluk and taluk.lower() != district_clean.lower() else "", district_clean, state] if p]
            return {
                "latitude": lat,
                "longitude": lon,
                "district": district_clean,
                "state": state,
                "location_name": ", ".join(parts) if parts else cleaned,
            }
    except Exception as exc:
        logger.error("[Location] Nominatim search failed for '%s': %s", cleaned, exc)
        print(f"[Location ERROR] Nominatim search failed for '{cleaned}': {exc}", flush=True)
        return None


def resolve_coordinates(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    location_name: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Resolve coordinates & location name from explicit arguments, saved UserLocation,
    or known district name lookup.
    """
    if lat is not None and lon is not None:
        return {
            "latitude": float(lat),
            "longitude": float(lon),
            "location_name": location_name or f"{float(lat):.4f}, {float(lon):.4f}",
            "source": "request_coords",
        }

    if user_id:
        saved = get_saved_user_location(user_id)
        if saved:
            return {
                "latitude": saved["latitude"],
                "longitude": saved["longitude"],
                "location_name": location_name or saved["location_name"],
                "district": saved.get("district"),
                "state": saved.get("state"),
                "source": "saved_user_location",
            }

    if location_name:
        low = location_name.strip().lower()
        for key, (k_lat, k_lon, dist, st) in KARNATAKA_DISTRICT_COORDS.items():
            if key in low:
                return {
                    "latitude": k_lat,
                    "longitude": k_lon,
                    "location_name": location_name,
                    "district": dist,
                    "state": st,
                    "source": "district_lookup",
                }

    return {
        "latitude": None,
        "longitude": None,
        "location_name": location_name or "Not specified",
        "source": "unspecified",
    }


def _parse_open_meteo_payload(data: Dict[str, Any], lat: float, lon: float, loc_label: str) -> Dict[str, Any]:
    curr = data.get("current", {})
    daily = data.get("daily", {})

    w_code = curr.get("weather_code")
    if w_code is None and daily.get("weather_code"):
        w_code = daily["weather_code"][0]
    weather_desc = WMO_DESC.get(w_code, "Variable sky")

    temp_now = curr.get("temperature_2m")
    rh_now = curr.get("relative_humidity_2m")
    wind_now = curr.get("wind_speed_10m")
    rain_now = curr.get("precipitation")

    rain_today = (daily.get("precipitation_sum") or [0.0])[0]
    rain_prob = (daily.get("precipitation_probability_max") or [0])[0]
    tmax = (daily.get("temperature_2m_max") or [None])[0]
    tmin = (daily.get("temperature_2m_min") or [None])[0]

    rain_3day = sum(v or 0.0 for v in (daily.get("precipitation_sum") or [])[:3])
    summary = (
        f"Location: {loc_label} (lat={lat:.4f}, lon={lon:.4f}). "
        f"Current weather: {weather_desc}, temp={temp_now}°C, humidity={rh_now}%, "
        f"wind={wind_now} km/h, current_precip={rain_now} mm. "
        f"Today max/min: {tmax}°C/{tmin}°C, rain_today={rain_today} mm (prob {rain_prob}%), "
        f"3-day total rain forecast={rain_3day:.1f} mm."
    )
    return {
        "is_live": True,
        "location_name": loc_label,
        "latitude": lat,
        "longitude": lon,
        "weather_desc": weather_desc,
        "temp_now": temp_now,
        "humidity_pct": rh_now,
        "wind_kmh": wind_now,
        "rain_today_mm": rain_today,
        "rain_prob_pct": rain_prob,
        "temp_max": tmax,
        "temp_min": tmin,
        "rain_3day_mm": round(rain_3day, 1),
        "summary_text": summary,
    }


def fetch_live_weather_sync(lat: float, lon: float, location_name: Optional[str] = None) -> Dict[str, Any]:
    """Fetch live Open-Meteo weather synchronously for given coordinates."""
    loc_label = location_name or f"{lat:.4f}, {lon:.4f}"
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max"
        f"&forecast_days=3&timezone=auto"
    )
    try:
        timeout = httpx.Timeout(4.0)
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return _parse_open_meteo_payload(resp.json(), lat, lon, loc_label)
    except Exception as exc:
        logger.error("[Weather Context] Open-Meteo fetch failed for (%.4f, %.4f): %s", lat, lon, exc)
        print(f"[Weather Context ERROR] Open-Meteo fetch failed: {exc}", flush=True)
        return {
            "is_live": False,
            "location_name": loc_label,
            "latitude": lat,
            "longitude": lon,
            "summary_text": f"Location: {loc_label} (lat={lat:.4f}, lon={lon:.4f}). Live Open-Meteo weather temporarily unavailable ({exc}).",
        }


async def fetch_live_weather_async(lat: float, lon: float, location_name: Optional[str] = None) -> Dict[str, Any]:
    """Fetch live Open-Meteo weather asynchronously for given coordinates."""
    loc_label = location_name or f"{lat:.4f}, {lon:.4f}"
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max"
        f"&forecast_days=3&timezone=auto"
    )
    try:
        timeout = httpx.Timeout(4.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return _parse_open_meteo_payload(resp.json(), lat, lon, loc_label)
    except Exception as exc:
        logger.error("[Weather Context] Open-Meteo async fetch failed for (%.4f, %.4f): %s", lat, lon, exc)
        print(f"[Weather Context ERROR] Open-Meteo async fetch failed: {exc}", flush=True)
        return {
            "is_live": False,
            "location_name": loc_label,
            "latitude": lat,
            "longitude": lon,
            "summary_text": f"Location: {loc_label} (lat={lat:.4f}, lon={lon:.4f}). Live Open-Meteo weather temporarily unavailable ({exc}).",
        }


def resolve_state(
    state: Optional[str] = None,
    location_name: Optional[str] = None,
    district: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> str:
    """
    Resolve canonical Indian state name from state, location name, district, or GPS coordinates.
    Defaults to 'Karnataka' if no specific Indian state can be resolved.
    """
    known_states = {
        "karnataka": "Karnataka",
        "telangana": "Telangana",
        "maharashtra": "Maharashtra",
        "tamil nadu": "Tamil Nadu",
        "tamilnadu": "Tamil Nadu",
        "andhra pradesh": "Andhra Pradesh",
        "andhra": "Andhra Pradesh",
        "kerala": "Kerala",
        "uttar pradesh": "Uttar Pradesh",
        "punjab": "Punjab",
        "haryana": "Haryana",
        "madhya pradesh": "Madhya Pradesh",
        "gujarat": "Gujarat",
        "west bengal": "West Bengal",
        "rajasthan": "Rajasthan",
        "bihar": "Bihar",
        "odisha": "Odisha",
        "orissa": "Odisha",
    }
    # 1. Direct state string
    if state and state.strip():
        s_clean = state.strip().lower()
        if s_clean in known_states:
            return known_states[s_clean]
        for key, canonical in known_states.items():
            if key in s_clean:
                return canonical

    # 2. Check district/location_name
    test_str = f"{district or ''} {location_name or ''}".lower()
    for key, canonical in known_states.items():
        if key in test_str:
            return canonical

    # 3. Known district/city keywords in test_str
    city_to_state = {
        "hyderabad": "Telangana", "warangal": "Telangana", "nizamabad": "Telangana", "khammam": "Telangana",
        "pune": "Maharashtra", "mumbai": "Maharashtra", "nashik": "Maharashtra", "nagpur": "Maharashtra",
        "coimbatore": "Tamil Nadu", "thanjavur": "Tamil Nadu", "chennai": "Tamil Nadu", "madurai": "Tamil Nadu",
        "guntur": "Andhra Pradesh", "vijayawada": "Andhra Pradesh", "kurnool": "Andhra Pradesh",
        "thrissur": "Kerala", "kochi": "Kerala", "palakkad": "Kerala", "wayanad": "Kerala",
        "lucknow": "Uttar Pradesh", "kanpur": "Uttar Pradesh", "varanasi": "Uttar Pradesh", "agra": "Uttar Pradesh",
        "ludhiana": "Punjab", "amritsar": "Punjab", "jalandhar": "Punjab", "bathinda": "Punjab",
        "karnal": "Haryana", "hisar": "Haryana", "ambala": "Haryana",
        "indore": "Madhya Pradesh", "bhopal": "Madhya Pradesh", "ujjain": "Madhya Pradesh",
        "ahmedabad": "Gujarat", "rajkot": "Gujarat", "surat": "Gujarat", "vadodara": "Gujarat",
        "kolkata": "West Bengal", "hooghly": "West Bengal", "siliguri": "West Bengal", "bardhaman": "West Bengal",
        "jaipur": "Rajasthan", "jodhpur": "Rajasthan", "kota": "Rajasthan", "bikaner": "Rajasthan",
        "patna": "Bihar", "gaya": "Bihar", "muzaffarpur": "Bihar",
        "cuttack": "Odisha", "bhubaneswar": "Odisha", "sambalpur": "Odisha",
        "bengaluru": "Karnataka", "bangalore": "Karnataka", "shivamogga": "Karnataka", "mysuru": "Karnataka",
        "davanagere": "Karnataka", "dharwad": "Karnataka", "belagavi": "Karnataka", "tumakuru": "Karnataka",
    }
    for city, st in city_to_state.items():
        if city in test_str:
            return st

    # 4. Lat/lon proximity
    if lat is not None and lon is not None:
        best_dist = 999999.0
        best_state = None
        for _name, (clat, clon, _dist, st) in KARNATAKA_DISTRICT_COORDS.items():
            dist = (clat - lat) ** 2 + (clon - lon) ** 2
            if dist < best_dist:
                best_dist = dist
                best_state = st
        if best_state and best_dist < 4.0:  # within ~200km
            return best_state

    return "Karnataka"


def get_cached_mandi_prices_context(limit_commodities: int = 10, limit_mandis: int = 12) -> str:
    """Build a concise snapshot of cached APMC mandi prices from SQLite for Gemini prompt injection."""
    db = SessionLocal()
    try:
        commodities = db.query(models.Commodity).limit(limit_commodities).all()
        mandis = (
            db.query(models.MandiPrice)
            .order_by(models.MandiPrice.recorded_date.desc())
            .limit(limit_mandis)
            .all()
        )
        lines = []
        if commodities:
            c_strs = [
                f"{c.name}: ₹{c.current_price:.0f}/{c.unit} ({c.market})"
                for c in commodities
            ]
            lines.append("Headline APMC Rates: " + "; ".join(c_strs))
        if mandis:
            m_strs = [
                f"{m.commodity_name} @ {m.market_name} ({m.district}): modal ₹{m.modal_price:.0f} (min ₹{m.min_price:.0f}-max ₹{m.max_price:.0f}, date {m.recorded_date})"
                for m in mandis
            ]
            lines.append("Recent Cached Mandi Records: " + "; ".join(m_strs))
        return "\n".join(lines) if lines else "No cached APMC mandi records in database."
    except Exception as exc:
        logger.error("[Mandi Context] Failed reading cached APMC prices: %s", exc)
        return "Cached APMC mandi prices currently unavailable."
    finally:
        db.close()
