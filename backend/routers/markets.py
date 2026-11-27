"""
Commodity Market Analytics & 6-Year Historical Trends Router — Sprint 4.
Handles 14-day daily price history, cross-mandi APMC selling price comparisons,
and 6-year seasonal price trends (2021-2026) for Karnataka commodities.
When DATA_GOV_API_KEY is set, fetches live Agmarknet prices from data.gov.in
and upserts them into the local SQLite MandiPrice table.
"""
import logging
import threading
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db, SessionLocal
import models
import config

logger = logging.getLogger("markets")

router = APIRouter(prefix="/api/markets", tags=["markets"])

# Canonical commodity name aliases mapping
COMMODITY_ALIASES = {
    "paddy": "Paddy (Fine)",
    "paddy (fine)": "Paddy (Fine)",
    "paddy (coarse)": "Paddy (Coarse)",
    "areca": "Areca Nut (Chali)",
    "areca nut": "Areca Nut (Chali)",
    "arecanut": "Areca Nut (Chali)",
    "areca nut (chali)": "Areca Nut (Chali)",
    "areca nut (red)": "Areca Nut (Red)",
    "ginger": "Ginger (Fresh)",
    "ginger (fresh)": "Ginger (Fresh)",
    "ginger (dry)": "Ginger (Dry)",
    "corn": "Corn / Maize",
    "maize": "Corn / Maize",
    "corn / maize": "Corn / Maize",
    "pepper": "Black Pepper",
    "black pepper": "Black Pepper",
    "coconut": "Coconut (Copra)",
    "coconut (copra)": "Coconut (Copra)",
    "coconut (tender)": "Coconut (Tender)",
    "tomato": "Tomato",
    "onion": "Onion",
    "turmeric": "Turmeric",
    "groundnut": "Groundnut",
    "sunflower": "Sunflower",
}


def _resolve_commodity_name(name: str) -> str:
    cleaned = name.strip().lower()
    return COMMODITY_ALIASES.get(cleaned, name)


# Mapping from canonical commodity name to Agmarknet query string
AGMARKNET_QUERY_MAP = {
    "Paddy (Fine)": "Paddy",
    "Paddy (Coarse)": "Paddy",
    "Areca Nut (Chali)": "Arecanut",
    "Areca Nut (Red)": "Arecanut",
    "Ginger (Fresh)": "Ginger",
    "Ginger (Dry)": "Ginger",
    "Corn / Maize": "Maize",
    "Black Pepper": "Pepper",
    "Coconut (Copra)": "Coconut",
    "Coconut (Tender)": "Coconut",
}

AGMARKNET_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"


def _fetch_agmarknet_prices(commodity_name: str, db: Optional[Session] = None) -> bool:
    """
    Fetch live prices from data.gov.in Agmarknet API and upsert into MandiPrice table.
    Returns True if live data was fetched and upserted, False otherwise.
    Uses safe timeouts (2.5s connect, 4.0s read), handles network errors gracefully without hanging,
    and manages its own dedicated DB session if none provided or when running off-thread.
    """
    if not config.has_data_gov():
        return False

    agmarknet_query = AGMARKNET_QUERY_MAP.get(commodity_name, commodity_name.split(" ")[0])
    url = (
        f"https://api.data.gov.in/resource/{AGMARKNET_RESOURCE_ID}"
        f"?api-key={config.DATA_GOV_API_KEY}"
        f"&format=json"
        f"&filters[commodity]={agmarknet_query}"
        f"&filters[state]=Karnataka"
        f"&limit=10"
    )

    is_main_thread = (threading.current_thread() is threading.main_thread())
    created_local_db = False
    session = db
    # Use dedicated session if none provided or if running in a background/worker thread
    if session is None or not is_main_thread:
        session = SessionLocal()
        created_local_db = True

    t0 = time.perf_counter()
    logger.info("[Agmarknet] Querying live prices for '%s' (filter=%s) from data.gov.in...", commodity_name, agmarknet_query)

    try:
        # Use httpx with explicit safe timeouts to prevent hanging
        timeout = httpx.Timeout(connect=2.5, read=4.0, write=4.0, pool=5.0)
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            elapsed = time.perf_counter() - t0
            if resp.status_code != 200:
                logger.warning("[Agmarknet] data.gov.in API returned HTTP %s for %s in %.2fs", resp.status_code, commodity_name, elapsed)
                return False
            data = resp.json()
            records = data.get("records", [])
            if not records:
                logger.info("[Agmarknet] No records returned for %s in %.2fs", commodity_name, elapsed)
                return False

            upsert_count = 0
            for rec in records:
                market = rec.get("market", "Unknown")
                district = rec.get("district", "")
                min_p = float(rec.get("min_price", 0) or 0)
                max_p = float(rec.get("max_price", 0) or 0)
                modal_p = float(rec.get("modal_price", 0) or 0)
                if modal_p <= 0:
                    continue

                # Upsert: update if exists, insert if not
                existing = session.query(models.MandiPrice).filter(
                    models.MandiPrice.commodity_name == commodity_name,
                    models.MandiPrice.market_name == market,
                ).first()
                if existing:
                    existing.min_price = min_p
                    existing.max_price = max_p
                    existing.modal_price = modal_p
                else:
                    session.add(models.MandiPrice(
                        commodity_name=commodity_name,
                        market_name=market,
                        district=district,
                        state="Karnataka",
                        min_price=min_p,
                        max_price=max_p,
                        modal_price=modal_p,
                        arrivals_tonnes=0.0,
                    ))
                upsert_count += 1

            session.commit()
            logger.info("[Agmarknet] Successfully upserted %d live records for %s in %.2fs", upsert_count, commodity_name, elapsed)
            return True
    except httpx.TimeoutException as e:
        elapsed = time.perf_counter() - t0
        logger.warning("[Agmarknet] Timeout (%.2fs) while fetching Agmarknet prices for %s: %s", elapsed, commodity_name, e)
        return False
    except httpx.RequestError as e:
        elapsed = time.perf_counter() - t0
        logger.warning("[Agmarknet] Network request error (%.2fs) fetching prices for %s: %s", elapsed, commodity_name, e)
        return False
    except Exception as e:
        elapsed = time.perf_counter() - t0
        logger.warning("[Agmarknet] Error (%.2fs) fetching Agmarknet prices for %s: %s", elapsed, commodity_name, e)
        if session:
            try:
                session.rollback()
            except Exception:
                pass
        return False
    finally:
        if created_local_db and session:
            try:
                session.close()
            except Exception:
                pass


@router.get("/commodities/list")
def list_available_commodities(db: Session = Depends(get_db)):
    """Return all available commodities for market analytics."""
    commodities = db.query(models.Commodity).all()
    res = []
    for c in commodities:
        diff = c.current_price - c.previous_price
        pct = round((diff / c.previous_price) * 100, 2) if c.previous_price else 0
        trend = "up" if diff > 0 else ("down" if diff < 0 else "stable")
        res.append({
            "id": c.id,
            "name": c.name,
            "name_kannada": c.name_kannada,
            "category": c.category,
            "unit": c.unit,
            "current_price": c.current_price,
            "trend": trend,
            "change_pct": pct,
            "market": c.market,
        })
    return res


@router.get("/{commodity_name}")
def get_commodity_analytics(commodity_name: str, db: Session = Depends(get_db)):
    """
    Returns complete commodity market analytics:
    1. Basic metadata & current rate
    2. Past 2-Week daily price history (14 days min, max, modal)
    3. Cross-Mandi selling price comparison across 5-6 regional Karnataka APMC markets
    4. 5-to-6 Year seasonal monthly price trends (2021-2026) with peak & drop months highlighted
    5. Actionable selling timing recommendations for farmers
    """
    canonical_name = _resolve_commodity_name(commodity_name)

    # Sprint 4: Try to refresh from Agmarknet live API
    agmarknet_live = _fetch_agmarknet_prices(canonical_name, db)

    # 1. Fetch commodity record
    commodity = db.query(models.Commodity).filter(
        (models.Commodity.name == canonical_name) |
        (models.Commodity.name.ilike(f"%{commodity_name}%"))
    ).first()

    if not commodity:
        # Fallback to first commodity if not found
        commodity = db.query(models.Commodity).first()
        if not commodity:
            raise HTTPException(status_code=404, detail="No commodity data found.")
        canonical_name = commodity.name

    diff = commodity.current_price - commodity.previous_price
    pct = round((diff / commodity.previous_price) * 100, 2) if commodity.previous_price else 0
    trend = "up" if diff > 0 else ("down" if diff < 0 else "stable")

    # 2. Fetch 2-Week Price History (14 days)
    history_records = (
        db.query(models.TwoWeekHistory)
        .filter(models.TwoWeekHistory.commodity_name == commodity.name)
        .order_by(models.TwoWeekHistory.day_offset.asc()) # 0 is today, 13 is 13 days ago
        .all()
    )

    two_week_data = []
    for h in history_records:
        two_week_data.append({
            "day_offset": h.day_offset,
            "date": h.date_str,
            "min_price": h.min_price,
            "max_price": h.max_price,
            "modal_price": h.modal_price,
        })

    # 3. Fetch Cross-Mandi Selling Price Comparison (5–6 APMC markets)
    mandi_records = (
        db.query(models.MandiPrice)
        .filter(models.MandiPrice.commodity_name == commodity.name)
        .order_by(models.MandiPrice.modal_price.desc())
        .all()
    )

    cross_mandi_data = []
    base_price = commodity.current_price
    best_market = None
    max_rate = 0

    for m in mandi_records:
        diff_from_base = m.modal_price - base_price
        if m.modal_price > max_rate:
            max_rate = m.modal_price
            best_market = m.market_name

        cross_mandi_data.append({
            "market_name": m.market_name,
            "district": m.district,
            "state": m.state,
            "min_price": m.min_price,
            "max_price": m.max_price,
            "modal_price": m.modal_price,
            "arrivals_tonnes": m.arrivals_tonnes,
            "diff_from_base": round(diff_from_base, 1),
            "diff_pct": round((diff_from_base / base_price) * 100, 1) if base_price else 0,
            "is_highest": False,
        })

    # Mark highest market
    for m in cross_mandi_data:
        if m["market_name"] == best_market:
            m["is_highest"] = True

    # 4. Fetch 6-Year Seasonal Price Trends (2021–2026)
    seasonal_records = (
        db.query(models.SeasonalHistoricalPrice)
        .filter(models.SeasonalHistoricalPrice.commodity_name == commodity.name)
        .order_by(models.SeasonalHistoricalPrice.year.asc(), models.SeasonalHistoricalPrice.month.asc())
        .all()
    )

    seasonal_data = []
    monthly_aggregates = {} # month -> [prices]
    peak_months = set()
    drop_months = set()

    for s in seasonal_records:
        seasonal_data.append({
            "year": s.year,
            "month": s.month,
            "month_name": s.month_name,
            "label": f"{s.month_name[:3]} '{str(s.year)[2:]}",
            "avg_price": s.avg_price,
            "is_peak": s.is_peak,
            "is_drop": s.is_drop,
            "season_note": s.season_note,
        })
        if s.is_peak:
            peak_months.add(s.month_name)
        if s.is_drop:
            drop_months.add(s.month_name)

        if s.month_name not in monthly_aggregates:
            monthly_aggregates[s.month_name] = []
        monthly_aggregates[s.month_name].append(s.avg_price)

    # Calculate 6-year average per month (Jan–Dec)
    monthly_pattern = []
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for m in month_order:
        vals = monthly_aggregates.get(m, [])
        if vals:
            avg_val = round(sum(vals) / len(vals), 1)
            monthly_pattern.append({
                "month": m,
                "six_year_avg": avg_val,
                "is_peak": m in peak_months,
                "is_drop": m in drop_months,
            })

    # 5. Farmer Selling Timing Recommendations based on seasonal analytics
    timing_recommendations = _generate_timing_advice(commodity.name, peak_months, drop_months)

    return {
        "commodity": {
            "id": commodity.id,
            "name": commodity.name,
            "name_kannada": commodity.name_kannada,
            "category": commodity.category,
            "unit": commodity.unit,
            "current_price": commodity.current_price,
            "previous_price": commodity.previous_price,
            "trend": trend,
            "change_pct": pct,
            "min_price": commodity.min_price,
            "max_price": commodity.max_price,
            "market": commodity.market,
            "state": commodity.state,
            "updated_at": commodity.updated_at.isoformat(),
        },
        "two_week_history": two_week_data,
        "cross_mandi_comparison": cross_mandi_data,
        "best_mandi": best_market,
        "highest_modal_price": max_rate,
        "six_year_seasonal": seasonal_data,
        "monthly_pattern": monthly_pattern,
        "peak_months": list(peak_months),
        "drop_months": list(drop_months),
        "selling_advisory": timing_recommendations,
        "data_source": "Agmarknet Live (data.gov.in)" if agmarknet_live else "SQLite Cache",
        "api_status": {"data_gov": "live" if agmarknet_live else "demo"},
    }


def _generate_timing_advice(name: str, peaks: set, drops: set) -> dict:
    """Generate farmer selling timing advisory tailored to Karnataka crop cycles."""
    peaks_str = ", ".join(sorted(peaks)) if peaks else "May – July"
    drops_str = ", ".join(sorted(drops)) if drops else "December – January"

    if "areca" in name.lower():
        return {
            "headline": "High Seasonal Value Window Approaching in Pre-Monsoon",
            "headline_kannada": "ಮುಂಗಾರಿಗೆ ಮುನ್ನ (ಮೇ-ಜುಲೈ) ಅಡಿಕೆ ಗರಿಷ್ಠ ಬೆಲೆ ಕಾಣುವ ಸಾಧ್ಯತೆ",
            "advice": (
                f"Historical 6-year data reveals peak prices typically occur during {peaks_str} "
                "when market arrivals drop. Heavy post-harvest glut in {drops_str} depresses prices. "
                "Recommendation: Farmers with scientific godown storage should hold good quality Chali "
                "for sale in April–June to maximize return by ₹3,000–₹5,000 per quintal."
            ),
            "best_selling_window": "April to July",
            "storage_feasibility": "High (well-dried Chali stores up to 12 months with minimal weight loss)",
        }
    elif "paddy" in name.lower():
        return {
            "headline": "Post-Harvest Trough in Progress; Price Recovery by Mid-Year",
            "headline_kannada": "ಕೊಯ್ಲಿನ ನಂತರ ದರ ಇಳಿಕೆ ಸಾಮಾನ್ಯ; ಜೂನ್-ಆಗಸ್ಟ್‌ನಲ್ಲಿ ಚೇತರಿಕೆ",
            "advice": (
                f"Paddy experiences seasonal price troughs during peak harvest months ({drops_str}) "
                f"due to massive arrivals. Prices recover strongly in {peaks_str}. "
                "Recommendation: Avoid distress selling below MSP (₹2,183/q). Avail e-NWR warehouse loans "
                "or Karnataka Raitha Sanjeevini pledge loan scheme to hold stock for 3–4 months."
            ),
            "best_selling_window": "May to August",
            "storage_feasibility": "Medium (requires moisture <13% and rat-proof godowns)",
        }
    elif "ginger" in name.lower():
        return {
            "headline": "Price Surge in Dry Season (February – April)",
            "headline_kannada": "ಬೇಸಿಗೆಯಲ್ಲಿ (ಫೆಬ್ರವರಿ-ಏಪ್ರಿಲ್) ಶುಂಠಿ ಬೆಲೆ ತೀವ್ರ ಏರಿಕೆ",
            "advice": (
                f"Fresh ginger harvest floods mandis between November and January causing price drops. "
                f"Peak prices consistently occur in {peaks_str} for seed ginger and preserved stock. "
                "Recommendation: Stage sales in 2–3 tranches; sell partial yield now to cover labor, "
                "preserve remainder in underground pits or cold storage for summer demand."
            ),
            "best_selling_window": "March to May",
            "storage_feasibility": "Moderate (underground pit storage or cold chain required)",
        }
    elif "corn" in name.lower() or "maize" in name.lower():
        return {
            "headline": "Poultry Feed Industry Demand Spikes in Monsoon Months",
            "headline_kannada": "ಕೋಳಿ ಆಹಾರ ಉದ್ಯಮದಿಂದ ಜುಲೈ-ಸೆಪ್ಟೆಂಬರ್‌ನಲ್ಲಿ ಮೆಕ್ಕೆಜೋಳಕ್ಕೆ ಹೆಚ್ಚಿನ ಬೇಡಿಕೆ",
            "advice": (
                f"Rabi and Kharif peak arrivals in {drops_str} create supply surplus. "
                f"Poultry and starch industries aggressively procure stock during {peaks_str}. "
                "Recommendation: Ensure grain moisture is below 12% to prevent aflatoxin and sell to Davangere/Ranebennur industrial buyers."
            ),
            "best_selling_window": "June to September",
            "storage_feasibility": "High with airtight bags (Hermetic bags recommended)",
        }
    else:
        return {
            "headline": "Market Trend Favorable in Off-Season Months",
            "headline_kannada": "ಹಂಗಾಮಿಲ್ಲದ ಸಮಯದಲ್ಲಿ ಉತ್ತಮ ಮಾರುಕಟ್ಟೆ ದರ",
            "advice": (
                f"Historical patterns show seasonal peak prices around {peaks_str}. "
                "Stagger your market offerings across high-demand months to obtain higher average realization."
            ),
            "best_selling_window": peaks_str,
            "storage_feasibility": "Consult local APMC warehouse",
        }
