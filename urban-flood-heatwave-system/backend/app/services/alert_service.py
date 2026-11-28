"""
Alert Service — creates, broadcasts (via WebSocket/Redis), and manages alerts.
"""

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.alert import Alert
from app.core.config import settings


class AlertService:

    async def create_alert(
        self,
        db: AsyncSession,
        alert_type: str,
        severity: str,
        city: str,
        title: str,
        message: str,
        zone_id: str = None,
        lat: float = None,
        lon: float = None,
        hours_valid: int = 6,
    ) -> Alert:
        expires = datetime.utcnow() + timedelta(hours=hours_valid)
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            city=city,
            zone_id=zone_id,
            title=title,
            message=message,
            latitude=lat,
            longitude=lon,
            expires_at=expires,
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        return alert

    async def get_active_alerts(self, db: AsyncSession, city: str = None):
        q = select(Alert).where(
            Alert.is_active == True,
            Alert.expires_at > datetime.utcnow(),
        )
        if city:
            q = q.where(Alert.city == city)
        result = await db.execute(q.order_by(Alert.created_at.desc()))
        return result.scalars().all()

    async def deactivate_alert(self, db: AsyncSession, alert_id: int):
        result = await db.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()
        if alert:
            alert.is_active = False
            await db.commit()
        return alert

    def build_flood_message(self, zone_name: str, risk_level: str, risk_score: float) -> tuple[str, str]:
        title = f"⚠️ Flood Risk Alert – {zone_name}"
        message = (
            f"Flood risk in {zone_name} is {risk_level} (score: {risk_score:.0%}). "
            "Avoid low-lying streets. Use the app to find safe routes."
        )
        if risk_level == "CRITICAL":
            title = f"🚨 CRITICAL Flood Warning – {zone_name}"
            message = (
                f"CRITICAL flood warning for {zone_name}. Evacuate immediately. "
                "Do NOT attempt to walk or drive through flooded streets."
            )
        return title, message

    def build_heatwave_message(self, city: str, risk_level: str, heat_index: float) -> tuple[str, str]:
        title = f"🌡️ Heatwave Alert – {city}"
        message = (
            f"Heatwave conditions in {city}. Feels like {heat_index:.1f}°C. "
            "Find a cooling centre near you."
        )
        if risk_level == "CRITICAL":
            title = f"🔴 CRITICAL Heatwave Warning – {city}"
            message = (
                f"Extreme heat emergency in {city} – feels like {heat_index:.1f}°C. "
                "Go to the nearest cooling centre immediately."
            )
        return title, message


alert_service = AlertService()
