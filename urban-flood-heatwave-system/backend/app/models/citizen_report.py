"""ORM Models for Citizen Photo Reports."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class CitizenReport(Base):
    __tablename__ = "citizen_reports"

    id              = Column(Integer, primary_key=True, index=True)
    reporter_name   = Column(String(256), nullable=True)
    phone           = Column(String(32), nullable=True)
    city            = Column(String(128), index=True)
    latitude        = Column(Float)
    longitude       = Column(Float)
    description     = Column(Text, nullable=True)
    photo_path      = Column(String(512), nullable=True)
    # AI-analysed fields
    ai_label        = Column(String(128), nullable=True)   # e.g. "flooded_road", "heat_shimmer"
    ai_confidence   = Column(Float, nullable=True)
    ai_summary      = Column(Text, nullable=True)
    is_verified     = Column(Boolean, default=False)
    report_type     = Column(String(16), default="FLOOD")  # FLOOD / HEATWAVE
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
