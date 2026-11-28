
from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path
from datetime import datetime, timezone

from app.utils.security import get_current_user
from app.ai.pollution_detection import detect_pollution
from app.database import db

router = APIRouter(
    prefix="/api/ai",
    tags=["AI Pollution Detection"]
)

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"

# MongoDB detections collection
detections_collection = db["detections"]


@router.post("/detect/{filename}")
def detect_pollution_api(
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    # Prevent access to files outside the uploads folder
    if Path(filename).name != filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename"
        )

    image_path = UPLOAD_DIR / filename

    if not image_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Uploaded image not found"
        )

    try:
        # Run custom AquaWatch AI model
        result = detect_pollution(str(image_path))

        # Prepare detection record
        detection_record = {
            "user_id": str(current_user["_id"]),
            "filename": filename,
            "model": result["model"],
            "total_detections": result["total_detections"],
            "detections": result["detections"],
            "created_at": datetime.now(timezone.utc)
        }

        # Save results in MongoDB
        saved_record = detections_collection.insert_one(
            detection_record
        )

        return {
            "message": "AI image analysis completed and saved",
            "detection_id": str(saved_record.inserted_id),
            "filename": filename,
            "user_id": str(current_user["_id"]),
            "analysis": result
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"AI detection or database saving failed: {str(error)}"
        )
