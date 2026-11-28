
"""API Router — Alerts and email notification subscriptions."""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional

from app.core.database import get_db
from app.services.alert_service import alert_service
from app.models.user import User

router = APIRouter()


class EmailSubscription(BaseModel):
    username: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    email_notifications: bool = True
    flood_notifications: bool = True
    heatwave_notifications: bool = True


@router.get("/")
async def get_active_alerts(
    city: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get all currently active alerts."""
    alerts = await alert_service.get_active_alerts(db, city)

    return [
        {
            "id": a.id,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "city": a.city,
            "zone_id": a.zone_id,
            "title": a.title,
            "message": a.message,
            "latitude": a.latitude,
            "longitude": a.longitude,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "expires_at": a.expires_at.isoformat() if a.expires_at else None,
        }
        for a in alerts
    ]


@router.delete("/{alert_id}")
async def deactivate_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
):
    alert = await alert_service.deactivate_alert(db, alert_id)

    if not alert:
        raise HTTPException(404, "Alert not found")

    return {"status": "deactivated", "alert_id": alert_id}


@router.post("/subscribe")
async def subscribe_to_email_alerts(
    request: EmailSubscription,
    db: AsyncSession = Depends(get_db),
):
    """Register or update a user's email alert preferences."""

    email = request.email.strip().lower()
    username = request.username.strip()

    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(400, "Please enter a valid email address.")

    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if user:
        user.username = username
        user.email_notifications = request.email_notifications
        user.flood_notifications = request.flood_notifications
        user.heatwave_notifications = request.heatwave_notifications
    else:
        username_result = await db.execute(
            select(User).where(User.username == username)
        )

        if username_result.scalar_one_or_none():
            raise HTTPException(
                409,
                "This username is already registered with another email."
            )

        user = User(
            username=username,
            email=email,
            email_notifications=request.email_notifications,
            flood_notifications=request.flood_notifications,
            heatwave_notifications=request.heatwave_notifications,
        )
        db.add(user)

    await db.commit()

    return {
        "status": "success",
        "message": "Email notification preferences saved.",
        "email": email,
        "email_notifications": user.email_notifications,
        "flood_notifications": user.flood_notifications,
        "heatwave_notifications": user.heatwave_notifications,
    }
