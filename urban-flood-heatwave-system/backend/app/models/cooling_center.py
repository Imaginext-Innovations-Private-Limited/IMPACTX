"""ORM Models for Cooling Centres and Safe Shelters."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.core.database import Base


class CoolingCenter(Base):
    __tablename__ = "cooling_centers"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(256))
    center_type = Column(String(64))   # e.g. "School", "Community Hall", "Hospital"
    city        = Column(String(128), index=True)
    address     = Column(Text)
    latitude    = Column(Float)
    longitude   = Column(Float)
    capacity    = Column(Integer, default=100)
    current_occupancy = Column(Integer, default=0)
    is_open     = Column(Boolean, default=True)
    has_water   = Column(Boolean, default=True)
    has_medical = Column(Boolean, default=False)
    phone       = Column(String(32), nullable=True)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
