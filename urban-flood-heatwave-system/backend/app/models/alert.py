"""ORM Models for Alerts."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Enum
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class AlertType(str, enum.Enum):
    FLOOD = "FLOOD"
    HEATWAVE = "HEATWAVE"
    COMBINED = "COMBINED"


class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Alert(Base):
    __tablename__ = "alerts"

    id          = Column(Integer, primary_key=True, index=True)
    alert_type  = Column(String(16))
    severity    = Column(String(16))
    city        = Column(String(128), index=True)
    zone_id     = Column(String(64), index=True, nullable=True)
    title       = Column(String(512))
    message     = Column(Text)
    latitude    = Column(Float, nullable=True)
    longitude   = Column(Float, nullable=True)
    is_active   = Column(Boolean, default=True)
    expires_at  = Column(DateTime(timezone=True), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
