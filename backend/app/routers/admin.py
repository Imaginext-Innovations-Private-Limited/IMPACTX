
from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import db
from app.utils.security import get_current_user

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"]
)


# Admin-only access
def require_admin(current_user=Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user


# Convert MongoDB values into JSON-compatible values
def serialize_document(document):
    if isinstance(document, ObjectId):
        return str(document)

    if isinstance(document, datetime):
        return document.isoformat()

    if isinstance(document, dict):
        return {
            key: serialize_document(value)
            for key, value in document.items()
        }

    if isinstance(document, list):
        return [serialize_document(item) for item in document]

    return document


# Request model for report status updates
class StatusUpdate(BaseModel):
    status: str = Field(
        pattern="^(submitted|under_review|resolved|rejected)$"
    )


# 1. Admin dashboard statistics
@router.get("/stats")
def get_admin_stats(admin=Depends(require_admin)):

    total_reports = db.reports.count_documents({})

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
        "total_reports": total_reports,
        "submitted": submitted,
        "under_review": under_review,
        "resolved": resolved,
        "rejected": rejected,
        "total_citizens": total_citizens
    }


# 2. Get all pollution reports
@router.get("/reports")
def get_admin_reports(admin=Depends(require_admin)):

    reports = list(
        db.reports.find().sort("created_at", -1)
    )

    return [
        serialize_document(report)
        for report in reports
    ]


# 3. Update pollution report status
@router.patch("/reports/{report_id}/status")
def update_report_status(
    report_id: str,
    status_data: StatusUpdate,
    admin=Depends(require_admin)
):

    if not ObjectId.is_valid(report_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid report ID"
        )

    result = db.reports.update_one(
        {"_id": ObjectId(report_id)},
        {
            "$set": {
                "status": status_data.status,
                "updated_at": datetime.utcnow()
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

    return {
        "message": "Report status updated successfully",
        "report_id": report_id,
        "status": status_data.status
    }
