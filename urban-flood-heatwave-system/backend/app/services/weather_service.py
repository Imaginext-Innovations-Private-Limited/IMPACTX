"""
Weather Data Service — fetches rainfall forecasts and temperature data
from OpenWeatherMap API and caches them.
"""

import httpx
from datetime import datetime
from app.core.config import settings


class WeatherService:

    BASE = settings.OPENWEATHER_BASE_URL
    KEY  = settings.OPENWEATHER_API_KEY

    async def get_current_weather(self, lat: float, lon: float) -> dict:
        """Fetch current conditions for a coordinate."""
        url = f"{self.BASE}/weather"
        params = {"lat": lat, "lon": lon, "appid": self.KEY, "units": "metric"}
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        return {
            "temp_celsius":    data["main"]["temp"],
            "humidity_pct":    data["main"]["humidity"],
            "wind_speed_kmh":  data["wind"]["speed"] * 3.6,
            "rainfall_1h_mm":  data.get("rain", {}).get("1h", 0.0),
            "rainfall_3h_mm":  data.get("rain", {}).get("3h", 0.0),
            "uv_index":        0.0,  # fetched separately below
            "weather_desc":    data["weather"][0]["description"],
            "city_name":       data.get("name", ""),
            "timestamp":       datetime.utcnow().isoformat(),
        }

    async def get_forecast(self, lat: float, lon: float, hours: int = 6) -> dict:
        """Fetch 5-day/3-hour forecast, return cumulative rain for next N hours."""
        url = f"{self.BASE}/forecast"
        params = {"lat": lat, "lon": lon, "appid": self.KEY, "units": "metric", "cnt": max(1, hours // 3)}
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        total_rain = sum(
            item.get("rain", {}).get("3h", 0.0)
            for item in data.get("list", [])
        )
        max_temp = max(
            (item["main"]["temp"] for item in data.get("list", [])),
            default=0.0
        )
        return {
            "forecast_rain_mm": total_rain,
            "forecast_max_temp": max_temp,
            "periods": data.get("list", []),
        }

    async def get_uv_index(self, lat: float, lon: float) -> float:
        url = f"{self.BASE}/uvi"
        params = {"lat": lat, "lon": lon, "appid": self.KEY}
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(url, params=params)
                r.raise_for_status()
                return r.json().get("value", 0.0)
        except Exception:
            return 0.0


weather_service = WeatherService()
