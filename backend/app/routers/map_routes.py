
from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends

from app.database import db
from app.utils.security import get_current_user


router = APIRouter(
    prefix="/api/map",
    tags=["Public Map"]
)


def serialize_date(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@router.get("/reports")
def get_map_reports(current_user=Depends(get_current_user)):
    """
    Return limited pollution report information for
    authenticated citizens and administrators.
    Private user information is never included.
    """

    projection = {
        "_id": 1,
        "lake_name": 1,
        "latitude": 1,
        "longitude": 1,
        "description": 1,
        "pollution_type": 1,
        "status": 1,
        "created_at": 1
    }

    reports = list(
        db.reports.find({}, projection).sort("created_at", -1)
    )

    result = []

    for report in reports:
        result.append({
            "id": str(report.get("_id", "")),
            "lake_name": report.get("lake_name"),
            "latitude": report.get("latitude"),
            "longitude": report.get("longitude"),
            "description": report.get("description"),
            "pollution_type": report.get("pollution_type"),
            "status": report.get("status", "submitted"),
            "created_at": serialize_date(
                report.get("created_at")
            )
        })

    return {
        "total": len(result),
        "reports": result
    }
