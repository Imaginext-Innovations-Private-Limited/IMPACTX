"""Commodities router – APMC market rates for Karnataka."""
import random
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
import models

router = APIRouter(prefix="/api/commodities", tags=["commodities"])


class CommodityOut(BaseModel):
    id: int
    name: str
    name_kannada: Optional[str]
    name_hindi: Optional[str]
    category: str
    unit: str
    current_price: float
    previous_price: float
    min_price: Optional[float]
    max_price: Optional[float]
    market: str
    state: str
    trend: str          # "up" | "down" | "stable"
    change_pct: float
    updated_at: datetime

    class Config:
        from_attributes = True


def _enrich(c: models.Commodity) -> dict:
    diff = c.current_price - c.previous_price
    pct = round((diff / c.previous_price) * 100, 2) if c.previous_price else 0
    trend = "up" if diff > 0 else ("down" if diff < 0 else "stable")
    return {
        **{col.name: getattr(c, col.name) for col in c.__table__.columns},
        "trend": trend,
        "change_pct": pct,
    }


@router.get("/", response_model=list[CommodityOut])
def list_commodities(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Return all commodities, optionally filtered by category."""
    q = db.query(models.Commodity)
    if category:
        q = q.filter(models.Commodity.category == category)
    return [_enrich(c) for c in q.all()]


@router.get("/ticker", response_model=list[CommodityOut])
def ticker_commodities(db: Session = Depends(get_db)):
    """
    Return the 6 headline commodities shown in the sticky ticker bar.
    Paddy, Areca, Ginger, Corn, Pepper, Coconut.
    """
    names_filter = ["Paddy (Fine)", "Areca Nut (Chali)", "Ginger (Fresh)",
                    "Corn / Maize", "Black Pepper", "Coconut (Copra)"]
    commodities = (
        db.query(models.Commodity)
        .filter(models.Commodity.name.in_(names_filter))
        .all()
    )
    return [_enrich(c) for c in commodities]


@router.get("/{commodity_id}", response_model=CommodityOut)
def get_commodity(commodity_id: int, db: Session = Depends(get_db)):
    c = db.query(models.Commodity).filter(models.Commodity.id == commodity_id).first()
    if not c:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Commodity not found")
    return _enrich(c)


@router.post("/{commodity_id}/simulate-tick")
def simulate_price_tick(commodity_id: int, db: Session = Depends(get_db)):
    """
    Dev utility: randomly nudge a commodity price ±3% to simulate live feed.
    In production this would be replaced by a webhook / scheduled job
    calling the eNAM / Agmarknet API.
    """
    c = db.query(models.Commodity).filter(models.Commodity.id == commodity_id).first()
    if not c:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Commodity not found")
    c.previous_price = c.current_price
    factor = random.uniform(0.97, 1.03)
    c.current_price = round(c.current_price * factor, 2)
    c.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    return _enrich(c)
