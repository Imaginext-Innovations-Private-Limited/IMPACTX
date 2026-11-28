"""API Router — Heatwave risk endpoints."""

from fastapi import APIRouter, Query
from app.ml.heatwave_calculator import HeatFeatures, calculate_heatwave_risk
from app.services.weather_service import weather_service
from datetime import datetime

router = APIRouter()


@router.get("/predict")
async def predict_heatwave(
    lat: float = Query(...),
    lon: float = Query(...),
    uhi_offset: float = Query(3.0, description="Urban Heat Island offset °C"),
    consecutive_hot_days: int = Query(0),
):
    """On-demand heatwave risk for any location."""
    weather = await weather_service.get_current_weather(lat, lon)
    uv = await weather_service.get_uv_index(lat, lon)

    hour = datetime.utcnow().hour
    is_night = hour < 6 or hour >= 20

    hf = HeatFeatures(
        temp_celsius=weather["temp_celsius"],
        humidity_pct=weather["humidity_pct"],
        uv_index=uv,
        wind_speed_kmh=weather["wind_speed_kmh"],
        urban_heat_island_offset=uhi_offset,
        is_night=is_night,
        consecutive_hot_days=consecutive_hot_days,
    )
    result = calculate_heatwave_risk(hf)
    return {
        **result,
        "weather": weather,
        "uv_index": uv,
    }
