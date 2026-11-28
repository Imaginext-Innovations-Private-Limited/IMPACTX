"""SQLAlchemy ORM models for Farm Advisor (Sprint 1 & Sprint 2)."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, JSON
from database import Base


class Commodity(Base):
    __tablename__ = "commodities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    name_kannada = Column(String(100))
    name_hindi = Column(String(100))
    category = Column(String(50))          # grain, spice, plantation, vegetable, oilseed
    unit = Column(String(20), default="quintal")
    current_price = Column(Float, nullable=False)
    previous_price = Column(Float, nullable=False)
    min_price = Column(Float)
    max_price = Column(Float)
    market = Column(String(100), default="APMC Bangalore")
    state = Column(String(50), default="Karnataka")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MandiPrice(Base):
    __tablename__ = "mandi_prices"

    id = Column(Integer, primary_key=True, index=True)
    commodity_name = Column(String(100), nullable=False, index=True)
    market_name = Column(String(100), nullable=False)
    district = Column(String(50), nullable=False)
    state = Column(String(50), default="Karnataka")
    min_price = Column(Float, nullable=False)
    max_price = Column(Float, nullable=False)
    modal_price = Column(Float, nullable=False)
    arrivals_tonnes = Column(Float, default=10.0)
    recorded_date = Column(String(20), default=datetime.utcnow().strftime("%Y-%m-%d"))


class MandiPriceCache(Base):
    __tablename__ = "mandi_price_cache"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(50), nullable=False, index=True)
    commodity = Column(String(100), nullable=False, index=True)
    commodity_id = Column(Integer, index=True, nullable=True)
    category = Column(String(50), nullable=True)
    unit = Column(String(20), default="quintal")
    district = Column(String(50))
    market = Column(String(100))
    min_price = Column(Float, nullable=False)
    max_price = Column(Float, nullable=False)
    modal_price = Column(Float, nullable=False)
    previous_price = Column(Float, nullable=True)
    source = Column(String(30), default="fallback")  # "data_gov" | "fallback"
    cached_at = Column(DateTime, default=datetime.utcnow, index=True)


class TwoWeekHistory(Base):
    __tablename__ = "two_week_history"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(50), default="Karnataka", index=True)
    commodity_name = Column(String(100), nullable=False, index=True)
    day_offset = Column(Integer, nullable=False) # 0 = today, 13 = 13 days ago
    date_str = Column(String(20), nullable=False)
    min_price = Column(Float, nullable=False)
    max_price = Column(Float, nullable=False)
    modal_price = Column(Float, nullable=False)


class SeasonalHistoricalPrice(Base):
    __tablename__ = "seasonal_historical_prices"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(50), default="Karnataka", index=True)
    commodity_name = Column(String(100), nullable=False, index=True)
    year = Column(Integer, nullable=False)       # 2021 to 2026
    month = Column(Integer, nullable=False)      # 1 to 12
    month_name = Column(String(15), nullable=False)
    avg_price = Column(Float, nullable=False)
    is_peak = Column(Boolean, default=False)
    is_drop = Column(Boolean, default=False)
    season_note = Column(String(200))


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, nullable=False, index=True) # 1 to 9
    category_name = Column(String(100), nullable=False)
    category_kannada = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    title_kannada = Column(String(255))
    summary = Column(Text, nullable=False)
    summary_kannada = Column(Text)
    content = Column(Text)
    source = Column(String(100), default="Krishi Jagran / Dept of Agriculture Karnataka")
    read_time = Column(String(20), default="2 min read")
    published_date = Column(String(30), default=datetime.utcnow().strftime("%d %b %Y"))
    image_url = Column(String(255))
    key_takeaways = Column(Text) # JSON string array
    action_url = Column(String(255))
    voice_query_prompt = Column(String(255))


class DairyProcurementRate(Base):
    __tablename__ = "dairy_procurement_rates"

    id = Column(Integer, primary_key=True, index=True)
    dairy_name = Column(String(100), nullable=False)  # KMF Nandini, Amul, Dodla, Heritage, Tirumala
    brand_logo = Column(String(50))
    milk_type = Column(String(20), nullable=False)   # Cow or Buffalo
    slab_name = Column(String(50), default="Standard Slab") # Standard Slab / High-Fat Slab
    base_fat_pct = Column(Float, nullable=False)     # e.g., 3.5% Cow, 6.0% Buffalo
    base_snf_pct = Column(Float, nullable=False)     # e.g., 8.5% Cow, 9.0% Buffalo
    rate_per_litre = Column(Float, nullable=False)   # Base procurement rate in Rs
    fat_rate_factor = Column(Float, default=4.5)     # Rs per 1% fat change
    snf_rate_factor = Column(Float, default=3.2)     # Rs per 1% SNF change
    govt_incentive = Column(Float, default=0.0)      # e.g. Rs 5.0 for KMF Ksheera Dhare scheme
    notes = Column(String(255))


class LivestockBreed(Base):
    __tablename__ = "livestock_breeds"

    id = Column(Integer, primary_key=True, index=True)
    breed_name = Column(String(100), nullable=False)
    breed_kannada = Column(String(100))
    animal_type = Column(String(20), nullable=False) # Cow / Buffalo
    origin = Column(String(100))
    avg_yield_litres = Column(Float, nullable=False)
    peak_yield_litres = Column(Float)
    fat_pct = Column(Float)
    climate_zone = Column(String(100))
    min_temp_c = Column(Float, default=15.0)
    max_temp_c = Column(Float, default=38.0)
    heat_tolerance = Column(String(20)) # High, Moderate, Low
    drought_resistance = Column(String(20)) # High, Moderate, Low
    disease_resistance = Column(String(20))
    feeding_requirement = Column(String(50))
    description = Column(Text)


class FeedPlan(Base):
    __tablename__ = "feed_plans"

    id = Column(Integer, primary_key=True, index=True)
    animal_type = Column(String(20), nullable=False) # Cow / Buffalo
    stage = Column(String(50), nullable=False)       # Dry / Lactating
    plan_title = Column(String(100), nullable=False)
    plan_title_kannada = Column(String(100))
    body_weight_kg = Column(Integer, default=400)
    target_yield_litres = Column(Float, default=0.0)
    green_fodder_kg = Column(Float, nullable=False)  # Napier/Maize/Lucerne
    dry_fodder_kg = Column(Float, nullable=False)    # Paddy straw/Ragi straw
    concentrate_kg = Column(Float, nullable=False)   # Balanced cattle feed pellet/oil cake
    mineral_mixture_g = Column(Integer, default=50)  # grams
    bypass_fat_g = Column(Integer, default=0)        # grams
    salt_g = Column(Integer, default=30)             # grams
    water_litres = Column(Integer, default=60)
    schedule_tips = Column(Text)


class SireGuide(Base):
    __tablename__ = "sire_guides"

    id = Column(Integer, primary_key=True, index=True)
    dam_breed = Column(String(100), nullable=False)
    dam_breed_kannada = Column(String(100))
    recommended_sire = Column(String(100), nullable=False)
    recommended_sire_kannada = Column(String(100))
    purpose = Column(String(200), nullable=False)
    expected_gain = Column(String(200), nullable=False)
    inbreeding_caution = Column(String(255))
    veterinary_tip = Column(String(255))


class LivestockDisease(Base):
    __tablename__ = "livestock_diseases"

    id = Column(Integer, primary_key=True, index=True)
    symptom_key = Column(String(100), nullable=False, index=True)
    symptom_display = Column(String(150), nullable=False)
    symptom_kannada = Column(String(150))
    suspected_condition = Column(String(150), nullable=False)
    suspected_kannada = Column(String(150))
    urgency_level = Column(String(20), default="Medium") # Emergency, High, Medium, Low
    immediate_first_aid = Column(Text, nullable=False)
    avoid_doing = Column(Text)
    recommended_query = Column(String(255))


class DairyCache(Base):
    __tablename__ = "dairy_cache"

    cache_key = Column(String(150), primary_key=True, index=True)
    endpoint = Column(String(50), index=True)
    state = Column(String(60), index=True)
    language = Column(String(20), index=True)
    data_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


class VoiceQuery(Base):
    __tablename__ = "voice_queries"

    id = Column(Integer, primary_key=True, index=True)
    language = Column(String(20))
    query_text = Column(Text)
    response_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class ScanRecord(Base):
    __tablename__ = "scan_records"

    id = Column(Integer, primary_key=True, index=True)
    mode = Column(Integer)
    image_filename = Column(String(255))
    result_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# SPRINT 3: SCHEME NOTIFICATIONS & CHECKLIST PROGRESS
# ============================================================================

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False, index=True) 
    # 'training' (Fellowships & Training), 'subsidies' (Govt Subsidies),
    # 'insurance' (Crop Insurance & Premium Dues), 'relief' (Drought & Flood Relief)
    title = Column(String(200), nullable=False)
    title_kannada = Column(String(200))
    summary = Column(Text, nullable=False)
    summary_kannada = Column(Text)
    benefit_amount = Column(String(100), nullable=False)
    deadline_date = Column(String(50), nullable=False)  # ISO string or human date
    deadline_timestamp = Column(String(50))            # For countdown timer
    urgency = Column(String(20), default="High")       # Urgent, High, Medium, Info
    eligibility_rules = Column(Text)                   # JSON array of strings
    authority = Column(String(100))
    portal_url = Column(String(255))
    helpline = Column(String(50))
    checklist_template = Column(Text)                  # JSON array of checklist items
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class NotificationChecklistProgress(Base):
    __tablename__ = "notification_checklist_progress"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False, index=True)
    doc_key = Column(String(50), nullable=False)       # 'aadhaar', 'bhoomi_rtc', 'bank_passbook', 'sowing_cert'
    doc_name = Column(String(150), nullable=False)
    doc_name_kannada = Column(String(150))
    is_completed = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# SPRINT 3: WHOLE-YEAR FARM & HOUSEHOLD BALANCE SHEET (LEDGER)
# ============================================================================

class FarmLedgerEntry(Base):
    __tablename__ = "farm_ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    entry_date = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    crop_tag = Column(String(50), nullable=False, index=True)    # Paddy, Areca, Ginger, Corn, General/Household
    entry_type = Column(String(20), nullable=False, index=True)  # 'expense' or 'revenue'
    category = Column(String(50), nullable=False, index=True)
    # Categories:
    # 'cultivation' (seeds, fertilizers, pesticides, labor)
    # 'irrigation' (electricity/diesel, canal fees, pump maintenance)
    # 'harvest' (harvesting labor, threshing, transport, bagging)
    # 'household' (family living expenses or non-farm household income)
    # 'crop_sales' (sale of farm produce)
    sub_category = Column(String(100))
    description = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# SPRINT 3: ALTERNATIVE CROPS BENCHMARKS
# ============================================================================

class AlternativeCropBenchmark(Base):
    __tablename__ = "alternative_crop_benchmarks"

    id = Column(Integer, primary_key=True, index=True)
    crop_name = Column(String(100), nullable=False, unique=True)
    crop_kannada = Column(String(100))
    suitable_soil_types = Column(Text, nullable=False) # JSON array: ["Red Sandy Loam", "Black Cotton Soil", ...]
    min_temp_c = Column(Float, default=15.0)
    max_temp_c = Column(Float, default=38.0)
    water_demand_level = Column(String(20), default="Medium") # Low, Medium, High
    water_requirement_mm = Column(String(50))
    growth_duration_days = Column(Integer)
    avg_cost_per_acre = Column(Float, nullable=False)
    avg_yield_per_acre = Column(String(50), nullable=False)
    avg_gross_revenue_per_acre = Column(Float, nullable=False)
    avg_net_profit_per_acre = Column(Float, nullable=False)
    profit_ratio = Column(Float, nullable=False) # Net Profit / Cost
    roi_percent = Column(Float, nullable=False)  # (Net Profit / Cost) * 100
    risk_factor = Column(String(50), default="Low-Medium")
    advantages = Column(Text)


# ============================================================================
# SPRINT 5: HELP DIRECTORY, VET DOCTORS, CATTLE & LIVESTOCK/PET MARKETPLACE
# ============================================================================

class ServiceContact(Base):
    __tablename__ = "service_contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    phone = Column(String(50), nullable=False)
    location = Column(String(150), nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class VetDoctor(Base):
    __tablename__ = "vet_doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    doctor_type = Column(String(50), nullable=False, index=True)  # "Local Cow Doctor" or "Veterinary Doctor"
    specialization = Column(String(200))
    phone = Column(String(50), nullable=False)
    location = Column(String(150), nullable=False)
    availability = Column(String(150))
    emergency_available = Column(Boolean, default=False)


class CattleListing(Base):
    __tablename__ = "cattle_listings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    breed = Column(String(100), nullable=False, index=True)
    animal_type = Column(String(30), nullable=False, index=True)  # "Cow", "Buffalo", "Heifer", "Calf"
    price_inr = Column(Float, nullable=False)
    milk_yield_liters_per_day = Column(Float, default=0.0)
    age_years = Column(Float, default=0.0)
    location = Column(String(150), nullable=False)
    owner_name = Column(String(150), nullable=False)
    owner_phone = Column(String(50), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class LivestockPetListing(Base):
    __tablename__ = "livestock_pet_listings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False, index=True)  # "Poultry", "Goats & Sheep", "Pets", "Domestic Animals"
    breed_or_type = Column(String(100), nullable=False)
    quantity = Column(Integer, default=1)
    age = Column(String(50))
    price_inr = Column(Float, nullable=False)
    location = Column(String(150), nullable=False)
    owner_name = Column(String(150), nullable=False)
    owner_phone = Column(String(50), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# MONEY MANAGEMENT & FUTURE INVESTING (WEALTH PLANNER & LOAN TRACKER)
# ============================================================================

class UserLoan(Base):
    __tablename__ = "user_loans"

    id = Column(Integer, primary_key=True, index=True)
    pan_masked = Column(String(20), nullable=False, index=True)
    lender_name = Column(String(150), nullable=False)
    loan_type = Column(String(100), nullable=False)
    principal_amount = Column(Float, nullable=False)
    outstanding_balance = Column(Float, nullable=False)
    interest_rate_annual = Column(Float, nullable=False)
    emi_amount = Column(Float, default=0.0)
    next_due_date = Column(String(20), nullable=False)
    interest_accumulated = Column(Float, default=0.0)
    status = Column(String(20), default="active", nullable=False, index=True)  # "active" | "closed"
    created_at = Column(DateTime, default=datetime.utcnow)


class WealthPlanProfile(Base):
    __tablename__ = "wealth_plan_profiles"

    id = Column(Integer, primary_key=True, index=True)
    net_profit = Column(Float, nullable=False, default=0.0)
    household_reserve = Column(Float, nullable=False, default=0.0)
    next_cultivation_reserve = Column(Float, nullable=False, default=0.0)
    harvest_reserve = Column(Float, nullable=False, default=0.0)
    other_reserve = Column(Float, nullable=False, default=0.0)
    life_commitments = Column(JSON, nullable=False, default=list)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# LIVE LOCATION MEMORY (WHATSAPP + WEB API)
# ============================================================================

class UserLocation(Base):
    __tablename__ = "user_locations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, unique=True, index=True)
    phone_number = Column(String(50), nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    district = Column(String(120), nullable=True)
    state = Column(String(120), nullable=True)
    location_name = Column(String(255), nullable=True)
    language_code = Column(String(20), nullable=True)
    awaiting_language_choice = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WhatsAppUserState(Base):
    __tablename__ = "whatsapp_user_states"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(50), nullable=False, unique=True, index=True)
    preferred_language = Column(String(20), default="kn-IN")
    awaiting_location = Column(Boolean, default=False)
    pending_question = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
