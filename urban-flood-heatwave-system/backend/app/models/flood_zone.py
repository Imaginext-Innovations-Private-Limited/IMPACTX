"""ORM Models for Flood Zones and Drainage."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.core.database import Base


class FloodZone(Base):
    __tablename__ = "flood_zones"

    id          = Column(Integer, primary_key=True, index=True)
    zone_id     = Column(String(64), unique=True, index=True)
    name        = Column(String(256))
    city        = Column(String(128), index=True)
    latitude    = Column(Float)
    longitude   = Column(Float)
    # Drainage capacity in mm/hr
    drainage_capacity_mm = Column(Float, default=30.0)
    # Lake/reservoir fill level 0–100%
    lake_level_pct = Column(Float, default=50.0)
    elevation_m = Column(Float, default=0.0)
    risk_score  = Column(Float, default=0.0)   # 0–1 ML output
    risk_level  = Column(String(16), default="LOW")  # LOW/MEDIUM/HIGH/CRITICAL
    is_flooded  = Column(Boolean, default=False)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DrainageSensor(Base):
    __tablename__ = "drainage_sensors"

    id          = Column(Integer, primary_key=True, index=True)
    sensor_id   = Column(String(64), unique=True, index=True)
    zone_id     = Column(String(64), index=True)
    latitude    = Column(Float)
    longitude   = Column(Float)
    flow_rate   = Column(Float, default=0.0)   # litres/sec
    blockage_pct = Column(Float, default=0.0)  # 0–100 blockage percentage
    water_level_cm = Column(Float, default=0.0)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
