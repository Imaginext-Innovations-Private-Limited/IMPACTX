"""
Route Service — finds safe routes avoiding flooded zones using OSRM.
Also locates nearest cooling centres.
"""

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from math import radians, cos, sin, asin, sqrt
from app.models.flood_zone import FloodZone
from app.models.cooling_center import CoolingCenter
from app.core.config import settings


def haversine(lat1, lon1, lat2, lon2) -> float:
    """Return distance in kilometres between two coordinates."""
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * asin(sqrt(a))


class RouteService:

    async def get_safe_route(
        self,
        origin_lat: float, origin_lon: float,
        dest_lat: float, dest_lon: float,
        db: AsyncSession,
    ) -> dict:
        """
        Fetches a route from OSRM and annotates it with flood risk warnings.
        """
        url = (
            f"{settings.OSRM_BASE_URL}/route/v1/driving/"
            f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
            f"?overview=full&geometries=geojson&steps=true"
        )
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(url)
                r.raise_for_status()
                osrm_data = r.json()
        except Exception as e:
            return {"error": str(e), "route": None}

        # Fetch HIGH/CRITICAL flood zones
        result = await db.execute(
            select(FloodZone).where(FloodZone.risk_level.in_(["HIGH", "CRITICAL"]))
        )
        risky_zones = result.scalars().all()

        route = osrm_data["routes"][0] if osrm_data.get("routes") else {}
        warnings = []

        coords = route.get("geometry", {}).get("coordinates", [])
        for lon, lat in coords:
            for zone in risky_zones:
                dist = haversine(lat, lon, zone.latitude, zone.longitude)
                if dist < 0.3:  # within 300m
                    warnings.append({
                        "zone_id": zone.zone_id,
                        "zone_name": zone.name,
                        "risk_level": zone.risk_level,
                        "lat": zone.latitude,
                        "lon": zone.longitude,
                    })

        return {
            "route": route,
            "distance_m": route.get("distance", 0),
            "duration_s": route.get("duration", 0),
            "flood_warnings": warnings,
            "is_safe": len(warnings) == 0,
        }

    async def nearest_cooling_centres(
        self, lat: float, lon: float, db: AsyncSession, limit: int = 5
    ) -> list:
        result = await db.execute(
            select(CoolingCenter).where(CoolingCenter.is_open == True)
        )
        centers = result.scalars().all()
        scored = sorted(
            centers,
            key=lambda c: haversine(lat, lon, c.latitude, c.longitude)
        )[:limit]

        return [
            {
                "id": c.id,
                "name": c.name,
                "center_type": c.center_type,
                "address": c.address,
                "latitude": c.latitude,
                "longitude": c.longitude,
                "distance_km": round(haversine(lat, lon, c.latitude, c.longitude), 2),
                "capacity": c.capacity,
                "current_occupancy": c.current_occupancy,
                "has_water": c.has_water,
                "has_medical": c.has_medical,
                "phone": c.phone,
            }
            for c in scored
        ]


route_service = RouteService()
