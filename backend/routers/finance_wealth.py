"""
Money Management & Future Investing Router (/api/finance/wealth).
Provides:
- Surplus allocation & rural/agri business idea matching
- PAN-based loan tracking with masking, demo seeding & debt-avalanche action plan
- Real loan creation & closure endpoints
- Goal-based investment planner across FD, MF, Insurance & PPF/KVP/SGB
- Pure math returns calculator for FD, SIP, and Lumpsum
"""
import json
import re
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
import models

router = APIRouter(prefix="/wealth", tags=["finance-wealth"])

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

AGRI_BUSINESS_CATALOG = [
    {
        "id": "vermicompost_inputs",
        "name": "Vermicompost & Organic Bio-Inputs Unit",
        "category": "Organic Farm Inputs",
        "tier": "Micro-Enterprise (Up to ₹75,000)",
        "estimated_startup_cost": 25000.0,
        "expected_annual_roi_pct": 85.0,
        "payback_period": "10 - 14 months",
        "risk_level": "Low",
        "subsidy_support": "Up to 50% subsidy under Paramparagat Krishi Vikas Yojana / RKVY",
        "description": "Convert cattle dung and crop residue into high-margin vermicompost and enriched bio-manure for nearby arecanut, ginger, and vegetable farms.",
    },
    {
        "id": "mushroom_shed",
        "name": "Oyster & Milky Mushroom Cultivation Shed",
        "category": "Protected Horticulture",
        "tier": "Micro-Enterprise (Up to ₹75,000)",
        "estimated_startup_cost": 35000.0,
        "expected_annual_roi_pct": 95.0,
        "payback_period": "8 - 12 months",
        "risk_level": "Low-Medium",
        "subsidy_support": "State Horticulture Mission & KVK technical spawn support",
        "description": "Low-footprint indoor cropping using paddy straw bags; delivers weekly cashflow in 35-45 day cycles.",
    },
    {
        "id": "poultry_goat_backyard",
        "name": "Backyard Poultry / Small Ruminant Starter Unit",
        "category": "Allied Livestock",
        "tier": "Micro-Enterprise (Up to ₹75,000)",
        "estimated_startup_cost": 45000.0,
        "expected_annual_roi_pct": 72.0,
        "payback_period": "12 - 16 months",
        "risk_level": "Low-Medium",
        "subsidy_support": "National Livestock Mission (NLM) & state poultry schemes",
        "description": "Raise 100 Naati Koli / Giriraja birds or 3-4 Osmanabadi goats for steady egg, meat, and manure income alongside crop farming.",
    },
    {
        "id": "areca_leaf_plate",
        "name": "Areca Leaf Plate & Eco-Tableware Unit",
        "category": "Agri-Waste Value Addition",
        "tier": "Value-Addition (₹75,000 - ₹2.5 Lakh)",
        "estimated_startup_cost": 120000.0,
        "expected_annual_roi_pct": 68.0,
        "payback_period": "14 - 18 months",
        "risk_level": "Low",
        "subsidy_support": "PMFME 35% credit-linked subsidy & Mudra / PMEGP backing",
        "description": "Press fallen arecanut palm sheaths into biodegradable plates and bowls with strong urban catering and export demand.",
    },
    {
        "id": "goat_breeding_unit",
        "name": "Semi-Intensive Goat / Bannur Sheep Breeding Unit",
        "category": "Commercial Livestock",
        "tier": "Value-Addition (₹75,000 - ₹2.5 Lakh)",
        "estimated_startup_cost": 150000.0,
        "expected_annual_roi_pct": 60.0,
        "payback_period": "16 - 22 months",
        "risk_level": "Medium",
        "subsidy_support": "50% capital subsidy under NLM & NABARD livestock refinance",
        "description": "Stall-fed 10+1 Osmanabadi goat or Bannur sheep breeding model using farm fodder crops to hedge against monsoon crop volatility.",
    },
    {
        "id": "dairy_value_addition",
        "name": "Dairy Value-Addition Micro Unit (Ghee, Paneer & Curd)",
        "category": "Dairy Processing",
        "tier": "Value-Addition (₹75,000 - ₹2.5 Lakh)",
        "estimated_startup_cost": 180000.0,
        "expected_annual_roi_pct": 58.0,
        "payback_period": "15 - 20 months",
        "risk_level": "Low-Medium",
        "subsidy_support": "PMFME 35% grant + AHIDF 3% interest subvention",
        "description": "Convert raw cow/buffalo milk into A2 bilona ghee, fresh paneer, and curd to capture 2x margins over raw procurement rates.",
    },
    {
        "id": "solar_pump_irrigation",
        "name": "Solar Water Pump & Micro-Irrigation Upgrade",
        "category": "Clean Farm Infrastructure",
        "tier": "Mechanization & Infra (₹2.5 Lakh - ₹5 Lakh)",
        "estimated_startup_cost": 250000.0,
        "expected_annual_roi_pct": 45.0,
        "payback_period": "20 - 26 months",
        "risk_level": "Low",
        "subsidy_support": "PM-KUSUM 80% combined subsidy reduces out-of-pocket share to ~₹50,000-₹65,000",
        "description": "Eliminate diesel/grid bottlenecks with daytime solar pumping and automated drip fertigation for multi-crop yields.",
    },
    {
        "id": "custom_hiring_center",
        "name": "Custom Hiring Center (Power Tiller, Brush Cutter & Drone)",
        "category": "Agri Mechanization Rental",
        "tier": "Mechanization & Infra (₹2.5 Lakh - ₹5 Lakh)",
        "estimated_startup_cost": 350000.0,
        "expected_annual_roi_pct": 52.0,
        "payback_period": "18 - 24 months",
        "risk_level": "Medium",
        "subsidy_support": "SMAM / Krishi Yanthradhare 40% - 50% machinery subsidy",
        "description": "Rent out power tillers, sprayers, and chaff cutters to neighboring smallholders on hourly/per-acre rates during peak sowing and harvest.",
    },
    {
        "id": "mini_grading_cold_storage",
        "name": "Mini Grading, Sorting & Solar Cold Storage Unit",
        "category": "Post-Harvest Infrastructure",
        "tier": "Commercial Scale (Above ₹5 Lakh)",
        "estimated_startup_cost": 650000.0,
        "expected_annual_roi_pct": 42.0,
        "payback_period": "24 - 30 months",
        "risk_level": "Medium",
        "subsidy_support": "MIDH / AIF 3% interest subvention + 35% cold-chain capital subsidy",
        "description": "Grade, cure, and store ginger, vegetables, and spices to bypass harvest gluts and sell during peak seasonal price windows.",
    },
]

REFINANCING_ALTERNATIVES = [
    {
        "option": "Kisan Credit Card (KCC) Crop & Allied Loan",
        "effective_rate_pct": 4.0,
        "typical_range": "4.0% effective (7% base minus 3% Prompt Repayment Incentive)",
        "best_for": "Replacing 18%–24% informal moneylender & input dealer credit up to ₹2,00,000 collateral-free (plus ₹2,00,000 dairy sub-limit).",
    },
    {
        "option": "SBI / Canara Bank Agri Gold Loan",
        "effective_rate_pct": 9.0,
        "typical_range": "8.5% – 9.5% p.a.",
        "best_for": "Quick same-day refinancing of high-cost personal or microfinance loans using household gold ornaments.",
    },
    {
        "option": "NABARD Subsidized Term Loans (AHIDF / Farm Mechanization)",
        "effective_rate_pct": 8.5,
        "typical_range": "6.5% – 9.0% p.a. (with 3% subvention / capital subsidy)",
        "best_for": "Refinancing or funding tractors, micro-irrigation, solar pumps, and dairy/value-addition infrastructure.",
    },
]

RISK_ALLOCATIONS = {
    "low": {
        "label": "Safety-First Capital Preservation",
        "weights": {
            "insurance": 15,
            "fd": 45,
            "ppf_kvp_sgb": 30,
            "mutual_funds": 10,
        },
        "summary": "Prioritizes guaranteed principal protection, emergency health/life cover, and predictable fixed returns before moderate market exposure.",
    },
    "moderate": {
        "label": "Balanced Rural Wealth Builder",
        "weights": {
            "insurance": 15,
            "fd": 25,
            "ppf_kvp_sgb": 25,
            "mutual_funds": 35,
        },
        "summary": "Balances liquid fixed deposits and sovereign-backed tax-free compounding with disciplined index/hybrid SIPs to outpace inflation.",
    },
    "growth": {
        "label": "Long-Term Wealth Compounding",
        "weights": {
            "insurance": 10,
            "fd": 15,
            "ppf_kvp_sgb": 20,
            "mutual_funds": 55,
        },
        "summary": "Maximizes long-horizon equity SIP compounding for multi-year goals while retaining an essential insurance and FD safety cushion.",
    },
}

COMMITMENT_GUIDANCE_MAP = {
    "child_education": {
        "label": "Child Higher Education",
        "horizon": "8 - 15 years",
        "recommended_instruments": ["PPF (15-year tax-free)", "Nifty 50 / Flexi-Cap Mutual Fund SIP", "Sukanya Samriddhi Yojana (for girl child)"],
        "reason": "Education costs rise ~8–10% annually; combining equity index SIPs for growth with PPF/SSY sovereign safety builds an inflation-beating college corpus.",
    },
    "marriage": {
        "label": "Family Marriage Fund",
        "horizon": "5 - 10 years",
        "recommended_instruments": ["Sovereign Gold Bonds (SGB)", "Kisan Vikas Patra (KVP)", "Post Office Time Deposit"],
        "reason": "SGB tracks gold prices while paying 2.5% extra annual interest with zero making charges, while KVP/Post Office FD locks in guaranteed cash for wedding expenses.",
    },
    "land_tractor": {
        "label": "Land Expansion / Tractor & Machinery Purchase",
        "horizon": "2 - 5 years",
        "recommended_instruments": ["Bank / Post Office FD & RD", "Conservative Hybrid Mutual Fund", "NABARD Margin-Money Reserve"],
        "reason": "Near-term capital purchases cannot afford equity market drawdowns; liquid FDs and conservative hybrid funds protect your down-payment until the right deal appears.",
    },
    "retirement": {
        "label": "Farmer Retirement & Old-Age Security",
        "horizon": "15+ years",
        "recommended_instruments": ["PPF", "Index Mutual Fund SIP", "Atal Pension Yojana / PM-KMY / NPS"],
        "reason": "Builds an independent monthly pension and tax-free retirement reserve so household dignity does not depend solely on manual farm labor in later years.",
    },
    "emergency_medical": {
        "label": "Medical & Crop-Failure Emergency Buffer",
        "horizon": "Immediate (0 - 12 months)",
        "recommended_instruments": ["PMSBY (₹20/yr) & PMJJBY (₹436/yr)", "Ayushman Bharat / Yashaswini Health Cover + Term Life", "Sweep-In Bank FD (3-6 months expenses)"],
        "reason": "Prevents medical bills or sudden crop loss from forcing you into 24% moneylender debt; health & term insurance cap catastrophic risk while sweep-in FD keeps cash instant.",
    },
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _compute_live_ledger_summary(db: Session) -> Dict[str, float]:
    """Compute live farm net profit and household cashflow from FarmLedgerEntry."""
    entries = db.query(models.FarmLedgerEntry).all()
    farm_cost = 0.0
    crop_revenue = 0.0
    household_expense = 0.0
    household_income = 0.0

    for entry in entries:
        if entry.category in ("cultivation", "irrigation", "harvest"):
            farm_cost += entry.amount
        elif entry.category == "crop_sales":
            crop_revenue += entry.amount
        elif entry.category == "household":
            if entry.entry_type == "expense":
                household_expense += entry.amount
            else:
                household_income += entry.amount

    net_farm_profit = crop_revenue - farm_cost
    net_household_cashflow = household_income - household_expense
    return {
        "gross_crop_revenue": round(crop_revenue, 2),
        "total_farm_operating_cost": round(farm_cost, 2),
        "net_farm_profit": round(net_farm_profit, 2),
        "net_household_cashflow": round(net_household_cashflow, 2),
        "combined_net_cashflow": round(net_farm_profit + net_household_cashflow, 2),
    }


def _validate_and_mask_pan(pan: str) -> str:
    """Validate PAN against ^[A-Z]{5}[0-9]{4}[A-Z]$ and mask middle 3 characters."""
    cleaned = (pan or "").strip()
    if not PAN_REGEX.fullmatch(cleaned):
        raise HTTPException(
            status_code=400,
            detail="Invalid PAN format. Must match 10-character uppercase pattern ^[A-Z]{5}[0-9]{4}[A-Z]$ (e.g., ABCDE1234F).",
        )
    return f"{cleaned[:2]}XXX{cleaned[5:]}"


def _serialize_loan(loan: models.UserLoan) -> dict:
    return {
        "id": loan.id,
        "pan_masked": loan.pan_masked,
        "lender_name": loan.lender_name,
        "loan_type": loan.loan_type,
        "principal_amount": round(loan.principal_amount, 2),
        "outstanding_balance": round(loan.outstanding_balance, 2),
        "interest_rate_annual": round(loan.interest_rate_annual, 2),
        "emi_amount": round(loan.emi_amount or 0.0, 2),
        "next_due_date": loan.next_due_date,
        "interest_accumulated": round(loan.interest_accumulated or 0.0, 2),
        "status": loan.status,
    }


def _parse_commitments(raw_val) -> List[str]:
    if isinstance(raw_val, list):
        return [str(item) for item in raw_val]
    if isinstance(raw_val, str) and raw_val.strip():
        try:
            parsed = json.loads(raw_val)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except Exception:
            return [raw_val]
    return []


def _get_saved_investable_surplus(db: Session) -> Optional[float]:
    profile = db.query(models.WealthPlanProfile).order_by(models.WealthPlanProfile.id.desc()).first()
    if not profile:
        return None
    reserves = (
        profile.household_reserve
        + profile.next_cultivation_reserve
        + profile.harvest_reserve
        + profile.other_reserve
    )
    return round(max(0.0, profile.net_profit - reserves), 2)


def _upsert_wealth_profile(
    db: Session,
    *,
    net_profit: Optional[float] = None,
    household_reserve: Optional[float] = None,
    next_cultivation_reserve: Optional[float] = None,
    harvest_reserve: Optional[float] = None,
    other_reserve: Optional[float] = None,
    life_commitments: Optional[List[str]] = None,
) -> models.WealthPlanProfile:
    profile = db.query(models.WealthPlanProfile).order_by(models.WealthPlanProfile.id.asc()).first()
    if not profile:
        live_profit = _compute_live_ledger_summary(db)["net_farm_profit"] if net_profit is None else net_profit
        profile = models.WealthPlanProfile(
            net_profit=live_profit,
            household_reserve=household_reserve or 0.0,
            next_cultivation_reserve=next_cultivation_reserve or 0.0,
            harvest_reserve=harvest_reserve or 0.0,
            other_reserve=other_reserve or 0.0,
            life_commitments=life_commitments or [],
            updated_at=datetime.utcnow(),
        )
        db.add(profile)
    else:
        if net_profit is not None:
            profile.net_profit = net_profit
        if household_reserve is not None:
            profile.household_reserve = household_reserve
        if next_cultivation_reserve is not None:
            profile.next_cultivation_reserve = next_cultivation_reserve
        if harvest_reserve is not None:
            profile.harvest_reserve = harvest_reserve
        if other_reserve is not None:
            profile.other_reserve = other_reserve
        if life_commitments is not None:
            profile.life_commitments = life_commitments
        profile.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(profile)
    return profile


def _seed_demo_loans_for_pan(db: Session, pan_masked: str) -> List[models.UserLoan]:
    demo_loans = [
        models.UserLoan(
            pan_masked=pan_masked,
            lender_name="Local Input Dealer / Informal Sahukar Credit",
            loan_type="Informal/Moneylender",
            principal_amount=85000.0,
            outstanding_balance=68000.0,
            interest_rate_annual=24.0,
            emi_amount=7500.0,
            next_due_date="2026-12-05",
            interest_accumulated=14200.0,
            status="active",
        ),
        models.UserLoan(
            pan_masked=pan_masked,
            lender_name="Shriram Agri Finance (Tractor & Implements)",
            loan_type="NBFC Tractor Loan",
            principal_amount=240000.0,
            outstanding_balance=145000.0,
            interest_rate_annual=11.5,
            emi_amount=6850.0,
            next_due_date="2026-12-15",
            interest_accumulated=22400.0,
            status="active",
        ),
        models.UserLoan(
            pan_masked=pan_masked,
            lender_name="Canara Bank / PACS Kisan Credit Card",
            loan_type="KCC Crop Loan",
            principal_amount=150000.0,
            outstanding_balance=120000.0,
            interest_rate_annual=4.0,
            emi_amount=5200.0,
            next_due_date="2027-01-10",
            interest_accumulated=4800.0,
            status="active",
        ),
    ]
    for loan in demo_loans:
        db.add(loan)
    db.commit()
    for loan in demo_loans:
        db.refresh(loan)
    return demo_loans


def _build_debt_avalanche_plan(active_loans: List[models.UserLoan], available_surplus: float) -> dict:
    if not active_loans:
        return {
            "strategy": "Debt-Free / Zero Active Liabilities",
            "available_surplus": round(available_surplus, 2),
            "priority_loan": None,
            "payoff_steps": [],
            "total_annual_interest_saved": 0.0,
            "refinancing_alternatives": REFINANCING_ALTERNATIVES,
            "refinance_savings_estimate": {
                "high_interest_debt_total": 0.0,
                "savings_if_moved_to_kcc_4pct": 0.0,
                "savings_if_moved_to_gold_loan_9pct": 0.0,
            },
            "summary_note": "No active loans found. Allocate investable surplus toward emergency reserves and wealth-compounding investments.",
        }

    avalanche_sorted = sorted(
        active_loans,
        key=lambda l: (l.interest_rate_annual, l.outstanding_balance),
        reverse=True,
    )

    remaining_surplus = max(0.0, available_surplus)
    payoff_steps = []
    total_interest_saved = 0.0

    for loan in avalanche_sorted:
        if remaining_surplus <= 0:
            break
        pay_amount = round(min(remaining_surplus, loan.outstanding_balance), 2)
        remaining_balance = round(loan.outstanding_balance - pay_amount, 2)
        annual_saved = round(pay_amount * (loan.interest_rate_annual / 100.0), 2)
        total_interest_saved = round(total_interest_saved + annual_saved, 2)
        remaining_surplus = round(remaining_surplus - pay_amount, 2)

        action = "Full Closure" if remaining_balance == 0 else "Partial Principal Prepayment"
        payoff_steps.append({
            "loan_id": loan.id,
            "lender_name": loan.lender_name,
            "loan_type": loan.loan_type,
            "interest_rate_annual": round(loan.interest_rate_annual, 2),
            "outstanding_before": round(loan.outstanding_balance, 2),
            "amount_allocated": pay_amount,
            "remaining_after": remaining_balance,
            "action": action,
            "estimated_annual_interest_saved": annual_saved,
        })

    top_loan = avalanche_sorted[0]
    high_rate_loans = [l for l in active_loans if l.interest_rate_annual > 9.5]
    high_rate_total = round(sum(l.outstanding_balance for l in high_rate_loans), 2)
    savings_kcc = round(
        sum(l.outstanding_balance * max(0.0, (l.interest_rate_annual - 4.0) / 100.0) for l in high_rate_loans),
        2,
    )
    savings_gold = round(
        sum(l.outstanding_balance * max(0.0, (l.interest_rate_annual - 9.0) / 100.0) for l in high_rate_loans),
        2,
    )

    if payoff_steps:
        first_step = payoff_steps[0]
        summary_note = (
            f"Close '{top_loan.lender_name}' ({top_loan.interest_rate_annual:.1f}% p.a.) first using your surplus. "
            f"Allocating ₹{first_step['amount_allocated']:,.0f} saves ₹{first_step['estimated_annual_interest_saved']:,.0f}/year in interest."
        )
    else:
        summary_note = (
            f"Target '{top_loan.lender_name}' ({top_loan.interest_rate_annual:.1f}% p.a.) first as surplus builds up, "
            f"or refinance high-cost debt (>9.5%) into KCC (4%) / Agri Gold Loan (~9%) to save up to ₹{savings_kcc:,.0f}/year."
        )

    return {
        "strategy": "Debt Avalanche (Highest Interest Rate First)",
        "available_surplus": round(available_surplus, 2),
        "remaining_surplus_after_avalanche": round(remaining_surplus, 2),
        "priority_loan": _serialize_loan(top_loan),
        "payoff_steps": payoff_steps,
        "total_annual_interest_saved": total_interest_saved,
        "refinancing_alternatives": REFINANCING_ALTERNATIVES,
        "refinance_savings_estimate": {
            "high_interest_debt_total": high_rate_total,
            "savings_if_moved_to_kcc_4pct": savings_kcc,
            "savings_if_moved_to_gold_loan_9pct": savings_gold,
        },
        "summary_note": summary_note,
    }


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class AllocateRequest(BaseModel):
    net_profit: Optional[float] = None
    household_reserve: float = Field(default=0.0, ge=0.0)
    next_cultivation_reserve: float = Field(default=0.0, ge=0.0)
    harvest_reserve: float = Field(default=0.0, ge=0.0)
    other_reserve: float = Field(default=0.0, ge=0.0)
    life_commitments: Optional[List[str]] = None


class PanLoansRequest(BaseModel):
    pan: str
    available_surplus: Optional[float] = Field(default=None, ge=0.0)


class LoanCreateRequest(BaseModel):
    pan: Optional[str] = None
    pan_masked: Optional[str] = None
    lender_name: str = Field(..., min_length=1)
    loan_type: str = Field(..., min_length=1)
    principal_amount: float = Field(..., gt=0.0)
    outstanding_balance: Optional[float] = Field(default=None, ge=0.0)
    interest_rate_annual: float = Field(..., ge=0.0)
    emi_amount: float = Field(default=0.0, ge=0.0)
    next_due_date: str = Field(..., min_length=4)
    interest_accumulated: float = Field(default=0.0, ge=0.0)
    status: str = "active"


class InvestPlanRequest(BaseModel):
    monthly_income: Optional[float] = Field(default=None, ge=0.0)
    annual_surplus: Optional[float] = Field(default=None, ge=0.0)
    risk_profile: str = "moderate"
    commitments: List[str] = Field(default_factory=list)


class CalculateReturnsRequest(BaseModel):
    mode: str
    amount: float = Field(..., gt=0.0)
    annual_rate: float = Field(..., ge=0.0)
    years: int = Field(..., ge=1, le=50)


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/allocate")
def allocate_surplus(req: AllocateRequest, db: Session = Depends(get_db)):
    """
    Partition farm net profit into secured reserves and match investable surplus
    with diversified rural/agricultural side-business ideas.
    """
    ledger_summary = _compute_live_ledger_summary(db)
    effective_net_profit = round(
        req.net_profit if req.net_profit is not None else ledger_summary["net_farm_profit"],
        2,
    )
    total_secured_reserves = round(
        req.household_reserve
        + req.next_cultivation_reserve
        + req.harvest_reserve
        + req.other_reserve,
        2,
    )
    raw_surplus = round(effective_net_profit - total_secured_reserves, 2)
    investable_surplus = round(max(0.0, raw_surplus), 2)
    reserve_deficit = round(max(0.0, -raw_surplus), 2)

    profile = _upsert_wealth_profile(
        db,
        net_profit=effective_net_profit,
        household_reserve=round(req.household_reserve, 2),
        next_cultivation_reserve=round(req.next_cultivation_reserve, 2),
        harvest_reserve=round(req.harvest_reserve, 2),
        other_reserve=round(req.other_reserve, 2),
        life_commitments=req.life_commitments,
    )

    if investable_surplus <= 0:
        surplus_tier = "Reserve Protection Mode (No Surplus Yet)"
    elif investable_surplus <= 75000:
        surplus_tier = "Micro-Enterprise Tier (Up to ₹75,000)"
    elif investable_surplus <= 250000:
        surplus_tier = "Value-Addition Tier (₹75,001 – ₹2,50,000)"
    elif investable_surplus <= 500000:
        surplus_tier = "Mechanization & Infra Tier (₹2,50,001 – ₹5,00,000)"
    else:
        surplus_tier = "Commercial Agribusiness & Storage Tier (Above ₹5,00,000)"

    annotated_ideas = []
    for idea in AGRI_BUSINESS_CATALOG:
        cost = idea["estimated_startup_cost"]
        fits = investable_surplus >= cost
        annotated_ideas.append({
            **idea,
            "fits_current_surplus": fits,
            "funding_gap": 0.0 if fits else round(cost - investable_surplus, 2),
        })

    affordable_ideas = [i for i in annotated_ideas if i["fits_current_surplus"]]
    affordable_ideas.sort(key=lambda x: x["estimated_startup_cost"], reverse=True)

    stretch_ideas = [i for i in annotated_ideas if not i["fits_current_surplus"]]
    stretch_ideas.sort(key=lambda x: x["estimated_startup_cost"])

    # Always return matched ideas if affordable, otherwise show lowest-cost starter targets
    matched_business_ideas = affordable_ideas if affordable_ideas else stretch_ideas[:3]

    return {
        "profile_id": profile.id,
        "profit_source": "custom_input" if req.net_profit is not None else "live_finance_ledger",
        "net_profit": effective_net_profit,
        "live_ledger_net_profit": ledger_summary["net_farm_profit"],
        "reserves": {
            "household_reserve": round(req.household_reserve, 2),
            "next_cultivation_reserve": round(req.next_cultivation_reserve, 2),
            "harvest_reserve": round(req.harvest_reserve, 2),
            "other_reserve": round(req.other_reserve, 2),
        },
        "total_secured_reserves": total_secured_reserves,
        "investable_surplus": investable_surplus,
        "reserve_deficit": reserve_deficit,
        "surplus_tier": surplus_tier,
        "matched_business_ideas": matched_business_ideas,
        "stretch_business_ideas": stretch_ideas[:3] if affordable_ideas else stretch_ideas[3:6],
        "life_commitments": _parse_commitments(profile.life_commitments),
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


@router.post("/pan-loans")
def fetch_pan_loans(req: PanLoansRequest, db: Session = Depends(get_db)):
    """
    Validate PAN, mask to ABXXX1234F, seed 3 realistic demo loans if absent,
    and compute outstanding totals, sorted upcoming dues, and debt-avalanche plan.
    """
    pan_masked = _validate_and_mask_pan(req.pan)

    loans = (
        db.query(models.UserLoan)
        .filter(models.UserLoan.pan_masked == pan_masked)
        .order_by(models.UserLoan.next_due_date.asc(), models.UserLoan.id.asc())
        .all()
    )
    seeded_now = False
    if not loans:
        loans = _seed_demo_loans_for_pan(db, pan_masked)
        seeded_now = True

    active_loans = [l for l in loans if l.status == "active"]
    total_outstanding = round(sum(l.outstanding_balance for l in active_loans), 2)
    total_interest_accumulated = round(sum(l.interest_accumulated or 0.0 for l in loans), 2)

    upcoming_dues = [
        {
            "loan_id": l.id,
            "lender_name": l.lender_name,
            "loan_type": l.loan_type,
            "next_due_date": l.next_due_date,
            "emi_amount": round(l.emi_amount or 0.0, 2),
            "outstanding_balance": round(l.outstanding_balance, 2),
            "interest_rate_annual": round(l.interest_rate_annual, 2),
        }
        for l in sorted(active_loans, key=lambda item: item.next_due_date)
    ]

    if req.available_surplus is not None:
        surplus_for_plan = req.available_surplus
    else:
        saved_surplus = _get_saved_investable_surplus(db)
        surplus_for_plan = (
            saved_surplus
            if saved_surplus is not None
            else max(0.0, _compute_live_ledger_summary(db)["net_farm_profit"])
        )

    action_plan = _build_debt_avalanche_plan(active_loans, surplus_for_plan)

    return {
        "pan_masked": pan_masked,
        "seeded_demo_loans": seeded_now,
        "total_loans": len(loans),
        "active_loans_count": len(active_loans),
        "total_outstanding": total_outstanding,
        "total_interest_accumulated": total_interest_accumulated,
        "upcoming_dues": upcoming_dues,
        "loans": [_serialize_loan(l) for l in loans],
        "action_plan": action_plan,
    }


@router.post("/loans")
def add_user_loan(req: LoanCreateRequest, db: Session = Depends(get_db)):
    """Add a real loan under a validated/masked PAN."""
    if req.pan:
        pan_masked = _validate_and_mask_pan(req.pan)
    elif req.pan_masked and req.pan_masked.strip():
        candidate = req.pan_masked.strip()
        if PAN_REGEX.fullmatch(candidate):
            pan_masked = f"{candidate[:2]}XXX{candidate[5:]}"
        else:
            pan_masked = candidate
    else:
        raise HTTPException(status_code=400, detail="Either 'pan' or 'pan_masked' is required.")

    status_normalized = req.status.strip().lower()
    if status_normalized not in ("active", "closed"):
        raise HTTPException(status_code=400, detail="Status must be 'active' or 'closed'.")

    outstanding = (
        0.0
        if status_normalized == "closed"
        else (req.outstanding_balance if req.outstanding_balance is not None else req.principal_amount)
    )

    new_loan = models.UserLoan(
        pan_masked=pan_masked,
        lender_name=req.lender_name.strip(),
        loan_type=req.loan_type.strip(),
        principal_amount=round(req.principal_amount, 2),
        outstanding_balance=round(outstanding, 2),
        interest_rate_annual=round(req.interest_rate_annual, 2),
        emi_amount=round(req.emi_amount, 2),
        next_due_date=req.next_due_date.strip(),
        interest_accumulated=round(req.interest_accumulated, 2),
        status=status_normalized,
    )
    db.add(new_loan)
    db.commit()
    db.refresh(new_loan)

    return {"success": True, "loan": _serialize_loan(new_loan)}


@router.patch("/loans/{loan_id}/close")
def close_user_loan(loan_id: int, db: Session = Depends(get_db)):
    """Mark an existing loan as closed and clear its active outstanding balance."""
    loan = db.query(models.UserLoan).filter(models.UserLoan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    previous_outstanding = round(loan.outstanding_balance, 2)
    loan.status = "closed"
    loan.outstanding_balance = 0.0
    db.commit()
    db.refresh(loan)

    return {
        "success": True,
        "previous_outstanding": previous_outstanding,
        "loan": _serialize_loan(loan),
    }


@router.post("/invest-plan")
def generate_investment_plan(req: InvestPlanRequest, db: Session = Depends(get_db)):
    """
    Generate a tailored wealth-allocation plan across Bank/Post Office FD,
    Mutual Funds (SIP/Index/Hybrid), Insurance (PMJJBY, PMSBY, Term & Health),
    and PPF/KVP/SGB aligned with risk profile and life commitments.
    """
    risk_key = req.risk_profile.strip().lower()
    if risk_key not in RISK_ALLOCATIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid risk_profile. Choose from 'low', 'moderate', or 'growth'.",
        )

    if req.annual_surplus is not None and req.annual_surplus > 0:
        annual_budget = round(req.annual_surplus, 2)
        monthly_budget = round(annual_budget / 12.0, 2)
        income_basis = "annual_surplus"
    elif req.monthly_income is not None and req.monthly_income > 0:
        # Recommend allocating 25% of monthly income toward structured savings & protection
        monthly_budget = round(req.monthly_income * 0.25, 2)
        annual_budget = round(monthly_budget * 12.0, 2)
        income_basis = "monthly_income_25pct_savings_rule"
    else:
        saved_surplus = _get_saved_investable_surplus(db)
        annual_budget = round(saved_surplus if saved_surplus is not None else 0.0, 2)
        monthly_budget = round(annual_budget / 12.0, 2)
        income_basis = "saved_wealth_profile"

    cleaned_commitments = [c.strip() for c in req.commitments if c and c.strip()]
    if cleaned_commitments:
        _upsert_wealth_profile(db, life_commitments=cleaned_commitments)

    risk_cfg = RISK_ALLOCATIONS[risk_key]
    weights = dict(risk_cfg["weights"])

    # Slight protective tilt if emergency_medical is prioritized
    if "emergency_medical" in cleaned_commitments and weights["insurance"] < 15:
        shift = 15 - weights["insurance"]
        weights["insurance"] += shift
        weights["mutual_funds"] = max(5, weights["mutual_funds"] - shift)

    bucket_definitions = [
        {
            "key": "insurance",
            "category": "Insurance (PMJJBY, PMSBY, Term & Health)",
            "pct": weights["insurance"],
            "expected_return_note": "Risk Protection (Zero Asset Loss Shield)",
            "instruments": [
                "PMJJBY (₹436/year for ₹2 Lakh Life Cover)",
                "PMSBY (₹20/year for ₹2 Lakh Accidental Cover)",
                "Family Floater Health Cover / Ayushman Bharat / Yashaswini + Pure Term Life",
            ],
            "rationale": "Protects farm capital and family reserves from sudden medical bills or income loss before chasing returns.",
        },
        {
            "key": "fd",
            "category": "Bank/Post Office FD",
            "pct": weights["fd"],
            "expected_return_note": "6.7% – 7.5% p.a. (Guaranteed)",
            "instruments": [
                "Post Office Time Deposit (1–5 yr) & Recurring Deposit",
                "Sweep-in Bank Fixed Deposit for instant harvest/emergency liquidity",
                "Senior Citizen Savings Scheme (if parents are 60+)",
            ],
            "rationale": "Keeps near-term farming, medical, and machinery funds liquid with guaranteed capital safety.",
        },
        {
            "key": "ppf_kvp_sgb",
            "category": "PPF/KVP/SGB",
            "pct": weights["ppf_kvp_sgb"],
            "expected_return_note": "7.1% – 10.5% p.a. (Sovereign Backed)",
            "instruments": [
                "Public Provident Fund (PPF — 7.1% EEE tax-free compounding)",
                "Kisan Vikas Patra (KVP — doubles corpus with govt guarantee)",
                "Sovereign Gold Bonds (SGB — gold price growth + 2.5% annual interest)",
            ],
            "rationale": "Sovereign-backed long-term safety ideal for marriage gold planning, children's education, and retirement.",
        },
        {
            "key": "mutual_funds",
            "category": "Mutual Funds (SIP/Index/Hybrid)",
            "pct": weights["mutual_funds"],
            "expected_return_note": "10.0% – 13.5% p.a. (Market-Linked Long-Term)",
            "instruments": [
                "Nifty 50 Index Fund SIP (low-cost broad equity growth)",
                "Balanced Advantage / Conservative Hybrid Fund (auto-rebalanced)",
                "Flexi-Cap Equity SIP for 7+ year wealth goals",
            ],
            "rationale": "Beats inflation over 5–15 year horizons through disciplined monthly SIP rupee-cost averaging.",
        },
    ]

    allocations = []
    for b in bucket_definitions:
        pct = b["pct"]
        allocations.append({
            "key": b["key"],
            "category": b["category"],
            "allocation_pct": pct,
            "monthly_amount": round(monthly_budget * (pct / 100.0), 2),
            "annual_amount": round(annual_budget * (pct / 100.0), 2),
            "expected_return_note": b["expected_return_note"],
            "instruments": b["instruments"],
            "rationale": b["rationale"],
        })

    commitment_guidance = []
    for comm in cleaned_commitments:
        norm = comm.lower()
        if norm in COMMITMENT_GUIDANCE_MAP:
            info = COMMITMENT_GUIDANCE_MAP[norm]
            commitment_guidance.append({"commitment": norm, **info})
        else:
            commitment_guidance.append({
                "commitment": comm,
                "label": comm.replace("_", " ").title(),
                "horizon": "3 - 7 years",
                "recommended_instruments": [
                    "Post Office RD / Bank FD for near-term certainty",
                    "Balanced Advantage Mutual Fund SIP for inflation protection",
                ],
                "reason": f"Earmark a dedicated recurring transfer for '{comm}' so farm operating cashflow stays separated from personal milestone savings.",
            })

    return {
        "risk_profile": risk_key,
        "risk_label": risk_cfg["label"],
        "risk_summary": risk_cfg["summary"],
        "income_basis": income_basis,
        "monthly_income_input": req.monthly_income,
        "monthly_investment_budget": monthly_budget,
        "annual_investment_budget": annual_budget,
        "allocations": allocations,
        "commitment_guidance": commitment_guidance,
    }


@router.post("/calculate-returns")
def calculate_returns(req: CalculateReturnsRequest):
    """
    Pure math investment calculator supporting 'fd', 'sip', and 'lumpsum'.
    Returns total_invested, estimated_returns, maturity_value, and yearly_breakdown.
    """
    mode = req.mode.strip().lower()
    if mode not in ("fd", "sip", "lumpsum"):
        raise HTTPException(
            status_code=400,
            detail="Invalid mode. Supported modes are 'fd', 'sip', and 'lumpsum'.",
        )

    amount = req.amount
    r = req.annual_rate / 100.0
    years = req.years
    yearly_breakdown = []

    if mode == "fd":
        # Quarterly compounding (standard Indian Bank / Post Office FD convention)
        for y in range(1, years + 1):
            value = amount * ((1.0 + r / 4.0) ** (4 * y))
            yearly_breakdown.append({
                "year": y,
                "invested": round(amount, 2),
                "value": round(value, 2),
            })
    elif mode == "lumpsum":
        # Annual compounding
        for y in range(1, years + 1):
            value = amount * ((1.0 + r) ** y)
            yearly_breakdown.append({
                "year": y,
                "invested": round(amount, 2),
                "value": round(value, 2),
            })
    else:
        # SIP: monthly contribution compounded monthly (annuity due)
        monthly_rate = r / 12.0
        for y in range(1, years + 1):
            months = 12 * y
            invested = amount * months
            if monthly_rate == 0:
                value = invested
            else:
                value = amount * (((1.0 + monthly_rate) ** months - 1.0) / monthly_rate) * (1.0 + monthly_rate)
            yearly_breakdown.append({
                "year": y,
                "invested": round(invested, 2),
                "value": round(value, 2),
            })

    total_invested = yearly_breakdown[-1]["invested"]
    maturity_value = yearly_breakdown[-1]["value"]
    estimated_returns = round(maturity_value - total_invested, 2)

    return {
        "mode": mode,
        "amount": round(amount, 2),
        "annual_rate": round(req.annual_rate, 2),
        "years": years,
        "total_invested": total_invested,
        "estimated_returns": estimated_returns,
        "maturity_value": maturity_value,
        "yearly_breakdown": yearly_breakdown,
    }
