"""Commodities router – Pan-Indian APMC / Agmarknet market rates with SQLite TTL cache."""
import logging
import random
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
import httpx
from sqlalchemy.orm import Session
from pydantic import BaseModel

import config
from database import get_db
import models
from location_service import resolve_state

logger = logging.getLogger("commodities")
router = APIRouter(prefix="/api/commodities", tags=["commodities"])

CACHE_TTL_HOURS = 6
DATA_GOV_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"

# Comprehensive state fallback crops and APMC mandi profiles across India
STATE_FALLBACK_COMMODITIES: Dict[str, List[Dict[str, Any]]] = {
    "Telangana": [
        {"name": "Cotton (Kapas)", "category": "fiber", "modal": 7200.0, "min": 6900.0, "max": 7500.0, "market": "Warangal Enumamula", "district": "Warangal"},
        {"name": "Chilli (Red)", "category": "spice", "modal": 18500.0, "min": 17000.0, "max": 20000.0, "market": "Khammam APMC", "district": "Khammam"},
        {"name": "Paddy (Fine)", "category": "grain", "modal": 2320.0, "min": 2200.0, "max": 2450.0, "market": "Nizamabad APMC", "district": "Nizamabad"},
        {"name": "Corn / Maize", "category": "grain", "modal": 2180.0, "min": 2050.0, "max": 2320.0, "market": "Bowenpally APMC", "district": "Hyderabad"},
        {"name": "Soybean", "category": "oilseed", "modal": 4700.0, "min": 4450.0, "max": 4900.0, "market": "Adilabad APMC", "district": "Adilabad"},
        {"name": "Turmeric", "category": "spice", "modal": 13800.0, "min": 12900.0, "max": 14600.0, "market": "Nizamabad APMC", "district": "Nizamabad"},
        {"name": "Tomato", "category": "vegetable", "modal": 2100.0, "min": 1800.0, "max": 2400.0, "market": "Gaddiannaram APMC", "district": "Hyderabad"},
        {"name": "Onion", "category": "vegetable", "modal": 2350.0, "min": 2000.0, "max": 2650.0, "market": "Bowenpally APMC", "district": "Hyderabad"},
    ],
    "Maharashtra": [
        {"name": "Onion (Red)", "category": "vegetable", "modal": 2450.0, "min": 2100.0, "max": 2800.0, "market": "Lasalgaon APMC", "district": "Nashik"},
        {"name": "Soybean", "category": "oilseed", "modal": 4650.0, "min": 4400.0, "max": 4850.0, "market": "Latur APMC", "district": "Latur"},
        {"name": "Cotton (Kapas)", "category": "fiber", "modal": 7150.0, "min": 6800.0, "max": 7450.0, "market": "Akola APMC", "district": "Akola"},
        {"name": "Tur / Red Gram", "category": "pulse", "modal": 9800.0, "min": 9400.0, "max": 10200.0, "market": "Nagpur APMC", "district": "Nagpur"},
        {"name": "Pomegranate", "category": "fruit", "modal": 8500.0, "min": 7800.0, "max": 9200.0, "market": "Solapur APMC", "district": "Solapur"},
        {"name": "Wheat", "category": "grain", "modal": 2400.0, "min": 2280.0, "max": 2520.0, "market": "Pune APMC", "district": "Pune"},
    ],
    "Tamil Nadu": [
        {"name": "Paddy (Fine)", "category": "grain", "modal": 2350.0, "min": 2200.0, "max": 2500.0, "market": "Thanjavur Regulated Market", "district": "Thanjavur"},
        {"name": "Coconut (Copra)", "category": "plantation", "modal": 9400.0, "min": 9000.0, "max": 9800.0, "market": "Pollachi Market", "district": "Coimbatore"},
        {"name": "Turmeric", "category": "spice", "modal": 14200.0, "min": 13500.0, "max": 15000.0, "market": "Erode Market", "district": "Erode"},
        {"name": "Banana (Nendran)", "category": "fruit", "modal": 3200.0, "min": 2800.0, "max": 3600.0, "market": "Trichy Market", "district": "Tiruchirappalli"},
        {"name": "Groundnut", "category": "oilseed", "modal": 6800.0, "min": 6400.0, "max": 7100.0, "market": "Vellore Market", "district": "Vellore"},
        {"name": "Black Pepper", "category": "spice", "modal": 61000.0, "min": 58000.0, "max": 63500.0, "market": "Salem Market", "district": "Salem"},
    ],
    "Andhra Pradesh": [
        {"name": "Chilli (Red)", "category": "spice", "modal": 19200.0, "min": 18000.0, "max": 20500.0, "market": "Guntur Yard APMC", "district": "Guntur"},
        {"name": "Paddy (Fine)", "category": "grain", "modal": 2300.0, "min": 2180.0, "max": 2420.0, "market": "Tenali APMC", "district": "Guntur"},
        {"name": "Cotton (Kapas)", "category": "fiber", "modal": 7250.0, "min": 6900.0, "max": 7500.0, "market": "Kurnool APMC", "district": "Kurnool"},
        {"name": "Groundnut", "category": "oilseed", "modal": 6600.0, "min": 6250.0, "max": 6900.0, "market": "Ananthapur APMC", "district": "Anantapur"},
        {"name": "Tomato", "category": "vegetable", "modal": 2050.0, "min": 1750.0, "max": 2350.0, "market": "Madanapalle APMC", "district": "Annamayya"},
        {"name": "Corn / Maize", "category": "grain", "modal": 2170.0, "min": 2040.0, "max": 2300.0, "market": "Rajahmundry APMC", "district": "East Godavari"},
    ],
    "Punjab": [
        {"name": "Wheat", "category": "grain", "modal": 2325.0, "min": 2275.0, "max": 2400.0, "market": "Khanna Mandi", "district": "Ludhiana"},
        {"name": "Paddy (Basmati)", "category": "grain", "modal": 3850.0, "min": 3600.0, "max": 4100.0, "market": "Amritsar Mandi", "district": "Amritsar"},
        {"name": "Corn / Maize", "category": "grain", "modal": 2150.0, "min": 1950.0, "max": 2300.0, "market": "Hoshiarpur Mandi", "district": "Hoshiarpur"},
        {"name": "Cotton (Kapas)", "category": "fiber", "modal": 7050.0, "min": 6700.0, "max": 7350.0, "market": "Bathinda Mandi", "district": "Bathinda"},
        {"name": "Mustard", "category": "oilseed", "modal": 5500.0, "min": 5250.0, "max": 5750.0, "market": "Patiala Mandi", "district": "Patiala"},
        {"name": "Potato", "category": "vegetable", "modal": 1450.0, "min": 1250.0, "max": 1700.0, "market": "Jalandhar Mandi", "district": "Jalandhar"},
    ],
    "Uttar Pradesh": [
        {"name": "Wheat", "category": "grain", "modal": 2310.0, "min": 2275.0, "max": 2380.0, "market": "Lucknow Mandi", "district": "Lucknow"},
        {"name": "Potato", "category": "vegetable", "modal": 1650.0, "min": 1400.0, "max": 1900.0, "market": "Agra Mandi", "district": "Agra"},
        {"name": "Paddy (Fine)", "category": "grain", "modal": 2280.0, "min": 2180.0, "max": 2400.0, "market": "Varanasi Mandi", "district": "Varanasi"},
        {"name": "Mustard", "category": "oilseed", "modal": 5450.0, "min": 5200.0, "max": 5700.0, "market": "Mathura Mandi", "district": "Mathura"},
        {"name": "Sugarcane Gur", "category": "plantation", "modal": 3900.0, "min": 3600.0, "max": 4200.0, "market": "Muzaffarnagar Mandi", "district": "Muzaffarnagar"},
        {"name": "Onion", "category": "vegetable", "modal": 2200.0, "min": 1900.0, "max": 2500.0, "market": "Kanpur Mandi", "district": "Kanpur"},
    ],
    "Gujarat": [
        {"name": "Groundnut", "category": "oilseed", "modal": 6450.0, "min": 6100.0, "max": 6800.0, "market": "Gondal APMC", "district": "Rajkot"},
        {"name": "Cotton (Kapas)", "category": "fiber", "modal": 7300.0, "min": 7000.0, "max": 7600.0, "market": "Rajkot APMC", "district": "Rajkot"},
        {"name": "Cumin (Jeera)", "category": "spice", "modal": 24500.0, "min": 23000.0, "max": 26000.0, "market": "Unjha APMC", "district": "Mehsana"},
        {"name": "Wheat", "category": "grain", "modal": 2420.0, "min": 2300.0, "max": 2550.0, "market": "Ahmedabad APMC", "district": "Ahmedabad"},
        {"name": "Castor Seed", "category": "oilseed", "modal": 5950.0, "min": 5700.0, "max": 6200.0, "market": "Palanpur APMC", "district": "Banaskantha"},
        {"name": "Sesame (Til)", "category": "oilseed", "modal": 12500.0, "min": 11800.0, "max": 13200.0, "market": "Amreli APMC", "district": "Amreli"},
    ],
    "West Bengal": [
        {"name": "Paddy (Fine)", "category": "grain", "modal": 2290.0, "min": 2150.0, "max": 2420.0, "market": "Bardhaman Mandi", "district": "Purba Bardhaman"},
        {"name": "Potato (Jyoti)", "category": "vegetable", "modal": 1580.0, "min": 1350.0, "max": 1800.0, "market": "Hooghly Mandi", "district": "Hooghly"},
        {"name": "Jute", "category": "fiber", "modal": 5250.0, "min": 5000.0, "max": 5500.0, "market": "Nadia Mandi", "district": "Nadia"},
        {"name": "Mustard", "category": "oilseed", "modal": 5520.0, "min": 5280.0, "max": 5750.0, "market": "Murshidabad Mandi", "district": "Murshidabad"},
        {"name": "Ginger (Fresh)", "category": "spice", "modal": 8200.0, "min": 7500.0, "max": 8900.0, "market": "Siliguri Market", "district": "Darjeeling"},
        {"name": "Cabbage", "category": "vegetable", "modal": 1200.0, "min": 950.0, "max": 1400.0, "market": "Kolkata Koley Market", "district": "Kolkata"},
    ],
    "Kerala": [
        {"name": "Black Pepper", "category": "spice", "modal": 62500.0, "min": 59000.0, "max": 65000.0, "market": "Kochi Market", "district": "Ernakulam"},
        {"name": "Coconut (Copra)", "category": "plantation", "modal": 9600.0, "min": 9100.0, "max": 10100.0, "market": "Kozhikode Market", "district": "Kozhikode"},
        {"name": "Cardamom", "category": "spice", "modal": 195000.0, "min": 185000.0, "max": 208000.0, "market": "Vandanmedu Spices Board", "district": "Idukki"},
        {"name": "Rubber (RSS-4)", "category": "plantation", "modal": 17800.0, "min": 17200.0, "max": 18400.0, "market": "Kottayam Market", "district": "Kottayam"},
        {"name": "Ginger (Fresh)", "category": "spice", "modal": 8600.0, "min": 7900.0, "max": 9300.0, "market": "Wayanad Market", "district": "Wayanad"},
        {"name": "Banana (Nendran)", "category": "fruit", "modal": 3400.0, "min": 3000.0, "max": 3800.0, "market": "Thrissur Market", "district": "Thrissur"},
    ],
    "Madhya Pradesh": [
        {"name": "Soybean", "category": "oilseed", "modal": 4680.0, "min": 4450.0, "max": 4890.0, "market": "Ujjain Mandi", "district": "Ujjain"},
        {"name": "Wheat (Sharbati)", "category": "grain", "modal": 2850.0, "min": 2650.0, "max": 3100.0, "market": "Sehore Mandi", "district": "Sehore"},
        {"name": "Gram (Chana)", "category": "pulse", "modal": 5850.0, "min": 5500.0, "max": 6150.0, "market": "Indore Mandi", "district": "Indore"},
        {"name": "Garlic", "category": "spice", "modal": 12500.0, "min": 11000.0, "max": 14000.0, "market": "Mandsaur Mandi", "district": "Mandsaur"},
        {"name": "Mustard", "category": "oilseed", "modal": 5400.0, "min": 5150.0, "max": 5650.0, "market": "Morena Mandi", "district": "Morena"},
        {"name": "Corn / Maize", "category": "grain", "modal": 2160.0, "min": 2000.0, "max": 2300.0, "market": "Chhindwara Mandi", "district": "Chhindwara"},
    ],
    "Rajasthan": [
        {"name": "Mustard", "category": "oilseed", "modal": 5550.0, "min": 5300.0, "max": 5800.0, "market": "Bharatpur Mandi", "district": "Bharatpur"},
        {"name": "Cumin (Jeera)", "category": "spice", "modal": 25200.0, "min": 23500.0, "max": 27000.0, "market": "Jodhpur Mandi", "district": "Jodhpur"},
        {"name": "Guar Seed", "category": "pulse", "modal": 5350.0, "min": 5050.0, "max": 5650.0, "market": "Bikaner Mandi", "district": "Bikaner"},
        {"name": "Wheat", "category": "grain", "modal": 2340.0, "min": 2280.0, "max": 2420.0, "market": "Kota Mandi", "district": "Kota"},
        {"name": "Coriander", "category": "spice", "modal": 7400.0, "min": 6900.0, "max": 7900.0, "market": "Ramganj Mandi", "district": "Kota"},
        {"name": "Bajra (Pearl Millet)", "category": "grain", "modal": 2250.0, "min": 2100.0, "max": 2400.0, "market": "Jaipur Mandi", "district": "Jaipur"},
    ],
    "Haryana": [
        {"name": "Wheat", "category": "grain", "modal": 2330.0, "min": 2275.0, "max": 2400.0, "market": "Karnal Mandi", "district": "Karnal"},
        {"name": "Paddy (Basmati)", "category": "grain", "modal": 3900.0, "min": 3650.0, "max": 4150.0, "market": "Taraori Mandi", "district": "Karnal"},
        {"name": "Mustard", "category": "oilseed", "modal": 5480.0, "min": 5220.0, "max": 5700.0, "market": "Hisar Mandi", "district": "Hisar"},
        {"name": "Cotton (Kapas)", "category": "fiber", "modal": 7100.0, "min": 6750.0, "max": 7400.0, "market": "Sirsa Mandi", "district": "Sirsa"},
    ],
    "Bihar": [
        {"name": "Corn / Maize", "category": "grain", "modal": 2120.0, "min": 1950.0, "max": 2250.0, "market": "Gulabbagh Mandi", "district": "Purnia"},
        {"name": "Wheat", "category": "grain", "modal": 2300.0, "min": 2240.0, "max": 2380.0, "market": "Patna Mandi", "district": "Patna"},
        {"name": "Paddy (Fine)", "category": "grain", "modal": 2260.0, "min": 2120.0, "max": 2380.0, "market": "Buxar Mandi", "district": "Buxar"},
        {"name": "Potato", "category": "vegetable", "modal": 1550.0, "min": 1300.0, "max": 1780.0, "market": "Biharsharif Mandi", "district": "Nalanda"},
    ],
    "Odisha": [
        {"name": "Paddy (Fine)", "category": "grain", "modal": 2280.0, "min": 2183.0, "max": 2380.0, "market": "Bargarh Mandi", "district": "Bargarh"},
        {"name": "Turmeric", "category": "spice", "modal": 12800.0, "min": 11900.0, "max": 13600.0, "market": "Kandhamal Market", "district": "Kandhamal"},
        {"name": "Groundnut", "category": "oilseed", "modal": 6350.0, "min": 6000.0, "max": 6700.0, "market": "Jajpur Mandi", "district": "Jajpur"},
        {"name": "Ginger (Fresh)", "category": "spice", "modal": 7800.0, "min": 7100.0, "max": 8500.0, "market": "Koraput Mandi", "district": "Koraput"},
    ],
}


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


def _fetch_state_mandi_or_cache(state: str, district: Optional[str], db: Session) -> List[dict]:
    """Fetch state mandi prices from SQLite TTL cache, data.gov.in (if configured), or structured fallback."""
    cutoff = datetime.utcnow() - timedelta(hours=CACHE_TTL_HOURS)
    cached = (
        db.query(models.MandiPriceCache)
        .filter(models.MandiPriceCache.state == state, models.MandiPriceCache.cached_at >= cutoff)
        .all()
    )
    if cached:
        rows = cached
        if district:
            d_low = district.strip().lower()
            dist_rows = [r for r in rows if r.district and d_low in r.district.lower()]
            if dist_rows:
                rows = dist_rows
        out = []
        for r in rows:
            diff = r.modal_price - (r.previous_price or r.modal_price)
            pct = round((diff / r.previous_price) * 100, 2) if r.previous_price else 0.0
            trend = "up" if diff > 0 else ("down" if diff < 0 else "stable")
            out.append({
                "id": r.commodity_id or (10000 + r.id),
                "name": r.commodity,
                "name_kannada": None,
                "name_hindi": None,
                "category": r.category or "grain",
                "unit": r.unit or "quintal",
                "current_price": r.modal_price,
                "previous_price": r.previous_price or r.modal_price,
                "min_price": r.min_price,
                "max_price": r.max_price,
                "market": r.market or f"{state} APMC",
                "state": r.state,
                "trend": trend,
                "change_pct": pct,
                "updated_at": r.cached_at,
            })
        return out

    # Try live data.gov.in Agmarknet API if key is configured
    live_records = []
    if config.has_data_gov():
        try:
            params = {
                "api-key": config.DATA_GOV_API_KEY,
                "format": "json",
                "limit": 20,
                "filters[state]": state,
            }
            if district:
                params["filters[district]"] = district
            with httpx.Client(timeout=4.0) as client:
                resp = client.get(f"https://api.data.gov.in/resource/{DATA_GOV_RESOURCE_ID}", params=params)
                if resp.status_code == 200:
                    for rec in resp.json().get("records", []):
                        comm = rec.get("commodity")
                        modal = float(rec.get("modal_price") or 0)
                        if comm and modal > 0:
                            live_records.append({
                                "name": comm,
                                "category": "grain",
                                "min": float(rec.get("min_price") or modal * 0.9),
                                "max": float(rec.get("max_price") or modal * 1.1),
                                "modal": modal,
                                "previous": modal * random.uniform(0.97, 1.02),
                                "market": rec.get("market") or f"{state} APMC",
                                "district": rec.get("district") or district or state,
                                "source": "data_gov",
                            })
        except Exception as exc:
            logger.warning("[Commodities] data.gov.in fetch failed for %s: %s", state, exc)

    if not live_records:
        fallback = STATE_FALLBACK_COMMODITIES.get(state, STATE_FALLBACK_COMMODITIES.get("Telangana", []))
        live_records = [
            {
                **item,
                "previous": round(item["modal"] * random.uniform(0.97, 1.02), 2),
                "source": "fallback"
            }
            for item in fallback
        ]

    # Cache in SQLite keyed by (state, commodity)
    now = datetime.utcnow()
    out = []
    for idx, item in enumerate(live_records):
        cid = 10000 + (hash(f"{state}_{item['name']}") % 90000)
        existing = (
            db.query(models.MandiPriceCache)
            .filter(models.MandiPriceCache.state == state, models.MandiPriceCache.commodity == item["name"])
            .first()
        )
        prev_p = item.get("previous", item["modal"])
        diff = item["modal"] - prev_p
        pct = round((diff / prev_p) * 100, 2) if prev_p else 0.0
        trend = "up" if diff > 0 else ("down" if diff < 0 else "stable")

        if existing:
            existing.min_price = item["min"]
            existing.max_price = item["max"]
            existing.modal_price = item["modal"]
            existing.previous_price = prev_p
            existing.market = item["market"]
            existing.district = item.get("district")
            existing.category = item.get("category", "grain")
            existing.commodity_id = cid
            existing.source = item.get("source", "fallback")
            existing.cached_at = now
        else:
            db.add(models.MandiPriceCache(
                state=state,
                commodity=item["name"],
                commodity_id=cid,
                category=item.get("category", "grain"),
                unit="quintal",
                district=item.get("district"),
                market=item["market"],
                min_price=item["min"],
                max_price=item["max"],
                modal_price=item["modal"],
                previous_price=prev_p,
                source=item.get("source", "fallback"),
                cached_at=now,
            ))
        out.append({
            "id": cid,
            "name": item["name"],
            "name_kannada": None,
            "name_hindi": None,
            "category": item.get("category", "grain"),
            "unit": "quintal",
            "current_price": item["modal"],
            "previous_price": prev_p,
            "min_price": item["min"],
            "max_price": item["max"],
            "market": item["market"],
            "state": state,
            "trend": trend,
            "change_pct": pct,
            "updated_at": now,
        })
    if live_records:
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error("[Commodities] Failed to commit cache: %s", exc)
    return out


@router.get("/", response_model=List[CommodityOut])
def list_commodities(
    category: Optional[str] = Query(None),
    state: Optional[str] = Query(None, description="Indian state name"),
    district: Optional[str] = Query(None, description="District name"),
    location_name: Optional[str] = Query(None, description="Location name"),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    db: Session = Depends(get_db)
):
    """Return commodities, dynamically filtered by resolved Indian state, district, or category."""
    canonical_state = resolve_state(state=state, location_name=location_name, district=district, lat=lat, lon=lon)

    if canonical_state != "Karnataka":
        state_rows = _fetch_state_mandi_or_cache(canonical_state, district, db)
        if state_rows:
            if category:
                state_rows = [r for r in state_rows if r["category"] == category]
            return state_rows

    q = db.query(models.Commodity)
    if category:
        q = q.filter(models.Commodity.category == category)
    return [_enrich(c) for c in q.all()]


@router.get("/ticker", response_model=List[CommodityOut])
def ticker_commodities(
    state: Optional[str] = Query(None, description="Indian state name"),
    district: Optional[str] = Query(None, description="District name"),
    location_name: Optional[str] = Query(None, description="Location name"),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Return headline commodities shown in the sticky ticker bar for the resolved state.
    """
    canonical_state = resolve_state(state=state, location_name=location_name, district=district, lat=lat, lon=lon)

    if canonical_state != "Karnataka":
        state_rows = _fetch_state_mandi_or_cache(canonical_state, district, db)
        if state_rows:
            return state_rows[:6]

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
    if c:
        return _enrich(c)

    # Check in cached items
    cached = db.query(models.MandiPriceCache).filter(
        (models.MandiPriceCache.commodity_id == commodity_id) |
        (models.MandiPriceCache.id == (commodity_id - 10000))
    ).first()
    if cached:
        diff = cached.modal_price - (cached.previous_price or cached.modal_price)
        pct = round((diff / cached.previous_price) * 100, 2) if cached.previous_price else 0.0
        trend = "up" if diff > 0 else ("down" if diff < 0 else "stable")
        return {
            "id": commodity_id,
            "name": cached.commodity,
            "name_kannada": None,
            "name_hindi": None,
            "category": cached.category or "grain",
            "unit": cached.unit or "quintal",
            "current_price": cached.modal_price,
            "previous_price": cached.previous_price or cached.modal_price,
            "min_price": cached.min_price,
            "max_price": cached.max_price,
            "market": cached.market or f"{cached.state} APMC",
            "state": cached.state,
            "trend": trend,
            "change_pct": pct,
            "updated_at": cached.cached_at,
        }

    raise HTTPException(status_code=404, detail="Commodity not found")


@router.post("/{commodity_id}/simulate-tick")
def simulate_price_tick(commodity_id: int, db: Session = Depends(get_db)):
    """
    Dev utility: randomly nudge a commodity price ±3% to simulate live feed.
    """
    c = db.query(models.Commodity).filter(models.Commodity.id == commodity_id).first()
    if c:
        c.previous_price = c.current_price
        factor = random.uniform(0.97, 1.03)
        c.current_price = round(c.current_price * factor, 2)
        c.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(c)
        return _enrich(c)

    cached = db.query(models.MandiPriceCache).filter(
        (models.MandiPriceCache.commodity_id == commodity_id) |
        (models.MandiPriceCache.id == (commodity_id - 10000))
    ).first()
    if cached:
        cached.previous_price = cached.modal_price
        factor = random.uniform(0.97, 1.03)
        cached.modal_price = round(cached.modal_price * factor, 2)
        cached.cached_at = datetime.utcnow()
        db.commit()
        db.refresh(cached)
        diff = cached.modal_price - cached.previous_price
        pct = round((diff / cached.previous_price) * 100, 2)
        trend = "up" if diff > 0 else ("down" if diff < 0 else "stable")
        return {
            "id": commodity_id,
            "name": cached.commodity,
            "name_kannada": None,
            "name_hindi": None,
            "category": cached.category or "grain",
            "unit": cached.unit or "quintal",
            "current_price": cached.modal_price,
            "previous_price": cached.previous_price,
            "min_price": cached.min_price,
            "max_price": cached.max_price,
            "market": cached.market or f"{cached.state} APMC",
            "state": cached.state,
            "trend": trend,
            "change_pct": pct,
            "updated_at": cached.cached_at,
        }

    raise HTTPException(status_code=404, detail="Commodity not found")
