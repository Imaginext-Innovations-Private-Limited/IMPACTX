"""
Scheme, Insurance & Relief Notification Center Router.
Covers:
1. Four essential notification categories:
   a) Fellowships & Farmer Training Programs
   b) Government Subsidies
   c) Crop Insurance Schemes & Premium Dues
   d) Drought & Flood Relief Fund Application Deadlines
2. Document checklist status persistence (Aadhaar, Bhoomi RTC, Bank Passbook, Sowing Cert)
3. Unread count and mark-as-read endpoints
"""
from typing import Optional, List
import json
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
import models

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class ChecklistToggleRequest(BaseModel):
    is_completed: bool


@router.get("")
@router.get("/")
def get_notifications(
    category: Optional[str] = Query(None, description="training, subsidies, insurance, relief"),
    db: Session = Depends(get_db),
):
    """
    Fetch all notifications with their persistent document checklist progress.
    """
    q = db.query(models.Notification)
    if category and category != "all":
        q = q.filter(models.Notification.category == category)
    
    notifications = q.order_by(models.Notification.id.desc()).all()

    result = []
    for n in notifications:
        # Load checklist items and completion states
        progress_items = db.query(models.NotificationChecklistProgress).filter(
            models.NotificationChecklistProgress.notification_id == n.id
        ).all()

        checklist = []
        for p in progress_items:
            checklist.append({
                "id": p.id,
                "doc_key": p.doc_key,
                "doc_name": p.doc_name,
                "doc_name_kannada": p.doc_name_kannada,
                "is_completed": p.is_completed,
            })

        eligibility = []
        if n.eligibility_rules:
            try:
                eligibility = json.loads(n.eligibility_rules)
            except Exception:
                eligibility = [n.eligibility_rules]

        completed_count = sum(1 for c in checklist if c["is_completed"])
        total_docs = len(checklist)
        doc_progress_pct = int((completed_count / total_docs * 100)) if total_docs > 0 else 0

        result.append({
            "id": n.id,
            "category": n.category,
            "title": n.title,
            "title_kannada": n.title_kannada,
            "summary": n.summary,
            "summary_kannada": n.summary_kannada,
            "benefit_amount": n.benefit_amount,
            "deadline_date": n.deadline_date,
            "deadline_timestamp": n.deadline_timestamp,
            "urgency": n.urgency,
            "authority": n.authority,
            "portal_url": n.portal_url,
            "helpline": n.helpline,
            "eligibility_rules": eligibility,
            "is_read": n.is_read,
            "checklist": checklist,
            "completed_docs": completed_count,
            "total_docs": total_docs,
            "doc_progress_pct": doc_progress_pct,
        })

    unread_count = db.query(models.Notification).filter(models.Notification.is_read == False).count()

    return {
        "unread_count": unread_count,
        "total": len(result),
        "notifications": result,
    }


@router.get("/unread-count")
def get_unread_count(db: Session = Depends(get_db)):
    """Quick lookup for header bell badge."""
    count = db.query(models.Notification).filter(models.Notification.is_read == False).count()
    return {"unread_count": count}


@router.post("/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    """Mark a notification as read."""
    n = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    db.commit()
    return {"success": True, "notification_id": notification_id, "is_read": True}


@router.post("/mark-all-read")
def mark_all_read(db: Session = Depends(get_db)):
    """Mark all notifications as read."""
    db.query(models.Notification).update({models.Notification.is_read: True})
    db.commit()
    return {"success": True}


@router.post("/{notification_id}/checklist/{doc_key}")
def toggle_checklist_item(
    notification_id: int,
    doc_key: str,
    req: ChecklistToggleRequest,
    db: Session = Depends(get_db),
):
    """
    Toggle and persist the check-off progress of an individual required document in SQLite.
    """
    item = db.query(models.NotificationChecklistProgress).filter(
        models.NotificationChecklistProgress.notification_id == notification_id,
        models.NotificationChecklistProgress.doc_key == doc_key,
    ).first()

    if not item:
        # Create record if not already seeded
        item = models.NotificationChecklistProgress(
            notification_id=notification_id,
            doc_key=doc_key,
            doc_name=doc_key.replace("_", " ").title(),
            is_completed=req.is_completed,
            updated_at=datetime.utcnow(),
        )
        db.add(item)
    else:
        item.is_completed = req.is_completed
        item.updated_at = datetime.utcnow()

    db.commit()

    # Calculate overall progress for this notification
    total = db.query(models.NotificationChecklistProgress).filter(
        models.NotificationChecklistProgress.notification_id == notification_id
    ).count()
    completed = db.query(models.NotificationChecklistProgress).filter(
        models.NotificationChecklistProgress.notification_id == notification_id,
        models.NotificationChecklistProgress.is_completed == True
    ).count()

    pct = int((completed / total * 100)) if total > 0 else 0

    return {
        "success": True,
        "notification_id": notification_id,
        "doc_key": doc_key,
        "is_completed": item.is_completed,
        "completed_count": completed,
        "total_count": total,
        "progress_pct": pct,
    }
