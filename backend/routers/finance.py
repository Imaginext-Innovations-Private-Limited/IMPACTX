"""
Whole-Year Farm & Household Balance Sheet, Crop Profit-Ratio Engine,
and Agricultural Financing Advisory Hub Router.
"""
from typing import Optional, List, Dict
from datetime import datetime
import json
from collections import defaultdict
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
import models

router = APIRouter(prefix="/api/finance", tags=["finance"])


class LedgerEntryCreate(BaseModel):
    entry_date: str
    crop_tag: str
    entry_type: str  # 'expense' or 'revenue'
    category: str    # 'cultivation', 'irrigation', 'harvest', 'household', 'crop_sales'
    sub_category: Optional[str] = None
    description: str
    amount: float
    notes: Optional[str] = None


@router.get("/ledger")
def get_ledger(
    crop_tag: Optional[str] = Query(None, description="Paddy, Areca, Ginger, Corn, General/Household"),
    entry_type: Optional[str] = Query(None, description="expense or revenue"),
    db: Session = Depends(get_db),
):
    """
    Returns ledger entries and computes the comprehensive Whole-Year Farm & Household Balance Sheet.
    Computes:
    - Total Cultivation Cost
    - Total Irrigation Cost
    - Total Harvest Expense
    - Household Cashflow Summary (living expenses vs non-farm income)
    - Gross Crop Revenue
    - Net Farm Profit/Loss
    - Monthly income-vs-expense breakdown for charts
    """
    q = db.query(models.FarmLedgerEntry)
    if crop_tag and crop_tag != "All":
        q = q.filter(models.FarmLedgerEntry.crop_tag == crop_tag)
    if entry_type and entry_type != "All":
        q = q.filter(models.FarmLedgerEntry.entry_type == entry_type)

    entries = q.order_by(models.FarmLedgerEntry.entry_date.desc()).all()

    # Load all entries for annual balance sheet computation
    all_entries = db.query(models.FarmLedgerEntry).all()

    cultivation_cost = 0.0
    irrigation_cost = 0.0
    harvest_cost = 0.0
    crop_revenue = 0.0
    household_expense = 0.0
    household_income = 0.0

    monthly_summary = defaultdict(lambda: {"month": "", "income": 0.0, "expense": 0.0, "farm_income": 0.0, "farm_expense": 0.0})
    crop_breakdown = defaultdict(lambda: {"cost": 0.0, "revenue": 0.0, "net": 0.0})

    for e in all_entries:
        month_key = e.entry_date[:7] if len(e.entry_date) >= 7 else "2026-01"
        monthly_summary[month_key]["month"] = month_key

        if e.category == "cultivation":
            cultivation_cost += e.amount
            monthly_summary[month_key]["expense"] += e.amount
            monthly_summary[month_key]["farm_expense"] += e.amount
            crop_breakdown[e.crop_tag]["cost"] += e.amount
        elif e.category == "irrigation":
            irrigation_cost += e.amount
            monthly_summary[month_key]["expense"] += e.amount
            monthly_summary[month_key]["farm_expense"] += e.amount
            crop_breakdown[e.crop_tag]["cost"] += e.amount
        elif e.category == "harvest":
            harvest_cost += e.amount
            monthly_summary[month_key]["expense"] += e.amount
            monthly_summary[month_key]["farm_expense"] += e.amount
            crop_breakdown[e.crop_tag]["cost"] += e.amount
        elif e.category == "crop_sales":
            crop_revenue += e.amount
            monthly_summary[month_key]["income"] += e.amount
            monthly_summary[month_key]["farm_income"] += e.amount
            crop_breakdown[e.crop_tag]["revenue"] += e.amount
        elif e.category == "household":
            if e.entry_type == "expense":
                household_expense += e.amount
                monthly_summary[month_key]["expense"] += e.amount
            else:
                household_income += e.amount
                monthly_summary[month_key]["income"] += e.amount

    total_farm_operating_cost = cultivation_cost + irrigation_cost + harvest_cost
    net_farm_profit = crop_revenue - total_farm_operating_cost
    net_household_cashflow = household_income - household_expense
    combined_net_cashflow = net_farm_profit + net_household_cashflow

    # Calculate net profit for each crop
    crop_summary = []
    for c_tag, vals in crop_breakdown.items():
        if c_tag == "General/Household":
            continue
        c_net = vals["revenue"] - vals["cost"]
        p_ratio = round(c_net / vals["cost"], 2) if vals["cost"] > 0 else 0.0
        roi_pct = round((c_net / vals["cost"]) * 100, 1) if vals["cost"] > 0 else 0.0
        crop_summary.append({
            "crop": c_tag,
            "cost": round(vals["cost"], 2),
            "revenue": round(vals["revenue"], 2),
            "net_profit": round(c_net, 2),
            "profit_ratio": p_ratio,
            "roi_percent": roi_pct,
        })

    # Sort monthly data for Recharts
    chart_data = []
    for m in sorted(monthly_summary.keys()):
        # Convert YYYY-MM to human label like "Jan", "Feb"
        try:
            m_dt = datetime.strptime(m, "%Y-%m")
            label = m_dt.strftime("%b %y")
        except Exception:
            label = m
        chart_data.append({
            "month_key": m,
            "month": label,
            "income": round(monthly_summary[m]["income"], 2),
            "expense": round(monthly_summary[m]["expense"], 2),
            "net": round(monthly_summary[m]["income"] - monthly_summary[m]["expense"], 2),
            "farm_income": round(monthly_summary[m]["farm_income"], 2),
            "farm_expense": round(monthly_summary[m]["farm_expense"], 2),
        })

    entries_data = [
        {
            "id": e.id,
            "entry_date": e.entry_date,
            "crop_tag": e.crop_tag,
            "entry_type": e.entry_type,
            "category": e.category,
            "sub_category": e.sub_category,
            "description": e.description,
            "amount": e.amount,
            "notes": e.notes,
        }
        for e in entries
    ]

    return {
        "balance_sheet": {
            "total_cultivation_cost": round(cultivation_cost, 2),
            "total_irrigation_cost": round(irrigation_cost, 2),
            "total_harvest_expense": round(harvest_cost, 2),
            "total_farm_operating_cost": round(total_farm_operating_cost, 2),
            "gross_crop_revenue": round(crop_revenue, 2),
            "net_farm_profit": round(net_farm_profit, 2),
            "household_living_expenses": round(household_expense, 2),
            "household_non_farm_income": round(household_income, 2),
            "net_household_cashflow": round(net_household_cashflow, 2),
            "combined_net_cashflow": round(combined_net_cashflow, 2),
            "overall_farm_roi_percent": round((net_farm_profit / total_farm_operating_cost * 100), 1) if total_farm_operating_cost > 0 else 0.0,
            "crop_summary": crop_summary,
        },
        "monthly_chart": chart_data,
        "entries": entries_data,
    }


@router.post("/ledger")
def add_ledger_entry(entry: LedgerEntryCreate, db: Session = Depends(get_db)):
    """Add a new transaction entry into the farm ledger."""
    new_entry = models.FarmLedgerEntry(
        entry_date=entry.entry_date,
        crop_tag=entry.crop_tag,
        entry_type=entry.entry_type,
        category=entry.category,
        sub_category=entry.sub_category,
        description=entry.description,
        amount=entry.amount,
        notes=entry.notes,
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return {"success": True, "entry_id": new_entry.id}


@router.delete("/ledger/{entry_id}")
def delete_ledger_entry(entry_id: int, db: Session = Depends(get_db)):
    """Delete a transaction entry."""
    e = db.query(models.FarmLedgerEntry).filter(models.FarmLedgerEntry.id == entry_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(e)
    db.commit()
    return {"success": True, "deleted_id": entry_id}


class ProfitComparisonRequest(BaseModel):
    soil_type: Optional[str] = "Red Sandy Loam"
    temp_c: Optional[float] = 27.0


class AdvisoryRequest(BaseModel):
    crop: Optional[str] = None
    location: Optional[str] = None


@router.get("/profit-comparison")
def get_profit_comparison(
    soil_type: Optional[str] = Query("Red Sandy Loam", description="Selected Soil Type"),
    temp_c: Optional[float] = Query(27.0, description="Ambient or forecast temperature"),
    db: Session = Depends(get_db),
):
    """
    Crop Profit-Ratio Engine & Weather/Soil Alternative Comparator.
    - Calculates recorded crops' actual profit ratio and ROI from the farmer's balance sheet.
    - Recommends 3-4 alternative crops suited to that exact soil and current climate.
    - Compares expected Profit Ratio, water demand, and net profit per acre side-by-side.
    """
    # 1. Fetch farmer's actual crops from ledger
    all_entries = db.query(models.FarmLedgerEntry).all()
    crop_stats = defaultdict(lambda: {"cost": 0.0, "revenue": 0.0})
    for e in all_entries:
        if e.crop_tag != "General/Household":
            if e.entry_type == "expense":
                crop_stats[e.crop_tag]["cost"] += e.amount
            elif e.entry_type == "revenue":
                crop_stats[e.crop_tag]["revenue"] += e.amount

    farmer_crops = []
    for c_name, vals in crop_stats.items():
        cost = vals["cost"]
        rev = vals["revenue"]
        net = rev - cost
        p_ratio = round(net / cost, 2) if cost > 0 else 0.0
        roi = round((net / cost) * 100, 1) if cost > 0 else 0.0
        farmer_crops.append({
            "crop_name": c_name,
            "total_cost": round(cost, 2),
            "gross_revenue": round(rev, 2),
            "net_profit": round(net, 2),
            "profit_ratio": p_ratio,
            "roi_percent": roi,
            "status": "Currently Cultivated",
        })

    # 2. Fetch alternative crop benchmarks matching soil and weather
    benchmarks = db.query(models.AlternativeCropBenchmark).all()
    recommended_alternatives = []

    for b in benchmarks:
        soils = []
        if b.suitable_soil_types:
            try:
                soils = json.loads(b.suitable_soil_types)
            except Exception:
                soils = [b.suitable_soil_types]

        is_soil_match = any(soil_type.lower() in s.lower() for s in soils)
        is_temp_match = b.min_temp_c <= temp_c <= b.max_temp_c

        # Scoring
        match_level = "High Suitability" if (is_soil_match and is_temp_match) else "Moderate Suitability"

        recommended_alternatives.append({
            "id": b.id,
            "crop_name": b.crop_name,
            "crop_kannada": b.crop_kannada,
            "suitable_soils": soils,
            "is_soil_match": is_soil_match,
            "is_temp_match": is_temp_match,
            "match_level": match_level,
            "water_demand": b.water_demand_level,
            "water_requirement_mm": b.water_requirement_mm,
            "growth_duration_days": b.growth_duration_days,
            "avg_cost_per_acre": b.avg_cost_per_acre,
            "avg_yield_per_acre": b.avg_yield_per_acre,
            "avg_gross_revenue_per_acre": b.avg_gross_revenue_per_acre,
            "avg_net_profit_per_acre": b.avg_net_profit_per_acre,
            "profit_ratio": b.profit_ratio,
            "roi_percent": b.roi_percent,
            "risk_factor": b.risk_factor,
            "advantages": b.advantages,
        })

    # Sort alternatives by soil match first, then by profit ratio descending
    recommended_alternatives.sort(key=lambda x: (x["is_soil_match"], x["profit_ratio"]), reverse=True)

    available_soils = [
        "Red Sandy Loam",
        "Black Cotton Soil",
        "Laterite Soil",
        "Clay Loam",
        "Alluvial Soil",
    ]

    return {
        "selected_soil": soil_type,
        "current_temp_c": temp_c,
        "available_soils": available_soils,
        "farmer_crops": farmer_crops,
        "recommended_alternatives": recommended_alternatives[:4],  # top 4
        "all_benchmarks": recommended_alternatives,
    }


@router.post("/profit-comparison")
def post_profit_comparison(req: Optional[ProfitComparisonRequest] = None, db: Session = Depends(get_db)):
    """POST endpoint for crop profit comparison."""
    soil_type = req.soil_type if req and req.soil_type else "Red Sandy Loam"
    temp_c = req.temp_c if req and req.temp_c is not None else 27.0
    return get_profit_comparison(soil_type=soil_type, temp_c=temp_c, db=db)


@router.get("/advisory")
@router.post("/advisory")
def get_credit_advisory(req: Optional[AdvisoryRequest] = None):
    """
    Agricultural Financing & Credit Advisory Hub (supports GET & POST).
    Covers strictly the 6 required areas with highlights, document checklists, and calculator parameters:
    1) Short-Term Crop Loans & Kisan Credit Cards (KCC)
    2) Crop Insurance (PMFBY & Weather-Based)
    3) Warehouse Receipt Financing & Post-Harvest Loans
    4) Long-Term Investment Loans for Farm Modernization
    5) Value-Chain & Allied Sector Financing
    6) Solar Energy Financing (PM-KUSUM)
    """
    return {
        "title": "Agricultural Credit, Schemes & Farm Financing Hub",
        "title_kannada": "ಕೃಷಿ ಸಾಲ, ವಿಮೆ ಮತ್ತು ಸರ್ಕಾರದ ಸಬ್ಸಿಡಿ ಮಾರ್ಗದರ್ಶಿ",
        "credit_pillars": [
            {
                "id": "kcc",
                "title": "Short-Term Crop Loans & Kisan Credit Cards (KCC)",
                "title_kannada": "ಕಿಸಾನ್ ಕ್ರೆಡಿಟ್ ಕಾರ್ಡ್ (KCC) ಮತ್ತು ಅಲ್ಪಾವಧಿ ಬೆಳೆ ಸಾಲ",
                "badge": "4% Effective Interest Rate",
                "badge_color": "emerald",
                "description": "Short-term production credit for seasonal farm expenses (seeds, fertilizer, labor) and working capital for dairy and fisheries.",
                "key_highlights": [
                    "7% standard interest subvention rate with 3% Prompt Repayment Incentive (PRI) = 4% net effective rate",
                    "Collateral-free crop loan limit up to ₹2,00,000 for verified landholders",
                    "Dedicated ₹2,00,000 sub-limit for Dairy & Animal Husbandry working capital",
                    "Composite revolving credit card valid for 6 years with annual scale-of-finance review",
                    "Zero processing fees on loans up to ₹3,00,000"
                ],
                "required_documents": [
                    "Aadhaar Card and Voter ID / Ration Card",
                    "Bhoomi RTC / Pahani with updated Mutation Extract",
                    "FRUITS (Farmer Registration and Unified Beneficiary Information System) FID Number",
                    "No-Objection Certificate (NOC) from nearby PACS / Co-operative bank",
                    "Cropping pattern declaration verified by Village Accountant"
                ],
                "calculator_defaults": {
                    "base_rate": 7.0,
                    "prompt_rebate": 3.0,
                    "net_rate": 4.0,
                    "max_collateral_free": 200000,
                    "max_dairy_sublimit": 200000,
                    "scale_per_acre": {
                        "Paddy": 34000,
                        "Areca": 85000,
                        "Ginger": 95000,
                        "Corn": 26000
                    }
                }
            },
            {
                "id": "insurance",
                "title": "Crop Insurance (Reducing Financial & Weather Risks)",
                "title_kannada": "ಬೆಳೆ ವಿಮೆ (ಹವಾಮಾನ & ಪ್ರಾಕೃತಿಕ ನಷ್ಟ ತಗ್ಗಿಸುವಿಕೆ)",
                "badge": "1.5% - 5% Farmer Premium",
                "badge_color": "blue",
                "description": "Comprehensive insurance safety net from pre-sowing to post-harvest across notified drought, unseasonal rainfall, inundation, and cyclone events.",
                "key_highlights": [
                    "Pradhan Mantri Fasal Bima Yojana (PMFBY): Farmers pay only 1.5% for Rabi, 2% for Kharif, and 5% for Annual Commercial/Horticultural crops",
                    "Remaining premium subsidized 50:50 by Central and Karnataka State Governments",
                    "Automatic coverage for mid-season adversity and prevented sowing (>50% deficit)",
                    "Mandatory 72-hour loss reporting via Krishi Rakshak Helpline 14447 or Samrakshane portal for individual field inundation",
                    "Direct Aadhaar-seeded claim settlement straight into bank accounts without middleman delay"
                ],
                "required_documents": [
                    "Aadhaar Card of cultivating farmer",
                    "Bhoomi RTC indicating current crop entry",
                    "Sowing Certificate issued by Village Accountant / RSK",
                    "Aadhaar-seeded bank passbook copy with IFSC code"
                ],
                "calculator_defaults": {
                    "rabi_rate": 1.5,
                    "kharif_rate": 2.0,
                    "horticulture_rate": 5.0,
                    "reporting_window_hours": 72
                }
            },
            {
                "id": "warehouse",
                "title": "Warehouse Receipt Financing & Post-Harvest Loans",
                "title_kannada": "ಉಗ್ರಾಣ ರಸೀದಿ ಸಾಲ (ಇ-ಎನ್‌ಡಬ್ಲ್ಯೂಆರ್ ಅಡಮಾನ ಸಾಲ)",
                "badge": "Avoid Distress Selling",
                "badge_color": "amber",
                "description": "Pledge electronic Negotiable Warehouse Receipts (e-NWR) to borrow immediate cash at 7-9% interest, avoiding panic sales during harvest gluts and timing market peaks.",
                "key_highlights": [
                    "Borrow up to 75% of the current market value of commodities deposited in WDRA-registered warehouses",
                    "Interest subvention of 2% available for small and marginal farmers with active KCC for up to 6 months",
                    "Avoids immediate post-harvest distress selling when mandi rates dip by 20-30%",
                    "Sell stored produce directly on e-NAM digital auctions when seasonal price charts peak in off-season months",
                    "Free insurance against warehouse fire, burglary, rodent infestation, and quality deterioration"
                ],
                "required_documents": [
                    "WDRA Warehouse Deposit Receipt / Electronic e-NWR Certificate",
                    "Kisan Credit Card (KCC) or Bank Account statement",
                    "Farmer Aadhaar and PAN Card",
                    "Quality assaying and grade certificate issued by the warehouse manager"
                ],
                "calculator_defaults": {
                    "max_loan_to_value": 75.0,
                    "standard_tenure_months": 6,
                    "interest_rate": 7.5
                }
            },
            {
                "id": "modernization",
                "title": "Long-Term Investment Loans for Farm Modernization",
                "title_kannada": "ದೀರ್ಘಾವಧಿ ಕೃಷಿ ಆಧುನೀಕರಣ ಸಾಲ (ಯಂತ್ರೋಪಕರಣ & ಹನಿ ನೀರಾವರಿ)",
                "badge": "NABARD Refinanced",
                "badge_color": "purple",
                "description": "Medium and long-term credit (3 to 9 years) for farm asset creation, drip/sprinkler systems, polyhouses, farm ponds, and tractors.",
                "key_highlights": [
                    "Subsidized term loans for drip/sprinkler micro-irrigation systems integrated with PMKSY 90% subsidy",
                    "Tractor and power tiller loans with 15% margin money and up to 7-year repayment tenure",
                    "Polyhouse, shade-net and high-density horticulture project financing through National Horticulture Board (NHB) capital subsidy",
                    "Farm pond lining and borewell groundwater recharge structures",
                    "Moratorium period of 6 to 18 months before principal repayment begins"
                ],
                "required_documents": [
                    "Detailed Project Report (DPR) or authorized dealer quotation",
                    "RTC land records verifying unencumbered land parcel",
                    "FRUITS ID and 3-year IT return / bank statement",
                    "Approved vendor estimate with GST invoice"
                ],
                "calculator_defaults": {
                    "interest_rate": 8.5,
                    "max_tenure_years": 7,
                    "margin_money_pct": 15.0
                }
            },
            {
                "id": "allied",
                "title": "Value-Chain & Allied Sector Financing",
                "title_kannada": "ಹೈನುಗಾರಿಕೆ & ಮೌಲ್ಯವರ್ಧನೆ ಸಾಲ (Animal Husbandry Infrastructure Fund)",
                "badge": "3% Interest Subvention",
                "badge_color": "teal",
                "description": "Dedicated funding for commercial dairy units, milk chilling, cattle feed preparation, primary sorting/grading, and FPO packhouses.",
                "key_highlights": [
                    "Animal Husbandry Infrastructure Development Fund (AHIDF): 3% interest subvention for 8 years",
                    "NABARD Dairying Entrepreneurship Development Scheme (DEDS) back-ended capital subsidy",
                    "Commercial dairy farm setup for 2 to 20 crossbred cows or graded Murrah buffaloes",
                    "Financing for bulk milk coolers (BMC), silage baling machines, and chaff cutters",
                    "Credit guarantee coverage up to 25% of total project cost via NABSanrakshan"
                ],
                "required_documents": [
                    "Veterinary certificate of animal suitability / breed purchase invoice",
                    "Proof of shed land possession or long-term lease agreement",
                    "Dairy cooperative (KMF / Nandini) milk supply agreement letter",
                    "Aadhaar, PAN, and FRUITS registration"
                ],
                "calculator_defaults": {
                    "interest_rate": 6.5,
                    "subvention_rate": 3.0,
                    "max_tenure_years": 8
                }
            },
            {
                "id": "solar",
                "title": "Solar Energy Financing (PM-KUSUM)",
                "title_kannada": "ಸೌರಶಕ್ತಿ ಕೃಷಿ ಸಾಲ ಹಾಗೂ ಕುಸುಮ್ ಸಬ್ಸಿಡಿ (PM-KUSUM)",
                "badge": "80% Combined Subsidy",
                "badge_color": "rose",
                "description": "Solarization of agricultural pump sets under PM-KUSUM Component B & C. Farmer pays only 20%, with remaining 80% covered by State and Central subsidies.",
                "key_highlights": [
                    "Combined 80% capital subsidy (30% Central MNRE + 50% Karnataka Govt through KREDL Souramitra)",
                    "Farmer contribution capped at only 20%, which can also be financed via collateral-free bank loans",
                    "Zero monthly electricity bills and continuous reliable daytime irrigation for 25 years",
                    "Component C (Feeder solarization): Farmers can sell surplus daytime solar energy back to BESCOM/MESCOM grid for extra annual revenue",
                    "5-year comprehensive maintenance, insurance, and remote IoT monitoring included free"
                ],
                "required_documents": [
                    "Bhoomi RTC record proving agricultural land ownership",
                    "Borewell / Openwell water source certificate",
                    "FRUITS Karnataka ID and Aadhaar card",
                    "Bank passbook copy for subsidy crediting"
                ],
                "calculator_defaults": {
                    "total_system_cost_5hp": 260000,
                    "subsidy_pct": 80.0,
                    "farmer_share_pct": 20.0,
                    "annual_power_savings": 32000
                }
            }
        ]
    }


from routers.finance_wealth import router as wealth_router

router.include_router(wealth_router)
