"""
Livestock & Pet Marketplace Router.
Covers Poultry, Goats & Sheep, Pets, and Domestic Animals listings
with category/price filtering, sorting, creation, and deletion.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator

from database import get_db
import models

router = APIRouter(prefix="/api/livestock-pets", tags=["livestock-pets"])


class LivestockPetListingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=50)
    breed_or_type: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(1, ge=1)
    age: Optional[str] = Field(None, max_length=50)
    price_inr: float = Field(..., ge=0)
    location: str = Field(..., min_length=1, max_length=150)
    owner_name: str = Field(..., min_length=1, max_length=150)
    owner_phone: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None

    @field_validator("title", "category", "breed_or_type", "location", "owner_name", "owner_phone")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace")
        return cleaned


class LivestockPetListingOut(BaseModel):
    id: int
    title: str
    category: str
    breed_or_type: str
    quantity: int
    age: Optional[str] = None
    price_inr: float
    location: str
    owner_name: str
    owner_phone: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[LivestockPetListingOut])
@router.get("/", response_model=List[LivestockPetListingOut])
def get_livestock_pet_listings(
    category: Optional[str] = Query(None, description="Poultry, Goats & Sheep, Pets, or Domestic Animals"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    sort_by: Optional[str] = Query(None, description="price_asc, price_desc, or newest"),
    db: Session = Depends(get_db),
):
    """List livestock and pet marketplace entries with optional filtering and sorting."""
    q = db.query(models.LivestockPetListing)

    if category and category.strip().lower() != "all":
        q = q.filter(models.LivestockPetListing.category.ilike(f"%{category.strip()}%"))

    if min_price is not None:
        q = q.filter(models.LivestockPetListing.price_inr >= min_price)

    if max_price is not None:
        q = q.filter(models.LivestockPetListing.price_inr <= max_price)

    if sort_by == "price_asc":
        q = q.order_by(models.LivestockPetListing.price_inr.asc())
    elif sort_by == "price_desc":
        q = q.order_by(models.LivestockPetListing.price_inr.desc())
    else:
        q = q.order_by(models.LivestockPetListing.created_at.desc(), models.LivestockPetListing.id.desc())

    return q.all()


@router.post("", response_model=LivestockPetListingOut, status_code=201)
@router.post("/", response_model=LivestockPetListingOut, status_code=201)
def create_livestock_pet_listing(
    payload: LivestockPetListingCreate,
    db: Session = Depends(get_db),
):
    """Create a new livestock or pet marketplace listing."""
    listing = models.LivestockPetListing(
        title=payload.title,
        category=payload.category,
        breed_or_type=payload.breed_or_type,
        quantity=payload.quantity,
        age=payload.age.strip() if payload.age else None,
        price_inr=payload.price_inr,
        location=payload.location,
        owner_name=payload.owner_name,
        owner_phone=payload.owner_phone,
        description=payload.description.strip() if payload.description else None,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/{listing_id}")
def delete_livestock_pet_listing(listing_id: int, db: Session = Depends(get_db)):
    """Delete a livestock or pet listing by ID."""
    listing = db.query(models.LivestockPetListing).filter(models.LivestockPetListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    db.delete(listing)
    db.commit()
    return {"success": True, "deleted_id": listing_id}
