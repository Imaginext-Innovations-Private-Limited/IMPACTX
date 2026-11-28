
import uuid
from pathlib import Path
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File
)

from app.database import db
from app.schemas.report import PollutionReport
from app.utils.security import (
    get_current_user,
    get_current_admin
)

router = APIRouter(
    prefix="/api/reports",
    tags=["Pollution Reports"]
)

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_STATUSES = {
    "under_review",
    "resolved",
    "rejected"
}


def serialize_report(report):
    report["id"] = str(report.pop("_id"))

    if report.get("created_at"):
        report["created_at"] = report["created_at"].isoformat()

    if report.get("updated_at"):
        report["updated_at"] = report["updated_at"].isoformat()

    return report


# 1. Create pollution report - Citizen
@router.post("/create")
def create_report(
    report: PollutionReport,
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])

    if report.detection_id:
        try:
            detection_object_id = ObjectId(report.detection_id)
        except (InvalidId, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Invalid detection ID"
            )

        detection = db.detections.find_one({
            "_id": detection_object_id,
            "user_id": user_id
        })

        if not detection:
            raise HTTPException(
                status_code=404,
                detail="AI detection not found for this user"
            )

        expected_photo_url = f"/uploads/{detection['filename']}"

        if report.photo_url != expected_photo_url:
            raise HTTPException(
                status_code=400,
                detail="Report photo does not match the analyzed image"
            )

    new_report = {
        "user_id": user_id,
        "user_name": current_user["name"],
        "lake_name": report.lake_name,
        "description": report.description,
        "latitude": report.latitude,
        "longitude": report.longitude,
        "pollution_type": report.pollution_type,
        "photo_url": report.photo_url,
        "detection_id": report.detection_id,
        "status": "submitted",
        "created_at": datetime.now(timezone.utc)
    }

    result = db.reports.insert_one(new_report)

    return {
        "message": "Pollution report submitted successfully",
        "report_id": str(result.inserted_id),
        "detection_id": report.detection_id,
        "user_id": user_id,
        "photo_url": report.photo_url,
        "status": "submitted"
    }


# 2. Get all reports - Admin only
@router.get("/")
def get_reports(
    current_admin: dict = Depends(get_current_admin)
):
    reports = list(
        db.reports.find().sort("created_at", -1)
    )

    reports = [serialize_report(r) for r in reports]

    return {
        "total_reports": len(reports),
        "reports": reports
    }


# 3. Get reports submitted by logged-in citizen
@router.get("/my-reports")
def get_my_reports(
    current_user: dict = Depends(get_current_user)
):
    reports = list(
        db.reports.find({
            "user_id": str(current_user["_id"])
        }).sort("created_at", -1)
    )

    reports = [serialize_report(r) for r in reports]

    return {
        "total_reports": len(reports),
        "reports": reports
    }


# 4. Admin dashboard statistics
@router.get("/admin/stats")
def get_admin_stats(
    current_admin: dict = Depends(get_current_admin)
):
    total = db.reports.count_documents({})

    submitted = db.reports.count_documents({
        "status": "submitted"
    })

    under_review = db.reports.count_documents({
        "status": "under_review"
    })

    resolved = db.reports.count_documents({
        "status": "resolved"
    })

    rejected = db.reports.count_documents({
        "status": "rejected"
    })

    total_citizens = db.users.count_documents({
        "role": "citizen"
    })

    return {
        "total_reports": total,
        "submitted": submitted,
        "under_review": under_review,
        "resolved": resolved,
        "rejected": rejected,
        "total_citizens": total_citizens
    }


# 5. Admin updates report status
@router.patch("/admin/{report_id}/status")
def update_report_status(
    report_id: str,
    new_status: str,
    current_admin: dict = Depends(get_current_admin)
):
    if new_status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Use under_review, resolved or rejected."
        )

    try:
        report_object_id = ObjectId(report_id)
    except (InvalidId, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid report ID"
        )

    report = db.reports.find_one({
        "_id": report_object_id
    })

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

    db.reports.update_one(
        {"_id": report_object_id},
        {
            "$set": {
                "status": new_status,
                "updated_at": datetime.now(timezone.utc),
                "reviewed_by": str(current_admin["_id"])
            }
        }
    )

    return {
        "message": "Report status updated successfully",
        "report_id": report_id,
        "old_status": report.get("status", "submitted"),
        "new_status": new_status
    }


# 6. Upload pollution photograph
@router.post("/upload-photo")
async def upload_photo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp"
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and WEBP images are allowed"
        )

    image_data = await file.read()

    if not image_data:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty"
        )

    if len(image_data) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Image size must be less than 5 MB"
        )

    filename = f"{uuid.uuid4().hex}{allowed_types[file.content_type]}"
    file_path = UPLOAD_DIR / filename

    with open(file_path, "wb") as image:
        image.write(image_data)

    photo_url = f"/uploads/{filename}"

    return {
        "message": "Photo uploaded successfully",
        "filename": filename,
        "photo_url": photo_url,
        "user_id": str(current_user["_id"])
    }
