"""Live-data tools the agent can call: weather, soil, market prices."""
import os, re
import httpx

TIMEOUT = httpx.Timeout(15.0)

async def _geocode(place: str):
    m = re.search(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", place)
    if m:  # exact point picked on the map
        return float(m.group(1)), float(m.group(2)), re.sub(r"\s*@.*$", "", place).strip() or "Selected point"
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get("https://geocoding-api.open-meteo.com/v1/search",
                        params={"name": place, "count": 1})
        res = r.json().get("results")
    if not res:
        raise ValueError(f"Could not find location '{place}'")
    g = res[0]
    return g["latitude"], g["longitude"], f'{g["name"]}, {g.get("admin1", "")}'

async def get_weather(location: str) -> dict:
    """Current weather, 5-day forecast, ET0 and top-layer soil moisture (Open-Meteo, no key)."""
    try:
        lat, lon, name = await _geocode(location)
        params = {
            "latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 5,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                     "precipitation_probability_max,et0_fao_evapotranspiration",
            "hourly": "soil_moisture_3_to_9cm,soil_temperature_6cm",
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            d = (await c.get("https://api.open-meteo.com/v1/forecast", params=params)).json()
        daily = d["daily"]
        forecast = [{
            "date": daily["time"][i],
            "tmax_c": daily["temperature_2m_max"][i], "tmin_c": daily["temperature_2m_min"][i],
            "rain_mm": daily["precipitation_sum"][i],
            "rain_chance_pct": daily["precipitation_probability_max"][i],
            "et0_mm": daily["et0_fao_evapotranspiration"][i],
        } for i in range(len(daily["time"]))]
        h = d["hourly"]
        return {
            "location": name, "lat": lat, "lon": lon, "current": d["current"],
            "forecast": forecast,
            "soil_moisture_m3m3_now": h["soil_moisture_3_to_9cm"][0],
            "soil_temp_c_now": h["soil_temperature_6cm"][0],
        }
    except Exception as e:
        return {"error": f"weather lookup failed: {e}"}

async def get_soil_health(location: str) -> dict:
    """Soil properties (pH, organic carbon, nitrogen, clay, sand) from ISRIC SoilGrids."""
    try:
        lat, lon, name = await _geocode(location)
        props = ["phh2o", "soc", "nitrogen", "clay", "sand"]
        params = [("lat", lat), ("lon", lon), ("depth", "0-5cm"), ("value", "mean")] + [("property", p) for p in props]
        async with httpx.AsyncClient(timeout=httpx.Timeout(40.0)) as c:
            r = await c.get("https://rest.isric.org/soilgrids/v2.0/properties/query", params=params)
            r.raise_for_status()
            layers = r.json()["properties"]["layers"]
        out = {}
        units = {"phh2o": "pH", "soc": "g/kg organic carbon", "nitrogen": "g/kg total N",
                 "clay": "% clay", "sand": "% sand"}
        for l in layers:
            v = l["depths"][0]["values"]["mean"]
            f = l["unit_measure"].get("d_factor", 1) or 1
            out[l["name"]] = {"value": round(v / f, 2) if v is not None else None, "unit": units.get(l["name"], "")}
        return {"location": name, "depth": "0-5cm", "soil": out,
                "note": "Satellite-modelled estimate; recommend a local soil-health-card test for exact NPK."}
    except Exception as e:
        return {"error": f"soil lookup failed: {e}. Advise farmer to use their Soil Health Card."}

_DEMO_PRICES = {  # Rs/quintal, illustrative fallback when no API key / API down
    "tomato": (1800, 2600, 2200), "onion": (1500, 2400, 1900), "potato": (1400, 2000, 1700),
    "ragi": (3300, 4100, 3700), "maize": (2000, 2400, 2200), "rice": (2100, 3000, 2500),
    "wheat": (2300, 2700, 2500), "cotton": (6500, 7400, 7000), "groundnut": (5500, 6600, 6000),
}

async def get_market_prices(commodity: str, state: str = "") -> dict:
    """Mandi prices (Rs/quintal) from Agmarknet via data.gov.in; demo fallback if unavailable."""
    key = os.getenv("DATA_GOV_API_KEY")
    if key:
        try:
            params = {"api-key": key, "format": "json", "limit": 10,
                      "filters[commodity]": commodity.title()}
            if state:
                params["filters[state]"] = state.title()
            async with httpx.AsyncClient(timeout=TIMEOUT) as c:
                r = await c.get("https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070", params=params)
            recs = r.json().get("records", [])
            if recs:
                return {"source": "Agmarknet (live)", "unit": "Rs/quintal", "records": [
                    {k: x.get(k) for k in ("market", "district", "state", "variety", "arrival_date",
                                           "min_price", "max_price", "modal_price")} for x in recs]}
        except Exception:
            pass
    lo, hi, mod = _DEMO_PRICES.get(commodity.lower(), (0, 0, 0))
    if not mod:
        return {"error": f"No price data for {commodity}"}
    return {"source": "DEMO DATA (set DATA_GOV_API_KEY for live prices)", "unit": "Rs/quintal",
            "records": [{"market": "Sample mandi", "min_price": lo, "max_price": hi, "modal_price": mod}]}

TOOL_FUNCS = {"get_weather": get_weather, "get_soil_health": get_soil_health, "get_market_prices": get_market_prices}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_weather",
        "description": "Get current weather, 5-day forecast (rain, temperature, evapotranspiration) and soil moisture for a place. Use for irrigation, sowing and spraying timing.",
        "parameters": {"type": "object", "properties": {"location": {"type": "string", "description": "Village/town/district name, e.g. 'Mandya'"}}, "required": ["location"]}}},
    {"type": "function", "function": {
        "name": "get_soil_health",
        "description": "Get soil pH, organic carbon, nitrogen, clay and sand content for a place. Use for crop selection and fertilizer advice.",
        "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}}},
    {"type": "function", "function": {
        "name": "get_market_prices",
        "description": "Get latest mandi (market) prices in Rs/quintal for a crop. Use for selling advice.",
        "parameters": {"type": "object", "properties": {
            "commodity": {"type": "string", "description": "English crop name, e.g. 'Tomato'"},
            "state": {"type": "string", "description": "Indian state, e.g. 'Karnataka' (optional)"}}, "required": ["commodity"]}}},
]
