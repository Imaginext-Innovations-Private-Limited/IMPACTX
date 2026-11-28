"""API Router — Flood risk endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.flood_zone import FloodZone
from app.ml.flood_predictor import FloodFeatures, flood_predictor
from app.services.weather_service import weather_service
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class FloodZoneOut(BaseModel):
    zone_id: str
    name: str
    city: str
    latitude: float
    longitude: float
    risk_score: float
    risk_level: str
    is_flooded: bool
    updated_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("/zones", response_model=list[FloodZoneOut])
async def list_flood_zones(
    city: Optional[str] = Query(None),
    min_risk: Optional[str] = Query(None, description="LOW|MEDIUM|HIGH|CRITICAL"),
    db: AsyncSession = Depends(get_db),
):
    """List all flood zones with current risk scores."""
    q = select(FloodZone)
    if city:
        q = q.where(FloodZone.city == city)
    if min_risk:
        levels = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        allowed = [k for k, v in levels.items() if v >= levels.get(min_risk, 0)]
        q = q.where(FloodZone.risk_level.in_(allowed))
    result = await db.execute(q.order_by(FloodZone.risk_score.desc()))
    return result.scalars().all()


@router.get("/zones/{zone_id}", response_model=FloodZoneOut)
async def get_flood_zone(zone_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FloodZone).where(FloodZone.zone_id == zone_id))
    zone = result.scalar_one_or_none()
    if not zone:
        from fastapi import HTTPException
        raise HTTPException(404, "Zone not found")
    return zone


@router.post("/predict")
async def predict_flood_risk(
    lat: float = Query(...),
    lon: float = Query(...),
    drainage_capacity: float = Query(30.0),
    lake_level: float = Query(50.0),
    elevation: float = Query(5.0),
):
    """
    On-demand flood risk prediction for any lat/lon using live weather data.
    """
    weather = await weather_service.get_current_weather(lat, lon)
    forecast = await weather_service.get_forecast(lat, lon, 6)

    ff = FloodFeatures(
        rainfall_mm_1h=weather["rainfall_1h_mm"],
        rainfall_mm_3h=weather["rainfall_3h_mm"],
        rainfall_forecast_6h=forecast["forecast_rain_mm"],
        drainage_capacity_mm=drainage_capacity,
        drainage_blockage_pct=0.0,
        lake_level_pct=lake_level,
        elevation_m=elevation,
        soil_saturation=min(weather["rainfall_3h_mm"] / 50.0, 1.0),
        citizen_reports_1h=0,
        water_level_cm=0.0,
    )
    result = flood_predictor.predict(ff)
    return {
        **result,
        "weather": weather,
        "forecast": {"forecast_rain_mm": forecast["forecast_rain_mm"]},
    }
