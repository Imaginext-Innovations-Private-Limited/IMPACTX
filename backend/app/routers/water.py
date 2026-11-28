
import math

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import db
from app.schemas.water import WaterQualityReading
from app.utils.security import get_current_user


router = APIRouter(
    prefix="/api/water",
    tags=["Water Quality"]
)


# -----------------------------------
# CREATE MANUAL WATER QUALITY READING
# -----------------------------------

@router.post("/readings")
async def create_water_reading(
    reading: WaterQualityReading,
    current_user: dict = Depends(get_current_user)
):
    try:
        reading_data = reading.model_dump()

        reading_data["user_id"] = str(current_user["_id"])
        reading_data["created_at"] = datetime.now(timezone.utc)
        reading_data["source"] = "manual"
        reading_data["data_type"] = "manual"

        result = db["water_readings"].insert_one(reading_data)

        return {
            "message": "Water quality reading saved successfully",
            "reading_id": str(result.inserted_id)
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to save water quality reading"
        )


# -----------------------------------
# GET ALL WATER QUALITY READINGS
# -----------------------------------

@router.get("/readings")
async def get_water_readings(
    current_user: dict = Depends(get_current_user)
):
    readings = list(
        db["water_readings"].find().sort("created_at", -1)
    )

    for reading in readings:
        reading["_id"] = str(reading["_id"])

        if isinstance(reading.get("created_at"), datetime):
            reading["created_at"] = reading["created_at"].isoformat()

        if isinstance(reading.get("measurement_date"), datetime):
            reading["measurement_date"] = reading["measurement_date"].isoformat()

    return {
        "total_readings": len(readings),
        "readings": readings
    }


# -----------------------------------
# GET CURRENT USER'S READINGS
# -----------------------------------

@router.get("/my-readings")
async def get_my_water_readings(
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])

    readings = list(
        db["water_readings"].find({
            "user_id": user_id
        }).sort("created_at", -1)
    )

    for reading in readings:
        reading["_id"] = str(reading["_id"])

        if isinstance(reading.get("created_at"), datetime):
            reading["created_at"] = reading["created_at"].isoformat()

    return {
        "total_readings": len(readings),
        "readings": readings
    }


# -----------------------------------
# FIND NEARBY HISTORICAL CPCB DATA
# -----------------------------------

@router.get("/historical/nearby")
async def get_nearby_historical_readings(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=25, gt=0, le=500),
    current_user: dict = Depends(get_current_user)
):

    def calculate_distance(lat1, lon1, lat2, lon2):
        earth_radius = 6371

        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        lat2 = math.radians(lat2)
        lon2 = math.radians(lon2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1)
            * math.cos(lat2)
            * math.sin(dlon / 2) ** 2
        )

        return earth_radius * 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )

    records = list(
        db["water_readings"].find({
            "source": "CPCB",
            "data_type": "historical"
        })
    )

    nearby = []

    for record in records:

        station_lat = record.get("latitude")
        station_lon = record.get("longitude")

        if station_lat is None or station_lon is None:
            continue

        distance = calculate_distance(
            latitude,
            longitude,
            station_lat,
            station_lon
        )

        if distance <= radius_km:

            record["_id"] = str(record["_id"])
            record["distance_km"] = round(distance, 2)

            if isinstance(record.get("measurement_date"), datetime):
                record["measurement_date"] = (
                    record["measurement_date"].isoformat()
                )

            if isinstance(record.get("created_at"), datetime):
                record["created_at"] = (
                    record["created_at"].isoformat()
                )

            nearby.append(record)

    nearby.sort(key=lambda item: item["distance_km"])

    return {
        "total_readings": len(nearby),
        "search_radius_km": radius_km,
        "data_source": "CPCB",
        "data_type": "Historical monitoring data",
        "readings": nearby[:100]
    }
