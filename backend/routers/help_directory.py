"""
Farmer Help & Service Directory Router.
Covers local agricultural service contacts across 10 Karnataka categories
with category filtering, text search, creation, and deletion.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator

from database import get_db
import models

router = APIRouter(prefix="/api/help", tags=["help"])


class ServiceContactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    category: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=3, max_length=50)
    location: str = Field(..., min_length=1, max_length=150)
    notes: Optional[str] = None

    @field_validator("name", "category", "phone", "location")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace")
        return cleaned


class ServiceContactOut(BaseModel):
    id: int
    name: str
    category: str
    phone: str
    location: str
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/contacts", response_model=List[ServiceContactOut])
def get_service_contacts(
    category: Optional[str] = Query(None, description="Filter by service category"),
    search: Optional[str] = Query(None, description="Search by name, location, or notes"),
    db: Session = Depends(get_db),
):
    """Return agricultural service contacts, optionally filtered by category or search query."""
    q = db.query(models.ServiceContact)

    if category and category.strip().lower() != "all":
        q = q.filter(models.ServiceContact.category.ilike(f"%{category.strip()}%"))

    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.filter(
            or_(
                models.ServiceContact.name.ilike(term),
                models.ServiceContact.location.ilike(term),
                models.ServiceContact.notes.ilike(term),
            )
        )

    return q.order_by(models.ServiceContact.id.desc()).all()


@router.post("/contacts", response_model=ServiceContactOut, status_code=201)
def create_service_contact(
    payload: ServiceContactCreate,
    db: Session = Depends(get_db),
):
    """Create a new agricultural service contact."""
    contact = models.ServiceContact(
        name=payload.name,
        category=payload.category,
        phone=payload.phone,
        location=payload.location,
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/contacts/{contact_id}")
def delete_service_contact(contact_id: int, db: Session = Depends(get_db)):
    """Delete a service contact by ID."""
    contact = db.query(models.ServiceContact).filter(models.ServiceContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Service contact not found")
    db.delete(contact)
    db.commit()
    return {"success": True, "deleted_id": contact_id}
