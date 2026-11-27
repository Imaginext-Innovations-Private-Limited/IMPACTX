"""
Animal Husbandry & Dairy Module Router.
Covers:
1. Dairy milk procurement rate comparison (KMF Nandini, Amul, Dodla, Heritage, Tirumala) with Fat/SNF calculator
2. Weather-matched high-yield cow and buffalo breeds
3. Targeted feed & nutrition planner (dry vs lactating)
4. Breeding & sire semen selection guide
5. Livestock disease & behavior advisor with immediate first aid and voice link
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator

from database import get_db
import models

router = APIRouter(prefix="/api/dairy", tags=["dairy"])


class RateCalculateRequest(BaseModel):
    milk_type: str = "Cow"  # "Cow" or "Buffalo"
    fat_pct: float = 3.5
    snf_pct: float = 8.5
    quantity_litres: float = 10.0


@router.get("")
@router.get("/")
def get_dairy_overview(db: Session = Depends(get_db)):
    """
    Consolidated Animal Husbandry & Dairy Overview:
    - Nandini, Amul, Dodla, Heritage, Tirumala milk procurement rates
    - Weather-matched breeds
    - Rations / feed plans
    - Breeding guide / sire semen matching
    - Symptom & disease advisor
    """
    rates = get_procurement_rates(None, db)
    breeds = get_breeds(None, None, db)
    feed_plans = get_feed_plans(None, None, db)
    sire_guide = get_breeding_guide(None, db)
    diseases = get_disease_advisor(None, db)
    return {
        "title": "Karnataka Animal Husbandry & Dairy Advisory",
        "procurement_rates": rates,
        "breeds": breeds,
        "feed_plans": feed_plans,
        "rations": feed_plans,
        "breeding_guide": sire_guide,
        "semen_matching": sire_guide,
        "disease_advisor": diseases,
        "symptom_advisor": diseases,
    }


@router.get("/procurement-rates")
def get_procurement_rates(
    milk_type: Optional[str] = Query(None, description="Cow or Buffalo"),
    db: Session = Depends(get_db)
):
    """
    Returns procurement rates across major Karnataka dairies:
    KMF Nandini, Amul, Dodla Dairy, Heritage Foods, Tirumala.
    Broken down by standard Fat % and SNF %, plus state government incentives (Ksheera Dhare).
    """
    q = db.query(models.DairyProcurementRate)
    if milk_type:
        q = q.filter(models.DairyProcurementRate.milk_type.ilike(f"%{milk_type}%"))
    rates = q.all()

    res = []
    for r in rates:
        # Standard payout at base fat/snf
        total_rate = round(r.rate_per_litre + r.govt_incentive, 2)
        res.append({
            "id": r.id,
            "dairy_name": r.dairy_name,
            "brand_logo": r.brand_logo,
            "slab_name": r.slab_name,
            "milk_type": r.milk_type,
            "base_fat_pct": r.base_fat_pct,
            "base_snf_pct": r.base_snf_pct,
            "base_rate_per_litre": r.rate_per_litre,
            "fat_rate_factor": r.fat_rate_factor,
            "snf_rate_factor": r.snf_rate_factor,
            "govt_incentive": r.govt_incentive,
            "total_effective_rate": total_rate,
            "notes": r.notes,
        })
    return res


@router.post("/calculate-payout")
def calculate_milk_payout(req: RateCalculateRequest, db: Session = Depends(get_db)):
    """
    Interactive milk payout calculator.
    Computes payout per liter and total payout based on tested Fat % and SNF %
    across all major dairies.
    """
    rates = db.query(models.DairyProcurementRate).filter(
        models.DairyProcurementRate.milk_type.ilike(f"%{req.milk_type}%")
    ).all()

    comparison = []
    best_dairy = None
    max_payout = 0

    for r in rates:
        # Calculate dynamic price adjustment
        fat_diff = req.fat_pct - r.base_fat_pct
        snf_diff = req.snf_pct - r.base_snf_pct

        adjusted_base = r.rate_per_litre + (fat_diff * r.fat_rate_factor) + (snf_diff * r.snf_rate_factor)
        adjusted_base = max(adjusted_base, 20.0) # floor

        effective_rate = round(adjusted_base + r.govt_incentive, 2)
        total_amount = round(effective_rate * req.quantity_litres, 2)

        if total_amount > max_payout:
            max_payout = total_amount
            best_dairy = r.dairy_name

        comparison.append({
            "dairy_name": r.dairy_name,
            "base_rate": r.rate_per_litre,
            "fat_adjustment": round(fat_diff * r.fat_rate_factor, 2),
            "snf_adjustment": round(snf_diff * r.snf_rate_factor, 2),
            "govt_incentive": r.govt_incentive,
            "rate_per_litre": effective_rate,
            "total_payout": total_amount,
            "is_highest": False,
        })

    for c in comparison:
        if c["dairy_name"] == best_dairy:
            c["is_highest"] = True

    return {
        "input": req.dict(),
        "best_dairy": best_dairy,
        "max_payout": max_payout,
        "results": comparison,
    }


@router.get("/breeds")
def get_breeds(
    temp_c: Optional[float] = Query(None, description="Current ambient temperature in °C"),
    animal_type: Optional[str] = Query(None, description="Cow or Buffalo"),
    db: Session = Depends(get_db),
):
    """
    Returns high-yield cow and buffalo breeds matched to local weather & temperature.
    Computes climate suitability status (High, Moderate, Heat-stressed).
    """
    q = db.query(models.LivestockBreed)
    if animal_type:
        q = q.filter(models.LivestockBreed.animal_type.ilike(f"%{animal_type}%"))
    breeds = q.all()

    current_temp = temp_c if temp_c is not None else 26.5

    res = []
    for b in breeds:
        # Climate suitability scoring
        if current_temp > b.max_temp_c:
            suitability = "Caution: Heat Stress"
            suitability_kannada = "ಎಚ್ಚರಿಕೆ: ಅಧಿಕ ತಾಪಮಾನದಿಂದ ಹಾಲು ಉತ್ಪಾದನೆ ಇಳಿಕೆ ಸಾಧ್ಯತೆ"
            suitability_score = "low"
            cooling_advice = "Provide ceiling fans, misting, shaded sheds, and cold drinking water."
        elif b.min_temp_c <= current_temp <= (b.max_temp_c - 3):
            suitability = "Optimal Climate"
            suitability_kannada = "ಪ್ರಸ್ತುತ ವಾತಾವರಣಕ್ಕೆ ಅತ್ಯುತ್ತಮ"
            suitability_score = "high"
            cooling_advice = "Standard shelter and ventilation are sufficient."
        else:
            suitability = "Moderate Tolerance"
            suitability_kannada = "ಮಧ್ಯಮ ಸಹಿಷ್ಣುತೆ"
            suitability_score = "medium"
            cooling_advice = "Ensure adequate green fodder and evening bathing."

        res.append({
            "id": b.id,
            "breed_name": b.breed_name,
            "breed_kannada": b.breed_kannada,
            "animal_type": b.animal_type,
            "origin": b.origin,
            "avg_yield_litres": b.avg_yield_litres,
            "peak_yield_litres": b.peak_yield_litres,
            "fat_pct": b.fat_pct,
            "climate_zone": b.climate_zone,
            "heat_tolerance": b.heat_tolerance,
            "drought_resistance": b.drought_resistance,
            "disease_resistance": b.disease_resistance,
            "feeding_requirement": b.feeding_requirement,
            "description": b.description,
            "weather_match": {
                "current_temp": current_temp,
                "suitability": suitability,
                "suitability_kannada": suitability_kannada,
                "suitability_score": suitability_score,
                "cooling_advice": cooling_advice,
            },
        })
    return res


@router.get("/feed-plans")
def get_feed_plans(
    animal_type: Optional[str] = Query(None, description="Cow or Buffalo"),
    stage: Optional[str] = Query(None, description="Dry or Lactating"),
    db: Session = Depends(get_db),
):
    """
    Returns targeted daily feed & nutrition rations separately for:
    (a) unfertilized/dry cows and buffaloes
    (b) lactating cows and buffaloes to maximize milk yield.
    """
    q = db.query(models.FeedPlan)
    if animal_type:
        q = q.filter(models.FeedPlan.animal_type.ilike(f"%{animal_type}%"))
    if stage:
        q = q.filter(models.FeedPlan.stage.ilike(f"%{stage}%"))
    plans = q.all()

    res = []
    for p in plans:
        total_roughage = p.green_fodder_kg + p.dry_fodder_kg
        res.append({
            "id": p.id,
            "plan_title": p.plan_title,
            "plan_title_kannada": p.plan_title_kannada,
            "animal_type": p.animal_type,
            "stage": p.stage,
            "body_weight_kg": p.body_weight_kg,
            "target_yield_litres": p.target_yield_litres,
            "green_fodder_kg": p.green_fodder_kg,
            "dry_fodder_kg": p.dry_fodder_kg,
            "concentrate_kg": p.concentrate_kg,
            "mineral_mixture_g": p.mineral_mixture_g,
            "bypass_fat_g": p.bypass_fat_g,
            "salt_g": p.salt_g,
            "water_litres": p.water_litres,
            "total_roughage_kg": total_roughage,
            "schedule_tips": p.schedule_tips,
        })
    return res


@router.get("/breeding-guide")
def get_breeding_guide(
    dam_breed: Optional[str] = Query(None, description="Selected Cow or Buffalo breed"),
    db: Session = Depends(get_db),
):
    """
    Breeding & Sire Semen Selection Guide.
    Shows which bull/sire semen breed is best suited for a selected cow/buffalo
    to boost milk yield and disease resistance.
    """
    q = db.query(models.SireGuide)
    if dam_breed:
        q = q.filter(models.SireGuide.dam_breed.ilike(f"%{dam_breed}%"))
    guides = q.all()

    res = []
    for g in guides:
        res.append({
            "id": g.id,
            "dam_breed": g.dam_breed,
            "dam_breed_kannada": g.dam_breed_kannada,
            "recommended_sire": g.recommended_sire,
            "recommended_sire_kannada": g.recommended_sire_kannada,
            "purpose": g.purpose,
            "expected_gain": g.expected_gain,
            "inbreeding_caution": g.inbreeding_caution,
            "veterinary_tip": g.veterinary_tip,
        })
    return res


@router.get("/disease-advisor")
def get_disease_advisor(
    symptom: Optional[str] = Query(None, description="Search symptom keyword"),
    db: Session = Depends(get_db),
):
    """
    Quick symptom and behavior variation advisor for livestock.
    Returns immediate first aid guidance and recommended voice assistant query.
    """
    q = db.query(models.LivestockDisease)
    if symptom:
        q = q.filter(
            (models.LivestockDisease.symptom_key.ilike(f"%{symptom}%")) |
            (models.LivestockDisease.symptom_display.ilike(f"%{symptom}%")) |
            (models.LivestockDisease.suspected_condition.ilike(f"%{symptom}%"))
        )
    diseases = q.all()

    res = []
    for d in diseases:
        res.append({
            "id": d.id,
            "symptom_key": d.symptom_key,
            "symptom_display": d.symptom_display,
            "symptom_kannada": d.symptom_kannada,
            "suspected_condition": d.suspected_condition,
            "suspected_kannada": d.suspected_kannada,
            "urgency_level": d.urgency_level,
            "immediate_first_aid": d.immediate_first_aid,
            "avoid_doing": d.avoid_doing,
            "recommended_query": d.recommended_query,
        })
    return res


# ============================================================================
# VETERINARY DOCTORS & CATTLE MARKETPLACE ENDPOINTS
# ============================================================================

class VetDoctorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    doctor_type: str = Field(..., min_length=1, max_length=50)  # "Local Cow Doctor" or "Veterinary Doctor"
    specialization: Optional[str] = Field(None, max_length=200)
    phone: str = Field(..., min_length=3, max_length=50)
    location: str = Field(..., min_length=1, max_length=150)
    availability: Optional[str] = Field(None, max_length=150)
    emergency_available: bool = False

    @field_validator("name", "doctor_type", "phone", "location")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace")
        return cleaned


class VetDoctorOut(BaseModel):
    id: int
    name: str
    doctor_type: str
    specialization: Optional[str] = None
    phone: str
    location: str
    availability: Optional[str] = None
    emergency_available: bool

    class Config:
        from_attributes = True


class CattleListingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    breed: str = Field(..., min_length=1, max_length=100)
    animal_type: str = Field(..., min_length=1, max_length=30)  # "Cow", "Buffalo", "Heifer", "Calf"
    price_inr: float = Field(..., ge=0)
    milk_yield_liters_per_day: float = Field(0.0, ge=0)
    age_years: float = Field(0.0, ge=0)
    location: str = Field(..., min_length=1, max_length=150)
    owner_name: str = Field(..., min_length=1, max_length=150)
    owner_phone: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None

    @field_validator("title", "breed", "animal_type", "location", "owner_name", "owner_phone")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace")
        return cleaned


class CattleListingOut(BaseModel):
    id: int
    title: str
    breed: str
    animal_type: str
    price_inr: float
    milk_yield_liters_per_day: float
    age_years: float
    location: str
    owner_name: str
    owner_phone: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/doctors", response_model=List[VetDoctorOut])
def get_vet_doctors(
    doctor_type: Optional[str] = Query(None, description="Local Cow Doctor or Veterinary Doctor"),
    search: Optional[str] = Query(None, description="Search by name, specialization, location, or phone"),
    db: Session = Depends(get_db),
):
    """Return local cow doctors and veterinary doctors, with optional filtering."""
    q = db.query(models.VetDoctor)

    if doctor_type and doctor_type.strip().lower() != "all":
        q = q.filter(models.VetDoctor.doctor_type.ilike(f"%{doctor_type.strip()}%"))

    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.filter(
            or_(
                models.VetDoctor.name.ilike(term),
                models.VetDoctor.specialization.ilike(term),
                models.VetDoctor.location.ilike(term),
                models.VetDoctor.phone.ilike(term),
            )
        )

    return q.order_by(models.VetDoctor.emergency_available.desc(), models.VetDoctor.id.desc()).all()


@router.post("/doctors", response_model=VetDoctorOut, status_code=201)
def create_vet_doctor(payload: VetDoctorCreate, db: Session = Depends(get_db)):
    """Add a new local cow doctor or veterinary doctor."""
    doctor = models.VetDoctor(
        name=payload.name,
        doctor_type=payload.doctor_type,
        specialization=payload.specialization.strip() if payload.specialization else None,
        phone=payload.phone,
        location=payload.location,
        availability=payload.availability.strip() if payload.availability else None,
        emergency_available=payload.emergency_available,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


@router.get("/cattle", response_model=List[CattleListingOut])
def get_cattle_listings(
    breed: Optional[str] = Query(None, description="Filter by breed"),
    animal_type: Optional[str] = Query(None, description="Cow, Buffalo, Heifer, or Calf"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    sort_by: Optional[str] = Query(None, description="price_asc, price_desc, milk_desc, or newest"),
    db: Session = Depends(get_db),
):
    """Return cattle marketplace listings with optional breed/price filtering and sorting."""
    q = db.query(models.CattleListing)

    if breed and breed.strip().lower() != "all":
        q = q.filter(models.CattleListing.breed.ilike(f"%{breed.strip()}%"))

    if animal_type and animal_type.strip().lower() != "all":
        q = q.filter(models.CattleListing.animal_type.ilike(f"%{animal_type.strip()}%"))

    if min_price is not None:
        q = q.filter(models.CattleListing.price_inr >= min_price)

    if max_price is not None:
        q = q.filter(models.CattleListing.price_inr <= max_price)

    if sort_by == "price_asc":
        q = q.order_by(models.CattleListing.price_inr.asc())
    elif sort_by == "price_desc":
        q = q.order_by(models.CattleListing.price_inr.desc())
    elif sort_by == "milk_desc":
        q = q.order_by(models.CattleListing.milk_yield_liters_per_day.desc())
    else:
        q = q.order_by(models.CattleListing.created_at.desc(), models.CattleListing.id.desc())

    return q.all()


@router.post("/cattle", response_model=CattleListingOut, status_code=201)
def create_cattle_listing(payload: CattleListingCreate, db: Session = Depends(get_db)):
    """Create a new cattle marketplace listing."""
    listing = models.CattleListing(
        title=payload.title,
        breed=payload.breed,
        animal_type=payload.animal_type,
        price_inr=payload.price_inr,
        milk_yield_liters_per_day=payload.milk_yield_liters_per_day,
        age_years=payload.age_years,
        location=payload.location,
        owner_name=payload.owner_name,
        owner_phone=payload.owner_phone,
        description=payload.description.strip() if payload.description else None,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/cattle/{listing_id}")
def delete_cattle_listing(listing_id: int, db: Session = Depends(get_db)):
    """Delete a cattle marketplace listing by ID."""
    listing = db.query(models.CattleListing).filter(models.CattleListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Cattle listing not found")
    db.delete(listing)
    db.commit()
    return {"success": True, "deleted_id": listing_id}
