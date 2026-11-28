
"""
Background scheduler — refreshes flood + heatwave scores
and sends email notifications for new high-risk alerts.
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select, and_

from app.core.config import settings

logger = logging.getLogger(__name__)
_scheduler_task: asyncio.Task | None = None


async def _refresh_loop():
    from app.core.database import AsyncSessionLocal
    from app.services.weather_service import weather_service
    from app.services.alert_service import alert_service
    from app.services.email_service import email_service
    from app.ml.flood_predictor import FloodFeatures, flood_predictor
    from app.ml.heatwave_calculator import HeatFeatures, calculate_heatwave_risk
    from app.models.flood_zone import FloodZone
    from app.models.alert import Alert
    from app.models.user import User

    while True:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(FloodZone))
                zones = result.scalars().all()

                for zone in zones:
                    try:
                        weather = await weather_service.get_current_weather(
                            zone.latitude, zone.longitude
                        )
                        forecast = await weather_service.get_forecast(
                            zone.latitude, zone.longitude, 6
                        )
                        uv = await weather_service.get_uv_index(
                            zone.latitude, zone.longitude
                        )

                        # Flood prediction
                        ff = FloodFeatures(
                            rainfall_mm_1h=weather["rainfall_1h_mm"],
                            rainfall_mm_3h=weather["rainfall_3h_mm"],
                            rainfall_forecast_6h=forecast["forecast_rain_mm"],
                            drainage_capacity_mm=zone.drainage_capacity_mm,
                            drainage_blockage_pct=0.0,
                            lake_level_pct=zone.lake_level_pct,
                            elevation_m=zone.elevation_m,
                            soil_saturation=min(
                                weather["rainfall_3h_mm"] / 50.0, 1.0
                            ),
                            citizen_reports_1h=0,
                            water_level_cm=0.0,
                        )

                        flood_result = flood_predictor.predict(ff)
                        zone.risk_score = flood_result["risk_score"]
                        zone.risk_level = flood_result["risk_level"]
                        zone.updated_at = datetime.utcnow()

                        # Heatwave assessment
                        is_night = (
                            datetime.utcnow().hour < 6
                            or datetime.utcnow().hour >= 20
                        )

                        hf = HeatFeatures(
                            temp_celsius=weather["temp_celsius"],
                            humidity_pct=weather["humidity_pct"],
                            uv_index=uv,
                            wind_speed_kmh=weather["wind_speed_kmh"],
                            urban_heat_island_offset=3.0,
                            is_night=is_night,
                            consecutive_hot_days=0,
                        )

                        heat_result = calculate_heatwave_risk(hf)

                        # Check whether this warning already exists
                        # as an active alert.
                        async def alert_already_active(
                            alert_type, severity, zone_id=None
                        ):
                            conditions = [
                                Alert.alert_type == alert_type,
                                Alert.severity == severity,
                                Alert.city == zone.city,
                                Alert.is_active == True,
                                Alert.expires_at > datetime.utcnow(),
                            ]

                            if zone_id is None:
                                conditions.append(Alert.zone_id.is_(None))
                            else:
                                conditions.append(Alert.zone_id == zone_id)

                            existing = await db.execute(
                                select(Alert.id).where(and_(*conditions)).limit(1)
                            )
                            return existing.scalar_one_or_none() is not None

                        # Send email to users who enabled the relevant alerts.
                        async def notify_users(alert_type, title, message):
                            if not settings.EMAIL_ENABLED:
                                return

                            preference = (
                                User.flood_notifications
                                if alert_type == "FLOOD"
                                else User.heatwave_notifications
                            )

                            result = await db.execute(
                                select(User).where(
                                    User.email_notifications == True,
                                    preference == True,
                                )
                            )

                            users = result.scalars().all()

                            for user in users:
                                await email_service.send_email(
                                    recipient=user.email,
                                    subject=title,
                                    body=(
                                        f"Hello {user.username},\n\n"
                                        f"{message}\n\n"
                                        "Please check the Urban Flood & "
                                        "Heatwave Early-Warning System "
                                        "for further safety information.\n\n"
                                        "Stay safe."
                                    ),
                                )

                        # Flood alert
                        flood_level = flood_result["risk_level"]

                        if flood_level in ("HIGH", "CRITICAL"):
                            already_active = await alert_already_active(
                                "FLOOD", flood_level, zone.zone_id
                            )

                            if not already_active:
                                title, msg = alert_service.build_flood_message(
                                    zone.name,
                                    flood_level,
                                    flood_result["risk_score"],
                                )

                                await alert_service.create_alert(
                                    db,
                                    "FLOOD",
                                    flood_level,
                                    zone.city,
                                    title,
                                    msg,
                                    zone.zone_id,
                                    zone.latitude,
                                    zone.longitude,
                                )

                                await notify_users("FLOOD", title, msg)

                        # Heatwave alert
                        heat_level = heat_result["risk_level"]

                        if heat_level in ("HIGH", "CRITICAL"):
                            already_active = await alert_already_active(
                                "HEATWAVE", heat_level
                            )

                            if not already_active:
                                title, msg = alert_service.build_heatwave_message(
                                    zone.city,
                                    heat_level,
                                    heat_result["heat_index_celsius"],
                                )

                                await alert_service.create_alert(
                                    db,
                                    "HEATWAVE",
                                    heat_level,
                                    zone.city,
                                    title,
                                    msg,
                                )

                                await notify_users("HEATWAVE", title, msg)

                    except Exception as zone_err:
                        logger.exception(
                            "Zone %s update failed: %s",
                            zone.zone_id,
                            zone_err,
                        )

                await db.commit()

            logger.info("Forecast refresh complete.")

        except Exception as e:
            logger.exception("Scheduler error: %s", e)

        await asyncio.sleep(settings.FORECAST_REFRESH_SECONDS)


async def start_scheduler():
    global _scheduler_task

    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_refresh_loop())
        logger.info("Background scheduler started.")


async def stop_scheduler():
    global _scheduler_task

    if _scheduler_task:
        _scheduler_task.cancel()

        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass

        _scheduler_task = None

        logger.info("Background scheduler stopped.")
