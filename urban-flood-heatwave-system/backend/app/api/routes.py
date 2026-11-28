"""API Router — Safe Route and Cooling Centre endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.route_service import route_service

router = APIRouter()


@router.get("/safe-route")
async def safe_route(
    origin_lat: float = Query(...),
    origin_lon: float = Query(...),
    dest_lat: float = Query(...),
    dest_lon: float = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Get a driving/walking route with flood-zone warnings overlaid."""
    return await route_service.get_safe_route(origin_lat, origin_lon, dest_lat, dest_lon, db)


@router.get("/cooling-centres")
async def cooling_centres(
    lat: float = Query(...),
    lon: float = Query(...),
    limit: int = Query(5),
    db: AsyncSession = Depends(get_db),
):
    """Find the nearest open cooling centres to a location."""
    return await route_service.nearest_cooling_centres(lat, lon, db, limit)
