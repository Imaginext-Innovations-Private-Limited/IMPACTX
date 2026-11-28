"""API Router — Citizen Photo Reports."""

import shutil, uuid
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.citizen_report import CitizenReport
from app.ml.photo_analyser import analyse_citizen_photo
from typing import Optional

router = APIRouter()
UPLOAD_DIR = Path("uploads/reports")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/")
async def submit_report(
    city: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    description: Optional[str] = Form(None),
    reporter_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    report_type: str = Form("FLOOD"),
    photo: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    """Citizens submit a flood or heat report with an optional photo."""
    photo_path = None
    ai_result = {}

    if photo:
        ext = Path(photo.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4()}{ext}"
        dest = UPLOAD_DIR / filename
        with dest.open("wb") as f:
            shutil.copyfileobj(photo.file, f)
        photo_path = str(dest)
        ai_result = await analyse_citizen_photo(photo_path)

    report = CitizenReport(
        reporter_name=reporter_name,
        phone=phone,
        city=city,
        latitude=latitude,
        longitude=longitude,
        description=description,
        photo_path=photo_path,
        report_type=report_type,
        ai_label=ai_result.get("category"),
        ai_confidence=ai_result.get("confidence"),
        ai_summary=ai_result.get("description"),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return {
        "report_id": report.id,
        "ai_analysis": ai_result,
        "status": "received",
        "message": "Thank you for your report. It has been recorded and will help improve alerts.",
    }


@router.get("/")
async def list_reports(
    city: Optional[str] = Query(None),
    report_type: Optional[str] = Query(None),
    limit: int = Query(50),
    db: AsyncSession = Depends(get_db),
):
    q = select(CitizenReport).order_by(CitizenReport.created_at.desc()).limit(limit)
    if city:
        q = q.where(CitizenReport.city == city)
    if report_type:
        q = q.where(CitizenReport.report_type == report_type)
    result = await db.execute(q)
    reports = result.scalars().all()
    return [
        {
            "id": r.id,
            "city": r.city,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "description": r.description,
            "report_type": r.report_type,
            "ai_label": r.ai_label,
            "ai_confidence": r.ai_confidence,
            "ai_summary": r.ai_summary,
            "photo_url": f"/uploads/{Path(r.photo_path).name}" if r.photo_path else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]
