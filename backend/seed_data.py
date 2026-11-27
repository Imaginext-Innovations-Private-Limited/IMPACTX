"""
Seed comprehensive realistic Karnataka data for Farm Advisor Sprint 1 & Sprint 2 (Parts A & B).
Covers:
- APMC Commodities & 14-Day Price History
- Regional Cross-Mandi APMC Rates
- 6-Year Monthly Historical Prices (2021–2026) with Seasonal Peaks & Drops
- 9 Curated Agricultural News Topics with Subsidy & Price Figures + Voice Assistant Queries
- Company Dairy Milk Procurement Board (KMF Nandini, Amul, Dodla, Heritage, Tirumala)
- Weather-Matched High-Yield Cattle & Buffalo Breeds (including Malnad Gidda)
- Targeted Feed & Nutrition Plans (Dry vs Lactating)
- Sire Semen Matching Guide
- Livestock Disease & Behavior Variation Advisor
"""
import sys
import os
import random
import json
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(__file__))

from database import engine, SessionLocal
import models

models.Base.metadata.create_all(bind=engine)

KARNATAKA_COMMODITIES = [
    {
        "name": "Paddy (Fine)",
        "name_kannada": "ಭತ್ತ (ಉತ್ತಮ - ಸೋನಾ ಮಸೂರಿ)",
        "name_hindi": "धान (बारीक)",
        "category": "grain",
        "unit": "quintal",
        "current_price": 2250.0,
        "previous_price": 2180.0,
        "min_price": 2100.0,
        "max_price": 2400.0,
        "market": "APMC Mangalore",
    },
    {
        "name": "Areca Nut (Chali)",
        "name_kannada": "ಅಡಿಕೆ (ಚಾಲಿ)",
        "name_hindi": "ಸುಪಾರಿ (ಚಾಲಿ)",
        "category": "plantation",
        "unit": "quintal",
        "current_price": 44500.0,
        "previous_price": 43200.0,
        "min_price": 42000.0,
        "max_price": 46000.0,
        "market": "APMC Shimoga",
    },
    {
        "name": "Ginger (Fresh)",
        "name_kannada": "ಶುಂಠಿ (ತಾಜಾ ಹಸಿ)",
        "name_hindi": "अदरक (ताजा)",
        "category": "spice",
        "unit": "quintal",
        "current_price": 3200.0,
        "previous_price": 2950.0,
        "min_price": 2800.0,
        "max_price": 3500.0,
        "market": "APMC Sirsi",
    },
    {
        "name": "Corn / Maize",
        "name_kannada": "ಮೆಕ್ಕೆ ಜೋಳ",
        "name_hindi": "मक्का",
        "category": "grain",
        "unit": "quintal",
        "current_price": 1850.0,
        "previous_price": 1780.0,
        "min_price": 1700.0,
        "max_price": 1950.0,
        "market": "APMC Davangere",
    },
    {
        "name": "Black Pepper",
        "name_kannada": "ಕಾಳು ಮೆಣಸು",
        "name_hindi": "काली मिर्च",
        "category": "spice",
        "unit": "quintal",
        "current_price": 52000.0,
        "previous_price": 54000.0,
        "min_price": 50000.0,
        "max_price": 55000.0,
        "market": "APMC Mangalore",
    },
    {
        "name": "Coconut (Copra)",
        "name_kannada": "ತೆಂಗಿನ ಕಾಯಿ (ಕೊಬ್ಬರಿ)",
        "name_hindi": "ನಾರಿಯಲ್ (ಖೋಪರಾ)",
        "category": "plantation",
        "unit": "quintal",
        "current_price": 11500.0,
        "previous_price": 11200.0,
        "min_price": 10800.0,
        "max_price": 12000.0,
        "market": "APMC Tumkur",
    },
    {
        "name": "Paddy (Coarse)",
        "name_kannada": "ಭತ್ತ (ದಪ್ಪ)",
        "name_hindi": "धान (मोटा)",
        "category": "grain",
        "unit": "quintal",
        "current_price": 1980.0,
        "previous_price": 2010.0,
        "min_price": 1900.0,
        "max_price": 2050.0,
        "market": "APMC Hassan",
    },
    {
        "name": "Areca Nut (Red)",
        "name_kannada": "ಅಡಿಕೆ (ಕೆಂಪು/ಬೆಟ್ಟೆ)",
        "name_hindi": "सुपारी (लाल)",
        "category": "plantation",
        "unit": "quintal",
        "current_price": 38000.0,
        "previous_price": 39500.0,
        "min_price": 37000.0,
        "max_price": 40000.0,
        "market": "APMC Sagara",
    },
    {
        "name": "Tomato",
        "name_kannada": "ಟೊಮ್ಯಾಟೋ",
        "name_hindi": "टमाटर",
        "category": "vegetable",
        "unit": "quintal",
        "current_price": 1200.0,
        "previous_price": 1500.0,
        "min_price": 800.0,
        "max_price": 2000.0,
        "market": "APMC Kolar",
    },
]


def seed_commodities(db):
    if db.query(models.Commodity).count() == 0:
        for c_data in KARNATAKA_COMMODITIES:
            db.add(models.Commodity(**c_data))
        db.commit()


def seed_cross_mandi_prices(db):
    if db.query(models.MandiPrice).count() > 0:
        return

    mandi_dataset = [
        # Paddy (Fine)
        {"c": "Paddy (Fine)", "m": "APMC Mangalore", "d": "Dakshina Kannada", "min": 2150, "max": 2380, "mod": 2250, "arr": 45.2},
        {"c": "Paddy (Fine)", "m": "APMC Hassan", "d": "Hassan", "min": 2120, "max": 2310, "mod": 2220, "arr": 85.0},
        {"c": "Paddy (Fine)", "m": "APMC Davangere", "d": "Davanagere", "min": 2180, "max": 2420, "mod": 2300, "arr": 120.5},
        {"c": "Paddy (Fine)", "m": "APMC Raichur", "d": "Raichur", "min": 2200, "max": 2460, "mod": 2350, "arr": 240.0},
        {"c": "Paddy (Fine)", "m": "APMC Shimoga", "d": "Shivamogga", "min": 2140, "max": 2350, "mod": 2260, "arr": 78.4},
        {"c": "Paddy (Fine)", "m": "APMC Mysuru", "d": "Mysuru", "min": 2100, "max": 2300, "mod": 2210, "arr": 62.0},

        # Areca Nut (Chali)
        {"c": "Areca Nut (Chali)", "m": "APMC Shimoga", "d": "Shivamogga", "min": 43000, "max": 45800, "mod": 44500, "arr": 95.0},
        {"c": "Areca Nut (Chali)", "m": "APMC Sagara", "d": "Shivamogga", "min": 42500, "max": 45200, "mod": 44100, "arr": 60.5},
        {"c": "Areca Nut (Chali)", "m": "APMC Sirsi", "d": "Uttara Kannada", "min": 43500, "max": 46500, "mod": 45200, "arr": 110.0},
        {"c": "Areca Nut (Chali)", "m": "APMC Channagiri", "d": "Davanagere", "min": 43800, "max": 46900, "mod": 45600, "arr": 88.0},
        {"c": "Areca Nut (Chali)", "m": "APMC Mangalore", "d": "Dakshina Kannada", "min": 42000, "max": 44500, "mod": 43800, "arr": 42.0},
        {"c": "Areca Nut (Chali)", "m": "APMC Yellapur", "d": "Uttara Kannada", "min": 43200, "max": 46000, "mod": 44800, "arr": 35.0},

        # Ginger (Fresh)
        {"c": "Ginger (Fresh)", "m": "APMC Sirsi", "d": "Uttara Kannada", "min": 2900, "max": 3450, "mod": 3200, "arr": 30.0},
        {"c": "Ginger (Fresh)", "m": "APMC Hassan", "d": "Hassan", "min": 3100, "max": 3650, "mod": 3450, "arr": 75.0},
        {"c": "Ginger (Fresh)", "m": "APMC Shimoga", "d": "Shivamogga", "min": 3000, "max": 3500, "mod": 3300, "arr": 50.0},
        {"c": "Ginger (Fresh)", "m": "APMC Bangalore", "d": "Bengaluru", "min": 3300, "max": 3900, "mod": 3650, "arr": 90.0},
        {"c": "Ginger (Fresh)", "m": "APMC Mysore", "d": "Mysuru", "min": 3050, "max": 3600, "mod": 3350, "arr": 42.0},

        # Corn / Maize
        {"c": "Corn / Maize", "m": "APMC Davangere", "d": "Davanagere", "min": 1720, "max": 1920, "mod": 1850, "arr": 350.0},
        {"c": "Corn / Maize", "m": "APMC Ranebennur", "d": "Haveri", "min": 1750, "max": 1960, "mod": 1890, "arr": 280.0},
        {"c": "Corn / Maize", "m": "APMC Bellary", "d": "Ballari", "min": 1700, "max": 1880, "mod": 1820, "arr": 210.0},
        {"c": "Corn / Maize", "m": "APMC Haveri", "d": "Haveri", "min": 1740, "max": 1940, "mod": 1870, "arr": 190.0},
        {"c": "Corn / Maize", "m": "APMC Bagalkot", "d": "Bagalkote", "min": 1680, "max": 1860, "mod": 1800, "arr": 140.0},

        # Black Pepper
        {"c": "Black Pepper", "m": "APMC Mangalore", "d": "Dakshina Kannada", "min": 50500, "max": 54000, "mod": 52000, "arr": 18.0},
        {"c": "Black Pepper", "m": "APMC Sirsi", "d": "Uttara Kannada", "min": 51500, "max": 55000, "mod": 53200, "arr": 25.0},
        {"c": "Black Pepper", "m": "APMC Sakleshpur", "d": "Hassan", "min": 51000, "max": 54500, "mod": 52800, "arr": 15.0},
        {"c": "Black Pepper", "m": "APMC Madikeri", "d": "Kodagu", "min": 52000, "max": 55800, "mod": 53900, "arr": 32.0},
        {"c": "Black Pepper", "m": "APMC Shimoga", "d": "Shivamogga", "min": 50000, "max": 53500, "mod": 51700, "arr": 12.0},

        # Coconut (Copra)
        {"c": "Coconut (Copra)", "m": "APMC Tumkur", "d": "Tumakuru", "min": 10900, "max": 12100, "mod": 11500, "arr": 85.0},
        {"c": "Coconut (Copra)", "m": "APMC Tiptur", "d": "Tumakuru", "min": 11200, "max": 12600, "mod": 11950, "arr": 145.0},
        {"c": "Coconut (Copra)", "m": "APMC Arsikere", "d": "Hassan", "min": 11000, "max": 12300, "mod": 11700, "arr": 95.0},
        {"c": "Coconut (Copra)", "m": "APMC Hassan", "d": "Hassan", "min": 10800, "max": 11900, "mod": 11400, "arr": 60.0},
        {"c": "Coconut (Copra)", "m": "APMC Mandya", "d": "Mandya", "min": 10700, "max": 11800, "mod": 11300, "arr": 40.0},
    ]

    for item in mandi_dataset:
        db.add(models.MandiPrice(
            commodity_name=item["c"],
            market_name=item["m"],
            district=item["d"],
            min_price=item["min"],
            max_price=item["max"],
            modal_price=item["mod"],
            arrivals_tonnes=item["arr"],
        ))
    db.commit()


def seed_two_week_history(db):
    if db.query(models.TwoWeekHistory).count() > 0:
        return

    today = datetime.now()
    targets = [
        {"name": "Paddy (Fine)", "base": 2250.0, "var": 30.0},
        {"name": "Areca Nut (Chali)", "base": 44500.0, "var": 400.0},
        {"name": "Ginger (Fresh)", "base": 3200.0, "var": 80.0},
        {"name": "Corn / Maize", "base": 1850.0, "var": 25.0},
        {"name": "Black Pepper", "base": 52000.0, "var": 500.0},
        {"name": "Coconut (Copra)", "base": 11500.0, "var": 120.0},
    ]

    for t in targets:
        cur = t["base"]
        for offset in range(14): # 0 is today, 13 is 13 days ago
            dt = today - timedelta(days=offset)
            factor = 1.0 - (offset * 0.003) + (random.uniform(-0.01, 0.01))
            modal = round(cur * factor, 1)
            min_p = round(modal - t["var"], 1)
            max_p = round(modal + t["var"] * 1.2, 1)
            db.add(models.TwoWeekHistory(
                commodity_name=t["name"],
                day_offset=offset,
                date_str=dt.strftime("%d %b"),
                min_price=min_p,
                max_price=max_p,
                modal_price=modal,
            ))
    db.commit()


def seed_seasonal_prices(db):
    if db.query(models.SeasonalHistoricalPrice).count() > 0:
        return

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    patterns = {
        "Areca Nut (Chali)": {
            "base_2021": 39000, "annual_growth": 1100,
            "multipliers": [0.93, 0.95, 0.98, 1.03, 1.08, 1.09, 1.07, 1.02, 0.99, 0.97, 0.94, 0.92],
            "peak_months": [5, 6, 7], "drop_months": [1, 11, 12],
            "peak_note": "Pre-monsoon inventory build-up by processing industries",
            "drop_note": "Heavy arrivals of freshly cured Chali from Malnad and coastal farms",
        },
        "Paddy (Fine)": {
            "base_2021": 1880, "annual_growth": 75,
            "multipliers": [0.92, 0.94, 0.97, 1.01, 1.04, 1.07, 1.08, 1.06, 1.02, 0.98, 0.93, 0.91],
            "peak_months": [6, 7, 8], "drop_months": [1, 11, 12],
            "peak_note": "Lean market arrival period; institutional rice millers compete for stock",
            "drop_note": "Kharif bumper crop arrival causing mandi yard gluts",
        },
        "Ginger (Fresh)": {
            "base_2021": 2400, "annual_growth": 160,
            "multipliers": [0.90, 0.95, 1.08, 1.15, 1.12, 1.04, 0.99, 0.96, 0.94, 0.92, 0.88, 0.87],
            "peak_months": [3, 4, 5], "drop_months": [10, 11, 12],
            "peak_note": "Seed ginger planting demand + high export demand for dry ginger",
            "drop_note": "Fresh rhizome harvest in Shivamogga, Hassan, and Kodagu",
        },
        "Corn / Maize": {
            "base_2021": 1450, "annual_growth": 80,
            "multipliers": [0.91, 0.93, 0.96, 1.00, 1.03, 1.07, 1.09, 1.08, 1.04, 0.97, 0.92, 0.90],
            "peak_months": [6, 7, 8], "drop_months": [1, 11, 12],
            "peak_note": "Peak feed mill requirement from Namakkal and Karnataka poultry belts",
            "drop_note": "Fresh grain arrivals with higher moisture percentage",
        },
        "Black Pepper": {
            "base_2021": 42000, "annual_growth": 2000,
            "multipliers": [0.96, 0.92, 0.91, 0.95, 0.99, 1.02, 1.04, 1.06, 1.09, 1.10, 1.07, 0.98],
            "peak_months": [9, 10, 11], "drop_months": [2, 3],
            "peak_note": "Global export contracts and festive season spice blending",
            "drop_note": "Peak pepper berry plucking season in Kodagu and Chikmagalur",
        },
        "Coconut (Copra)": {
            "base_2021": 9200, "annual_growth": 450,
            "multipliers": [0.96, 0.99, 1.06, 1.10, 1.08, 1.03, 0.99, 0.97, 0.93, 0.92, 0.93, 0.95],
            "peak_months": [3, 4, 5], "drop_months": [9, 10],
            "peak_note": "Summer season oil extraction & confectionery demand",
            "drop_note": "Post-monsoon flush harvest from southern Karnataka plantations",
        },
    }

    years = [2021, 2022, 2023, 2024, 2025, 2026]

    for comm_name, cfg in patterns.items():
        for y_idx, y in enumerate(years):
            annual_base = cfg["base_2021"] + (y_idx * cfg["annual_growth"])
            max_m = 11 if y == 2026 else 12

            for m in range(1, max_m + 1):
                mult = cfg["multipliers"][m - 1]
                price = round(annual_base * mult, 0)
                is_pk = (m in cfg["peak_months"])
                is_dp = (m in cfg["drop_months"])
                note = cfg["peak_note"] if is_pk else (cfg["drop_note"] if is_dp else "Steady inter-seasonal trading")

                db.add(models.SeasonalHistoricalPrice(
                    commodity_name=comm_name,
                    year=y,
                    month=m,
                    month_name=month_names[m - 1],
                    avg_price=price,
                    is_peak=is_pk,
                    is_drop=is_dp,
                    season_note=note,
                ))
    db.commit()


def seed_news_articles(db):
    # Always refresh to ensure exact 9 categories and rich figures
    db.query(models.NewsArticle).delete()

    articles = [
        # 1. Commodity Rates & Market Trends
        {
            "category_id": 1,
            "category_name": "Commodity Rates & Market Trends",
            "category_kannada": "ಕೃಷಿ ದರ ಮತ್ತು ಮಾರುಕಟ್ಟೆ ಪ್ರವೃತ್ತಿಗಳು",
            "title": "Areca Nut Prices Cross ₹45,200/q in Shimoga & Sirsi APMC as Export Demand Surges",
            "title_kannada": "ಶಿವಮೊಗ್ಗ ಹಾಗೂ ಶಿರಸಿ ಎಪಿಎಂಸಿಯಲ್ಲಿ ಅಡಿಕೆ ಚಾಲಿ ಬೆಲೆ ₹45,200 ಗಡಿ ದಾಟಿದೆ — ರಫ್ತು ಬೇಡಿಕೆ ಹೆಚ್ಚಳ",
            "summary": "High-grade Chali arecanut crossed ₹45,200 per quintal in Shivamogga, Sagara, and Sirsi mandis due to strong post-festival demand and low arrival volume from coastal areas.",
            "summary_kannada": "ದೀಪಾವಳಿ ನಂತರದ ಹೆಚ್ಚಿನ ಬೇಡಿಕೆ ಮತ್ತು ಕರಾವಳಿಯಿಂದ ಕಡಿಮೆ ಸರಕು ಆಗಮನದಿಂದಾಗಿ ಅಡಿಕೆ ಬೆಲೆ ಗಣನೀಯ ಏರಿಕೆ ಕಂಡಿದೆ.",
            "content": "Trade analysts project steady prices through January 2027. Farmers are advised to dry their produce to <11% moisture to prevent fungal spots and maximize grading scores at APMC auctions.",
            "source": "Agmarknet Karnataka & CAMPCO Report",
            "read_time": "3 min read",
            "published_date": "24 Nov 2026",
            "key_takeaways": json.dumps([
                "Chali modal price touched ₹45,200/q at Sirsi APMC (up by ₹2,000/q)",
                "Red/Bette areca holding firm at ₹38,000–₹39,500/q",
                "Moisture control (<11%) crucial for achieving Grade-A pricing",
            ]),
            "voice_query_prompt": "ಇಂದು ಕರ್ನಾಟಕದಲ್ಲಿ ಅಡಿಕೆ ಮತ್ತು ಕಾಳುಮೆಣಸಿನ ಮಾರುಕಟ್ಟೆ ದರ ಹೇಗಿದೆ?",
        },
        # 2. Agricultural Tools Available in Govt Subsidies
        {
            "category_id": 2,
            "category_name": "Agricultural Tools Available in Govt Subsidies",
            "category_kannada": "ಸರ್ಕಾರದ ಸಬ್ಸಿಡಿ ಕೃಷಿ ಯಂತ್ರೋಪಕರಣಗಳು",
            "title": "Karnataka Krishi Yanthradhare: 50% to 90% Subsidy on Power Weeders, Tillers & Mini Tractors",
            "title_kannada": "ಕೃಷಿ ಯಂತ್ರಧಾರೆ: ಪವರ್ ವೀಡರ್ ಮತ್ತು ಮಿನಿ ಟ್ರ್ಯಾಕ್ಟರ್‌ಗಳಿಗೆ 50% ರಿಂದ 90% ಸಬ್ಸಿಡಿ ಅರ್ಜಿ ಆಹ್ವಾನ",
            "summary": "State Agriculture Department opens registrations on the K-Kisan portal for farm mechanization machinery with up to 50% subsidy for General category and 90% for SC/ST farmers.",
            "summary_kannada": "ರೈತರಿಗೆ ಕೃಷಿ ಯಂತ್ರೋಪಕರಣಗಳ ಮೇಲೆ ಸಬ್ಸಿಡಿ ನೀಡಲು ಕೆ-ಕಿಸಾನ್ ಪೋರ್ಟಲ್‌ನಲ್ಲಿ ಅರ್ಜಿ ಸ್ವೀಕಾರ ಆರಂಭವಾಗಿದೆ.",
            "content": "Eligible implements include brush cutters (₹18,000 subsidy), power rotary tillers (₹45,000 subsidy), paddy transplanters, and 4WD mini tractors (up to ₹1,50,000 subsidy). Apply online with RTC (Pahani) and Aadhaar card through nearest Raitha Samparka Kendra.",
            "source": "Dept of Agriculture, Govt of Karnataka",
            "read_time": "4 min read",
            "published_date": "23 Nov 2026",
            "key_takeaways": json.dumps([
                "50% subsidy for general farmers; 90% subsidy for SC/ST beneficiaries",
                "Power weeders available at subsidized rate of ₹14,000 (MRP ₹32,000)",
                "Apply via Raitha Samparka Kendra / Seva Sindhu with Pahani (RTC)",
            ]),
            "voice_query_prompt": "ಕೃಷಿ ಯಂತ್ರಧಾರೆ ಯೋಜನೆಯಡಿ ಪವರ್ ವೀಡರ್ ಮತ್ತು ಟ್ರ್ಯಾಕ್ಟರ್ ಸಬ್ಸಿಡಿ ಪಡೆಯುವುದು ಹೇಗೆ?",
        },
        # 3. Upcoming Weather & Monsoon Alerts
        {
            "category_id": 3,
            "category_name": "Upcoming Weather & Monsoon Alerts",
            "category_kannada": "ಹವಾಮಾನ ಮತ್ತು ಮುಂಗಾರು ಮುನ್ಸೂಚನೆ",
            "title": "IMD Weather Watch: Northeast Monsoon Trough to Bring Scattered Showers in South Interior Karnataka",
            "title_kannada": "ದಕ್ಷಿಣ ಒಳನಾಡಿನಲ್ಲಿ ಮುಂದಿನ 3 ದಿನ ಸಾಧಾರಣ ಮಳೆ ಸಾಧ್ಯತೆ — ಹವಾಮಾನ ಇಲಾಖೆ ಮುನ್ಸೂಚನೆ",
            "summary": "Bengaluru Rural, Mysuru, Hassan, and Mandya may experience localized thunder-showers over the weekend. Farmers are advised to complete paddy harvesting before Friday evening.",
            "summary_kannada": "ಹಾಸನ, ಮೈಸೂರು ಮತ್ತು ಮಂಡ್ಯ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಹಗುರದಿಂದ ಸಾಧಾರಣ ಮಳೆಯಾಗುವ ಸಾಧ್ಯತೆ.",
            "content": "North Interior Karnataka (Belagavi, Bagalkote, Vijayapura) will remain dry with dropping night temperatures (15°C–17°C) favorable for Bengal gram and sunflower germination. Avoid open-field threshing in coastal and southern blocks.",
            "source": "IMD Bengaluru & KSNDMC",
            "read_time": "2 min read",
            "published_date": "25 Nov 2026",
            "key_takeaways": json.dumps([
                "Scattered evening showers (15–25mm) in South Interior districts",
                "Dry sunny days ideal for drying harvested grains in North Karnataka",
                "Night temperature dipping to 16°C in Malnad belts",
            ]),
            "voice_query_prompt": "ಮುಂದಿನ 5 ದಿನ ನಮ್ಮ ಜಿಲ್ಲೆಯಲ್ಲಿ ಮಳೆ ಬೀಳುವ ಸಾಧ್ಯತೆ ಇದೆಯೇ?",
        },
        # 4. Price Decreases in Agri Tools & Vehicles
        {
            "category_id": 4,
            "category_name": "Price Decreases in Agri Tools & Vehicles",
            "category_kannada": "ಕೃಷಿ ಸಲಕರಣೆಗಳ ದರ ಇಳಿಕೆ ಮತ್ತು ಕೊಡುಗೆಗಳು",
            "title": "Major Tractor Manufacturers Announce Year-End Price Cuts Up to ₹45,000 and 0% Processing Loans",
            "title_kannada": "ವರ್ಷಾಂತ್ಯದ ಕೊಡುಗೆ: ಟ್ರ್ಯಾಕ್ಟರ್ ಬೆಲೆ ₹45,000 ದರ ಕಡಿತ ಮತ್ತು ಶೂನ್ಯ ಬಡ್ಡಿ ಸಾಲ ಸೌಲಭ್ಯ",
            "summary": "Leading farm vehicle manufacturers announce seasonal discounts up to ₹45,000 on 35HP to 50HP tractors along with extended 6-year engine warranty for Karnataka farmers.",
            "summary_kannada": "ಕೃಷಿ ಟ್ರ್ಯಾಕ್ಟರ್‌ಗಳ ಮೇಲೆ ವರ್ಷಾಂತ್ಯದ ವಿಶೇಷ ರಿಯಾಯಿತಿ ಮತ್ತು ಸುಲಭ ಕಂತಿನ ಸಾಲ ಲಭ್ಯ.",
            "content": "Competitive pricing in battery-operated knapsack sprayers was also noted, with prices dropping below ₹2,200 for 16-liter lithium-ion dual-motor models at local agro-dealers across Hubballi, Davangere, and Shivamogga.",
            "source": "Agri Machinery Business Standard",
            "read_time": "3 min read",
            "published_date": "22 Nov 2026",
            "key_takeaways": json.dumps([
                "Year-end cash discount: ₹45,000 on 45HP tractors",
                "16-liter lithium battery sprayers slashed to ₹2,200 (earlier ₹3,400)",
                "Zero down payment finance available through SBI Agri Branch",
            ]),
            "voice_query_prompt": "ಕಡಿಮೆ ದರದಲ್ಲಿ ಬ್ಯಾಟರಿ ಸ್ಪ್ರೇಯರ್ ಮತ್ತು ಮಿನಿ ಟ್ರ್ಯಾಕ್ಟರ್ ಎಲ್ಲಿ ಸಿಗುತ್ತದೆ?",
        },
        # 5. Government Support Schemes for Farmers
        {
            "category_id": 5,
            "category_name": "Government Support Schemes for Farmers",
            "category_kannada": "ರೈತ ಬೆಂಬಲ ಮತ್ತು ಕಲ್ಯಾಣ ಯೋಜನೆಗಳು",
            "title": "Ksheera Dhare Direct Subsidy Released: ₹5/Litre Deposited Directly to 9.2 Lakh KMF Milk Producers",
            "title_kannada": "ಕ್ಷೀರಧಾರೆ ಯೋಜನೆ: 9.2 ಲಕ್ಷ ಹಾಲು ಉತ್ಪಾದಕರಿಗೆ ಪ್ರತಿ ಲೀಟರ್‌ಗೆ ₹5 ಪ್ರೋತ್ಸಾಹಧನ ನೇರ ಖಾತೆಗೆ ಜಮೆ",
            "summary": "Animal Husbandry Department disburses ₹460 Crore pending Ksheera Dhare subsidy directly into Aadhaar-linked DBT bank accounts of milk producers supplying to KMF Nandini dairy unions.",
            "summary_kannada": "ಕೆಎಂಎಫ್ ನಂದಿನಿ ಹಾಲು ಉತ್ಪಾದಕರ ಖಾತೆಗೆ ನೇರವಾಗಿ ಡಿಬಿಟಿ ಮೂಲಕ ₹5 ಪ್ರತಿ ಲೀಟರ್ ಪ್ರೋತ್ಸಾಹಧನ ಜಮೆಯಾಗಿದೆ.",
            "content": "Beneficiaries can verify payment status through the FRUITS portal (fruits.karnataka.gov.in) using their Farmer FID number or visit their local Milk Producers' Co-operative Society (MPCS).",
            "source": "Dept of Animal Husbandry, Karnataka",
            "read_time": "3 min read",
            "published_date": "21 Nov 2026",
            "key_takeaways": json.dumps([
                "₹5 per liter direct benefit transfer to dairy farmers supplying to KMF",
                "Linked to FRUITS FID number and Aadhaar bank account",
                "Total direct disbursement exceeds ₹460 Crores across 14 milk unions",
            ]),
            "voice_query_prompt": "ಕ್ಷೀರಧಾರೆ ಯೋಜನೆಯ ₹5 ಪ್ರೋತ್ಸಾಹಧನ ನನ್ನ ಬ್ಯಾಂಕ್ ಖಾತೆಗೆ ಜಮೆಯಾಗಿದೆಯೇ ಎಂದು ಹೇಗೆ ನೋಡಬೇಕು?",
        },
        # 6. Crop Insurance Schemes
        {
            "category_id": 6,
            "category_name": "Crop Insurance Schemes",
            "category_kannada": "ಬೆಳೆ ವಿಮೆ ಯೋಜನೆಗಳು (PMFBY)",
            "title": "PMFBY Rabi 2026-27 Enrollment Deadline Set for December 15 in Karnataka: Just 1.5% Premium",
            "title_kannada": "ಪ್ರಧಾನ ಮಂತ್ರಿ ಫಸಲ್ ಬಿಮಾ ಯೋಜನೆ: ಹಿಂಗಾರು ಬೆಳೆ ವಿಮೆ ನೋಂದಣಿಗೆ ಡಿಸೆಂಬರ್ 15 ಕೊನೆಯ ದಿನ",
            "summary": "Farmers cultivating Bengal gram, Jowar, Wheat, and Sunflower for Rabi season must enroll before December 15, 2026, paying just 1.5% premium (₹450/acre) for full risk insurance coverage.",
            "summary_kannada": "ಹಿಂಗಾರು ಹಂಗಾಮಿನ ಕಡಲೆ, ಜೋಳ, ಗೋಧಿ ಮತ್ತು ಸೂರ್ಯಕಾಂತಿ ಬೆಳೆಗಳಿಗೆ ಕೇವಲ 1.5% ಪ್ರೀಮಿಯಂ ದರದಲ್ಲಿ ವಿಮೆ ಲಭ್ಯ.",
            "content": "Both loanee and non-loanee farmers are eligible. Enrolment can be completed at BangaloreOne, GramaOne centers, or National Crop Insurance Portal (pmfby.gov.in) with RTC copy and bank passbook.",
            "source": "Samrakshane Portal & Ministry of Agriculture",
            "read_time": "3 min read",
            "published_date": "20 Nov 2026",
            "key_takeaways": json.dumps([
                "Rabi deadline: December 15, 2026 across all Karnataka districts",
                "Farmer premium: only 1.5% of sum insured (Govt pays the balance 14%)",
                "Enroll via GramaOne, CSC centers, or Samrakshane portal with RTC",
            ]),
            "voice_query_prompt": "ಫಸಲ್ ಬಿಮಾ ಯೋಜನೆಯಲ್ಲಿ ಹಿಂಗಾರು ಬೆಳೆ ವಿಮೆ ಮಾಡಿಸುವುದು ಹೇಗೆ?",
        },
        # 7. Budget-Friendly Pumpsets
        {
            "category_id": 7,
            "category_name": "Budget-Friendly Pumpsets",
            "category_kannada": "ಕಡಿಮೆ ವೆಚ್ಚದ ನೀರಾವರಿ ಪಂಪ್‌ಸೆಟ್‌ಗಳು",
            "title": "BEE 5-Star Submersible Pumpsets Reduce Power Consumption by 30% in Borewell Farms (Starting ₹18,500)",
            "title_kannada": "5-ಸ್ಟಾರ್ ಸಬ್‌ಮರ್ಸಿಬಲ್ ಪಂಪ್‌ಸೆಟ್‌ಗಳು: ₹18,500 ರಿಂದ ಪ್ರಾರಂಭ — 30% ರಷ್ಟು ವಿದ್ಯುತ್ ಉಳಿತಾಯ",
            "summary": "University of Agricultural Sciences (UAS) Dharwad testing reveals energy-efficient 5-star pumpsets maintain strong water discharge even during low voltage dips in rural feeders.",
            "summary_kannada": "ಕಡಿಮೆ ವೋಲ್ಟೇಜ್‌ನಲ್ಲೂ ಸಮರ್ಪಕ ನೀರು ಎತ್ತುವ ಸಾಮರ್ಥ್ಯ ಹೊಂದಿರುವ 5-ಸ್ಟಾರ್ ಪಂಪ್‌ಸೆಟ್‌ಗಳ ಪರೀಕ್ಷಾ ವರದಿ.",
            "content": "With prices starting at ₹18,500 for 5HP stainless steel impeller units, payback period is estimated at under 14 months due to lower motor burnout, fewer capacitor replacements, and reliable single-phase starter compatibility.",
            "source": "UAS Dharwad Farm Machinery Dept",
            "read_time": "2 min read",
            "published_date": "19 Nov 2026",
            "key_takeaways": json.dumps([
                "30% lower kilowatt-hour power draw during irrigation hours",
                "Stainless steel impellers resist sandy borewell silt erosion",
                "5HP units start at ₹18,500 with 2-year free service warranty",
            ]),
            "voice_query_prompt": "ಬೋರ್‌ವೆಲ್‌ಗೆ ಕಡಿಮೆ ವಿದ್ಯುತ್ ಬಳಸುವ 5-ಸ್ಟಾರ್ ಪಂಪ್‌ಸೆಟ್ ಯಾವುದು ಉತ್ತಮ?",
        },
        # 8. Quality Reviews of Agri Products (Seeds, Fertilizers, Equipment)
        {
            "category_id": 8,
            "category_name": "Quality Reviews of Agri Products (Seeds, Fertilizers, Equipment)",
            "category_kannada": "ಕೃಷಿ ಉತ್ಪನ್ನಗಳ ಗುಣಮಟ್ಟ ವಿಮರ್ಶೆ (ಬೀಜ/ಗೊಬ್ಬರ/ಉಪಕರಣ)",
            "title": "Field Test Report: CoFS-29 Multi-Cut Fodder Grass Yields 120 Tons/Acre/Year for Karnataka Dairy Farms",
            "title_kannada": "ಹೈನುಗಾರಿಕೆಗೆ CoFS-29 ಬಹುವಾರ್ಷಿಕ ಹಸಿರು ಮೇವು: ವರ್ಷಕ್ಕೆ 120 ಟನ್ ಇಳುವರಿ ಮತ್ತು ಹಾಲಿನ ಗುಣಮಟ್ಟ ವೃದ್ಧಿ",
            "summary": "Karnataka Milk Federation trials across 200 dairy farms validate CoFS-29 sorghum-sudan cross grass for high crude protein (11.5%) and exceptional digestibility in crossbred cows.",
            "summary_kannada": "ಹಸುಗಳಲ್ಲಿ ಹಾಲು ಮತ್ತು ಬೆಣ್ಣೆ ಅಂಶ ಹೆಚ್ಚಿಸಲು ಹೆಚ್ಚು ಪ್ರೋಟೀನ್ ಹೊಂದಿರುವ ಗುಣಮಟ್ಟದ ಹಸಿರು ಹುಲ್ಲು CoFS-29.",
            "content": "Requires just one sowing and yields 6 to 8 cuttings per year for 3 consecutive years. Drought-tolerant once established and significantly lowers commercial cattle feed expenditure by ₹35 per cow per day.",
            "source": "NDRI Southern Regional Station Bengaluru",
            "read_time": "3 min read",
            "published_date": "18 Nov 2026",
            "key_takeaways": json.dumps([
                "11.5% crude protein content boosts milk SNF from 8.3% to 8.7%",
                "6 to 8 cuttings per year with low water requirement",
                "Certified seeds available at Veterinary Hospitals & KVKs at ₹180/kg",
            ]),
            "voice_query_prompt": "ಹಸುಗಳಲ್ಲಿ ಹಾಲು ಮತ್ತು ಫ್ಯಾಟ್ ಹೆಚ್ಚಿಸಲು ಯಾವ ಹಸಿರು ಮೇವು ಬೆಳೆಸಬೇಕು?",
        },
        # 9. Solar Energy Utilization & Govt Subsidy Schemes
        {
            "category_id": 9,
            "category_name": "Solar Energy Utilization & Govt Subsidy Schemes",
            "category_kannada": "ಸೌರಶಕ್ತಿ ಕೃಷಿ ಮತ್ತು ಕುಸುಮ್ ಸಬ್ಸಿಡಿ ಯೋಜನೆ",
            "title": "PM-KUSUM Component-B: 80% Subsidy for Standalone Solar Agricultural Pumpsets (7.5HP for ₹48,000 Farmer Share)",
            "title_kannada": "ಕುಸುಮ್ ಯೋಜನೆ: ಸೋಲಾರ್ ಪಂಪ್‌ಸೆಟ್‌ಗಳಿಗೆ 80% ಸಬ್ಸಿಡಿ — ರೈತರಿಗೆ ಹಗಲು ವೇಳೆ ಉಚಿತ ನೀರಾವರಿ",
            "summary": "KREDL invites applications for 7.5HP solar pumpsets. Central Govt covers 30%, Karnataka Govt provides 50%, requiring only 20% (₹48,000) farmer beneficiary contribution.",
            "summary_kannada": "ರೈತರು ಕೇವಲ 20% (₹48,000) ಪಾಲು ಭರಿಸಿದರೆ ಸಾಕು, ಕೇಂದ್ರ ಮತ್ತು ರಾಜ್ಯ ಸರ್ಕಾರದಿಂದ 80% ಸಹಾಯಧನ.",
            "content": "Solves the chronic night-shift irrigation problem caused by 3-phase grid power schedules. Reliable daytime irrigation helps increase double-cropping acreage with zero recurring electricity bills.",
            "source": "KREDL (Karnataka Renewable Energy Development Ltd)",
            "read_time": "4 min read",
            "published_date": "23 Nov 2026",
            "key_takeaways": json.dumps([
                "80% composite subsidy (Centre 30% + Karnataka State 50%)",
                "Farmer contribution: only ₹48,000 for complete 7.5HP solar installation",
                "Daytime irrigation from 9:00 AM to 4:30 PM with automatic pressure controller",
            ]),
            "voice_query_prompt": "ಕುಸುಮ್ ಸೋಲಾರ್ ಪಂಪ್ ಯೋಜನೆಗೆ ಅರ್ಜಿ ಸಲ್ಲಿಸುವುದು ಹೇಗೆ ಮತ್ತು ದಾಖಲೆಗಳು ಏನು ಬೇಕು?",
        },
    ]

    for art in articles:
        db.add(models.NewsArticle(**art))
    db.commit()


def seed_dairy_module(db):
    # Wipe and reseed dairy tables to ensure latest exact rate slabs and breeds
    db.query(models.DairyProcurementRate).delete()
    db.query(models.LivestockBreed).delete()
    db.query(models.FeedPlan).delete()
    db.query(models.SireGuide).delete()
    db.query(models.LivestockDisease).delete()

    dairy_rates = [
        # KMF Nandini
        {
            "dairy_name": "KMF Nandini (Karnataka Milk Federation)",
            "brand_logo": "nandini",
            "milk_type": "Cow",
            "slab_name": "Standard Cow Slab (3.5% Fat / 8.5% SNF)",
            "base_fat_pct": 3.5,
            "base_snf_pct": 8.5,
            "rate_per_litre": 42.00,
            "fat_rate_factor": 4.60,
            "snf_rate_factor": 3.40,
            "govt_incentive": 5.00, # Ksheera Dhare scheme -> 42 + 5 = 47
            "notes": "Base rate ₹42.00/L + Karnataka Govt ₹5.00/L Ksheera Dhare subsidy = ₹47.00/L effective payout. Direct DBT to farmer FID.",
        },
        {
            "dairy_name": "KMF Nandini (Karnataka Milk Federation)",
            "brand_logo": "nandini",
            "milk_type": "Cow",
            "slab_name": "High-Fat Cow Slab (4.5% Fat / 8.8% SNF)",
            "base_fat_pct": 4.5,
            "base_snf_pct": 8.8,
            "rate_per_litre": 46.50,
            "fat_rate_factor": 4.60,
            "snf_rate_factor": 3.40,
            "govt_incentive": 5.00, # 46.50 + 5 = 51.50
            "notes": "Premium slab for high-fat Jersey, Gir, and indigenous cow milk (₹46.50 base + ₹5.00 Ksheera Dhare = ₹51.50/L).",
        },
        {
            "dairy_name": "KMF Nandini (Karnataka Milk Federation)",
            "brand_logo": "nandini",
            "milk_type": "Buffalo",
            "slab_name": "Standard Buffalo Slab (6.0% Fat / 9.0% SNF)",
            "base_fat_pct": 6.0,
            "base_snf_pct": 9.0,
            "rate_per_litre": 50.00,
            "fat_rate_factor": 5.20,
            "snf_rate_factor": 3.80,
            "govt_incentive": 5.00, # 50 + 5 = 55
            "notes": "Base rate ₹50.00/L + ₹5.00 Ksheera Dhare = ₹55.00/L. Paid across all district milk unions.",
        },
        {
            "dairy_name": "KMF Nandini (Karnataka Milk Federation)",
            "brand_logo": "nandini",
            "milk_type": "Buffalo",
            "slab_name": "High-Fat Murrah Slab (7.5% Fat / 9.2% SNF)",
            "base_fat_pct": 7.5,
            "base_snf_pct": 9.2,
            "rate_per_litre": 57.50,
            "fat_rate_factor": 5.20,
            "snf_rate_factor": 3.80,
            "govt_incentive": 5.00, # 57.50 + 5 = 62.50
            "notes": "Top incentive slab for Murrah & Jaffarabadi rich milk reaching up to ₹62.50/L net realization.",
        },

        # Amul
        {
            "dairy_name": "Amul (GCMMF)",
            "brand_logo": "amul",
            "milk_type": "Cow",
            "slab_name": "Standard Cow Slab (3.5% Fat / 8.5% SNF)",
            "base_fat_pct": 3.5,
            "base_snf_pct": 8.5,
            "rate_per_litre": 40.50,
            "fat_rate_factor": 4.80,
            "snf_rate_factor": 3.20,
            "govt_incentive": 0.0,
            "notes": "Direct private cooperative procurement centers in Belagavi, Mandya, and Kolar districts.",
        },
        {
            "dairy_name": "Amul (GCMMF)",
            "brand_logo": "amul",
            "milk_type": "Buffalo",
            "slab_name": "Standard Buffalo Slab (6.0% Fat / 9.0% SNF)",
            "base_fat_pct": 6.0,
            "base_snf_pct": 9.0,
            "rate_per_litre": 52.00,
            "fat_rate_factor": 5.00,
            "snf_rate_factor": 3.50,
            "govt_incentive": 0.0,
            "notes": "Competitive pricing in border taluks with 10-day computerized payments.",
        },

        # Dodla Dairy
        {
            "dairy_name": "Dodla Dairy",
            "brand_logo": "dodla",
            "milk_type": "Cow",
            "slab_name": "Standard Cow Slab (3.5% Fat / 8.5% SNF)",
            "base_fat_pct": 3.5,
            "base_snf_pct": 8.5,
            "rate_per_litre": 39.50,
            "fat_rate_factor": 4.50,
            "snf_rate_factor": 3.10,
            "govt_incentive": 0.0,
            "notes": "Active procurement in Chikkaballapur, Kolar, and Tumakuru border blocks with weekly settlements.",
        },
        {
            "dairy_name": "Dodla Dairy",
            "brand_logo": "dodla",
            "milk_type": "Buffalo",
            "slab_name": "Standard Buffalo Slab (6.0% Fat / 9.0% SNF)",
            "base_fat_pct": 6.0,
            "base_snf_pct": 9.0,
            "rate_per_litre": 51.00,
            "fat_rate_factor": 4.80,
            "snf_rate_factor": 3.30,
            "govt_incentive": 0.0,
            "notes": "Weekly bank settlements with automated fat testing printouts.",
        },

        # Heritage Foods
        {
            "dairy_name": "Heritage Foods",
            "brand_logo": "heritage",
            "milk_type": "Cow",
            "slab_name": "Standard Cow Slab (3.5% Fat / 8.5% SNF)",
            "base_fat_pct": 3.5,
            "base_snf_pct": 8.5,
            "rate_per_litre": 40.00,
            "fat_rate_factor": 4.60,
            "snf_rate_factor": 3.30,
            "govt_incentive": 0.0,
            "notes": "Fast digital payment via Chilling Centers in Eastern Karnataka.",
        },
        {
            "dairy_name": "Heritage Foods",
            "brand_logo": "heritage",
            "milk_type": "Buffalo",
            "slab_name": "Standard Buffalo Slab (6.0% Fat / 9.0% SNF)",
            "base_fat_pct": 6.0,
            "base_snf_pct": 9.0,
            "rate_per_litre": 51.50,
            "fat_rate_factor": 4.90,
            "snf_rate_factor": 3.40,
            "govt_incentive": 0.0,
            "notes": "Quality bonuses for low somatic cell count and high hygienic milk collection.",
        },

        # Tirumala Dairy
        {
            "dairy_name": "Tirumala Dairy (Lactalis)",
            "brand_logo": "tirumala",
            "milk_type": "Cow",
            "slab_name": "Standard Cow Slab (3.5% Fat / 8.5% SNF)",
            "base_fat_pct": 3.5,
            "base_snf_pct": 8.5,
            "rate_per_litre": 39.00,
            "fat_rate_factor": 4.40,
            "snf_rate_factor": 3.10,
            "govt_incentive": 0.0,
            "notes": "Active collection centers across Southern Karnataka border blocks.",
        },
        {
            "dairy_name": "Tirumala Dairy (Lactalis)",
            "brand_logo": "tirumala",
            "milk_type": "Buffalo",
            "slab_name": "Standard Buffalo Slab (6.0% Fat / 9.0% SNF)",
            "base_fat_pct": 6.0,
            "base_snf_pct": 9.0,
            "rate_per_litre": 50.50,
            "fat_rate_factor": 4.80,
            "snf_rate_factor": 3.20,
            "govt_incentive": 0.0,
            "notes": "French dairy group Lactalis quality standards with bi-monthly payouts.",
        },
    ]
    for r in dairy_rates:
        db.add(models.DairyProcurementRate(**r))

    # Breeds (including Malnad Gidda)
    breeds = [
        {
            "breed_name": "Holstein Friesian (HF) Crossbred",
            "breed_kannada": "ಎಚ್‌ಎಫ್ ಮಿಶ್ರತಳಿ ಹಸು (HF Cross)",
            "animal_type": "Cow",
            "origin": "European Crossbred (HF × Indigenous)",
            "avg_yield_litres": 18.0,
            "peak_yield_litres": 28.0,
            "fat_pct": 3.6,
            "climate_zone": "Southern Transition Zone / Malnad / Cool Dry Zones (12°C–32°C)",
            "min_temp_c": 12.0,
            "max_temp_c": 32.0,
            "heat_tolerance": "Moderate",
            "drought_resistance": "Low",
            "disease_resistance": "Moderate (requires tick management & clean dry bedding)",
            "feeding_requirement": "High green fodder & concentrate (35kg green + 5–7kg cattle feed)",
            "description": "Highest milk producing cow in Karnataka. Excellent for commercial dairy in Bengaluru, Hassan, Shivamogga, and Mysuru. Requires cool ventilated shed during summer.",
        },
        {
            "breed_name": "Jersey Crossbred",
            "breed_kannada": "ಜರ್ಸಿ ಮಿಶ್ರತಳಿ ಹಸು (Jersey Cross)",
            "animal_type": "Cow",
            "origin": "Jersey × Indian Zebu",
            "avg_yield_litres": 14.0,
            "peak_yield_litres": 22.0,
            "fat_pct": 4.5,
            "climate_zone": "All Karnataka Agro-Climatic Zones (Coastal, Dry, Malnad)",
            "min_temp_c": 14.0,
            "max_temp_c": 36.0,
            "heat_tolerance": "High",
            "drought_resistance": "Moderate",
            "disease_resistance": "High (resilient against tick fever)",
            "feeding_requirement": "Moderate feed requirement with high feed-to-milk conversion ratio",
            "description": "Ideal medium-sized cow with high milk fat (4.2%–4.8%) that fetches superior cooperative rates. Hardier than HF with lower veterinary maintenance costs.",
        },
        {
            "breed_name": "Gir Cow",
            "breed_kannada": "ಗೀರ್ ಹಸು (Gir - ಶುದ್ಧ ದೇಸಿ ಗೋವಂಶ)",
            "animal_type": "Cow",
            "origin": "Gujarat / Indigenous Desi Zebu",
            "avg_yield_litres": 12.0,
            "peak_yield_litres": 18.0,
            "fat_pct": 4.8,
            "climate_zone": "Dry & Semi-arid Zones (Central & North Karnataka)",
            "min_temp_c": 15.0,
            "max_temp_c": 42.0,
            "heat_tolerance": "Very High",
            "drought_resistance": "Very High",
            "disease_resistance": "Exceptional (natural immunity to tick-borne theileriosis)",
            "feeding_requirement": "Thrives on local dry roughage, agricultural by-products, and grazing",
            "description": "Renowned A2 milk indigenous breed with prominent hump and long curved horns. Exceptional heat tolerance and disease resistance. Premium pricing for A2 milk and ghee in urban markets.",
        },
        {
            "breed_name": "Hallikar",
            "breed_kannada": "ಹಳ್ಳಿಕಾರ್ ಹಸು (ಕರ್ನಾಟಕದ ಹೆಮ್ಮೆಯ ತಳಿ)",
            "animal_type": "Cow",
            "origin": "Native Southern Karnataka (Hassan, Tumakuru, Mandya)",
            "avg_yield_litres": 6.5,
            "peak_yield_litres": 10.0,
            "fat_pct": 5.2,
            "climate_zone": "All Karnataka Agro-climatic Zones (Semi-arid to Hilly)",
            "min_temp_c": 10.0,
            "max_temp_c": 44.0,
            "heat_tolerance": "Outstanding",
            "drought_resistance": "Outstanding",
            "disease_resistance": "Immune to most local tropical pathogens",
            "feeding_requirement": "Minimal input; thrives on dry ragi straw and wild grazing",
            "description": "Hardy native draught breed of Karnataka with high milk fat (>5%). Perfect for zero-budget natural farming (ZBNF), Jeevamrutha preparation, and rugged dryland farming.",
        },
        {
            "breed_name": "Malnad Gidda",
            "breed_kannada": "ಮಲೆನಾಡು ಗಿಡ್ಡ (ಪಶ್ಚಿಮ ಘಟ್ಟಗಳ ಕುಬ್ಜ ತಳಿ)",
            "animal_type": "Cow",
            "origin": "Western Ghats / Malnad of Karnataka (Shivamogga, Uttara Kannada, Udupi, Kodagu)",
            "avg_yield_litres": 4.5,
            "peak_yield_litres": 7.0,
            "fat_pct": 5.5,
            "climate_zone": "High-rainfall Malnad & Coastal Belt (humid, hilly, heavy rain)",
            "min_temp_c": 12.0,
            "max_temp_c": 38.0,
            "heat_tolerance": "High",
            "drought_resistance": "High",
            "disease_resistance": "Extraordinary (immune to foot rot, leech infestations, tick diseases)",
            "feeding_requirement": "Ultra-low input; grazes forest shrubs, bamboo leaves, and wild grass",
            "description": "Prized dwarf indigenous cattle of the Western Ghats. Highly adapted to torrential rains and steep slopes. Milk is rich in A2 beta-casein with high medicinal value and fat percentage reaching 5.5%–6.0%.",
        },
        {
            "breed_name": "Murrah Buffalo",
            "breed_kannada": "ಮುರ್ರಾ ಎಮ್ಮೆ (ಕಪ್ಪು ಚಿನ್ನ - Murrah Buffalo)",
            "animal_type": "Buffalo",
            "origin": "Haryana / North India (Adapted across Karnataka)",
            "avg_yield_litres": 14.0,
            "peak_yield_litres": 22.0,
            "fat_pct": 7.2,
            "climate_zone": "Canal command areas / irrigated belts across Karnataka",
            "min_temp_c": 15.0,
            "max_temp_c": 38.0,
            "heat_tolerance": "Moderate (requires daily water wallowing / spray wash)",
            "drought_resistance": "Moderate",
            "disease_resistance": "High (naturally resistant to clinical mastitis)",
            "feeding_requirement": "High roughage consumer (40kg green/dry + 4kg concentrate)",
            "description": "The premier dairy buffalo breed ('Black Gold'). Milk contains 7% to 8% fat, fetching the highest price per liter at dairies (₹55–₹62/L). Jet-black body with tightly curled horns.",
        },
        {
            "breed_name": "Jaffarabadi Buffalo",
            "breed_kannada": "ಜಾಫರಾಬಾದಿ ಎಮ್ಮೆ (ಭಾರಿ ತೂಕದ ಅಧಿಕ ಕೊಬ್ಬಿನ ತಳಿ)",
            "animal_type": "Buffalo",
            "origin": "Saurashtra / West Coast River Belts",
            "avg_yield_litres": 15.0,
            "peak_yield_litres": 24.0,
            "fat_pct": 7.8,
            "climate_zone": "Coastal and Northern River Basins (Krishna, Tungabhadra)",
            "min_temp_c": 16.0,
            "max_temp_c": 40.0,
            "heat_tolerance": "High",
            "drought_resistance": "High",
            "disease_resistance": "High",
            "feeding_requirement": "Heavy roughage and dry biomass consumer",
            "description": "Heavy-bodied buffalo with drooped horns. Yields rich, viscous milk (>7.8% fat) popular for khoa, peda, and ghee production in Belagavi, Dharwad, and Bagalkote.",
        },
    ]
    for b in breeds:
        db.add(models.LivestockBreed(**b))

    # Feed Plans: (a) Unfertilized/Dry and (b) High-Yield Lactating
    feed_plans = [
        # (a) Unfertilized / Dry Cows & Buffaloes
        {
            "animal_type": "Cow",
            "stage": "Dry / Unfertilized",
            "plan_title": "Unfertilized / Dry Cow Ration (Body Condition & Fertility Diet)",
            "plan_title_kannada": "ಬತ್ತಿದ / ಗರ್ಭಧರಿಸದ ಹಸುಗಳ ಪೋಷಕಾಂಶ ಆಹಾರ ಯೋಜನೆ",
            "body_weight_kg": 400,
            "target_yield_litres": 0.0,
            "green_fodder_kg": 15.0,
            "dry_fodder_kg": 6.0,
            "concentrate_kg": 1.5,
            "mineral_mixture_g": 50,
            "bypass_fat_g": 0,
            "salt_g": 30,
            "water_litres": 45,
            "schedule_tips": (
                "1. Focus on body condition score (BCS 3.0 to 3.5). Avoid over-feeding grain concentrate to prevent fatty liver.\n"
                "2. Provide 50g chelated mineral mixture daily to stimulate timely ovarian follicle development.\n"
                "3. Ensure dry fodder (ragi/paddy straw) is treated with 2% urea-molasses solution for higher digestibility."
            ),
        },
        {
            "animal_type": "Buffalo",
            "stage": "Dry / Unfertilized",
            "plan_title": "Unfertilized / Dry Buffalo Ration (Conception & Ruminal Conditioning)",
            "plan_title_kannada": "ಬತ್ತಿದ / ಗರ್ಭಧರಿಸದ ಎಮ್ಮೆಗಳ ಪೋಷಕಾಂಶ ಆಹಾರ ಯೋಜನೆ",
            "body_weight_kg": 500,
            "target_yield_litres": 0.0,
            "green_fodder_kg": 20.0,
            "dry_fodder_kg": 8.0,
            "concentrate_kg": 2.0,
            "mineral_mixture_g": 60,
            "bypass_fat_g": 0,
            "salt_g": 35,
            "water_litres": 60,
            "schedule_tips": (
                "1. Buffaloes efficiently digest fibrous dry roughage. Provide green fodder (Maize/Sorghum) mixed with chopped straw.\n"
                "2. Feed 60g mineral mixture with Vitamin A & E to prevent silent heat and irregular estrus cycles.\n"
                "3. Offer clean water twice daily; wallowing or hosing down in afternoon stimulates endocrine fertility."
            ),
        },

        # (b) High-Yield Lactating Cows & Buffaloes
        {
            "animal_type": "Cow",
            "stage": "Lactating High-Yield",
            "plan_title": "High-Yield Lactating Cow Ration (18–25+ L/day - Peak Milk & Fat/SNF)",
            "plan_title_kannada": "ಅಧಿಕ ಹಾಲು ನೀಡುವ ಹಸುಗಳ ಪೋಷಕಾಂಶ ಯೋಜನೆ (18-25+ ಲೀಟರ್)",
            "body_weight_kg": 480,
            "target_yield_litres": 22.0,
            "green_fodder_kg": 35.0,
            "dry_fodder_kg": 6.0,
            "concentrate_kg": 8.0,
            "mineral_mixture_g": 100,
            "bypass_fat_g": 100,
            "salt_g": 50,
            "water_litres": 110,
            "schedule_tips": (
                "1. Add 100g rumen-protected bypass fat (Prilled fat) to prevent negative energy balance and body weight loss.\n"
                "2. Include 30g sodium bicarbonate (baking soda) in morning feed to prevent subacute rumen acidosis (SARA).\n"
                "3. Split concentrate: 4kg during morning milking, 4kg during evening milking. Always feed roughage first."
            ),
        },
        {
            "animal_type": "Buffalo",
            "stage": "Lactating High-Yield",
            "plan_title": "High-Yield Lactating Buffalo Ration (12–18 L/day, 7.5%–8% Fat Optimization)",
            "plan_title_kannada": "ಅಧಿಕ ಹಾಲು ನೀಡುವ ಎಮ್ಮೆಗಳ ಪೋಷಕಾಂಶ ಯೋಜನೆ (12-18 ಲೀಟರ್, 7.5% ಫ್ಯಾಟ್)",
            "body_weight_kg": 550,
            "target_yield_litres": 14.0,
            "green_fodder_kg": 35.0,
            "dry_fodder_kg": 7.0,
            "concentrate_kg": 6.5,
            "mineral_mixture_g": 100,
            "bypass_fat_g": 80,
            "salt_g": 50,
            "water_litres": 100,
            "schedule_tips": (
                "1. To sustain >7.5% milk fat, feed at least 6–7kg dry roughage before concentrate to maintain rumen acetic acid.\n"
                "2. Cottonseed cake (1.5kg) or roasted soybean provides superior bypass protein for sustained peak lactation.\n"
                "3. Ensure continuous access to fresh drinking water; every liter of milk requires 4–5 liters of water intake."
            ),
        },
    ]
    for fp in feed_plans:
        db.add(models.FeedPlan(**fp))

    # Sire Guides
    sires = [
        {
            "dam_breed": "Holstein Friesian (HF) Crossbred Cow",
            "dam_breed_kannada": "ಎಚ್‌ಎಫ್ ಮಿಶ್ರತಳಿ ಹಸು",
            "recommended_sire": "Pedigree Proven HF Sire (50%–75% Exotic Bloodline)",
            "recommended_sire_kannada": "ಪ್ರೂವನ್ ಎಚ್‌ಎಫ್ ಹೋರಿ ವೀರ್ಯ (50%-75% ಮಟ್ಟ)",
            "purpose": "Sustain high peak milk yield (20–25L) while preventing exotic blood from exceeding 75% in warm Karnataka belts",
            "expected_gain": "+3 to 5 Litres/day yield increase over dam with strong udder attachment",
            "inbreeding_caution": "Never use semen sharing the same sire code; verify AI card pedigree registration",
            "veterinary_tip": "In dry zones (Bellary, Raichur), consider alternating with high-index Jersey semen for superior heat tolerance.",
        },
        {
            "dam_breed": "Jersey Crossbred Cow",
            "dam_breed_kannada": "ಜರ್ಸಿ ಮಿಶ್ರತಳಿ ಹಸು",
            "recommended_sire": "High-Index Progeny Tested Jersey Sire",
            "recommended_sire_kannada": "ಉತ್ತಮ ಗುಣಮಟ್ಟದ ಜರ್ಸಿ ಹೋರಿ ವೀರ್ಯ",
            "purpose": "Consolidate high fat percentage (4.6%–5.0%) and preserve compact body size with easy calving",
            "expected_gain": "+15% to 20% milk fat solids and extended productive herd longevity",
            "inbreeding_caution": "Avoid village scrubs; use semen only from KMF/BAIF certified semen stations",
            "veterinary_tip": "Jersey crosses exhibit the shortest inter-calving interval (12–13 months) among crossbreds.",
        },
        {
            "dam_breed": "Gir Cow",
            "dam_breed_kannada": "ಗೀರ್ ಹಸು (ದೇಸಿ)",
            "recommended_sire": "Purebred Pedigree Gir Bull Semen (NDDB / Gujarat Certified)",
            "recommended_sire_kannada": "ಶುದ್ಧ ಗೀರ್ ತಳಿಯ ಹೋರಿ ವೀರ್ಯ",
            "purpose": "Purebred conservation of indigenous A2 dairy traits with high disease and tick resistance",
            "expected_gain": "Preserves pure Gir genetic traits; offspring achieves 12–16 Litres/day A2 milk",
            "inbreeding_caution": "Do not cross with exotic HF or Jersey to preserve purebred A2 certification value",
            "veterinary_tip": "Avail sorted female sexed Gir semen to guarantee female heifer calves with 90% certainty.",
        },
        {
            "dam_breed": "Hallikar Cow",
            "dam_breed_kannada": "ಹಳ್ಳಿಕಾರ್ ಹಸು",
            "recommended_sire": "Pure Hallikar Bull Semen (or Gir Semen for Dual-Purpose Dairy)",
            "recommended_sire_kannada": "ಹಳ್ಳಿಕಾರ್ ಅಥವಾ ಗೀರ್ ಹೋರಿ ವೀರ್ಯ",
            "purpose": "Retain native draught agility; crossing with Gir bull creates a dual-purpose high-yielding A2 milker",
            "expected_gain": "Native hardiness preserved; +4 Litres/day milk increase if crossed with Gir",
            "inbreeding_caution": "Never inseminate Hallikar heifers with large exotic HF semen due to fatal calving dystocia risk",
            "veterinary_tip": "Hallikar heifers have compact pelvic morphology; only small-calf sires should be selected.",
        },
        {
            "dam_breed": "Malnad Gidda Cow",
            "dam_breed_kannada": "ಮಲೆನಾಡು ಗಿಡ್ಡ ಹಸು",
            "recommended_sire": "Selected Superior Malnad Gidda Bull Semen (or Vechur / Gir Semen)",
            "recommended_sire_kannada": "ಉತ್ತಮ ಮಲೆನಾಡು ಗಿಡ್ಡ ಅಥವಾ ಗೀರ್ ವೀರ್ಯ",
            "purpose": "Preserve extreme dwarf hardiness, forest foraging ability, and rich 5.5% fat medicinal A2 milk",
            "expected_gain": "Maintains 100% natural tick resistance with milk yield boosting to 6–7 Litres/day",
            "inbreeding_caution": "Strictly avoid standard large breeds (HF/Jersey) — causes fatal dystocia in dwarf cows",
            "veterinary_tip": "Malnad Gidda calves are born light (10–12kg) with zero assisted deliveries required.",
        },
        {
            "dam_breed": "Indigenous Non-Descript / Local Cow",
            "dam_breed_kannada": "ನಾಟಿ / ಸ್ಥಳೀಯ ಮಿಶ್ರ ಹಸು",
            "recommended_sire": "Progeny-Tested Jersey or Gir Semen",
            "recommended_sire_kannada": "ಜರ್ಸಿ ಅಥವಾ ಗೀರ್ ಹೋರಿ ವೀರ್ಯ",
            "purpose": "Grading up local non-descript cattle to produce sturdy F1 cows with 10–12 Litres daily yield",
            "expected_gain": "+80% to 120% milk yield improvement in first generation daughter",
            "inbreeding_caution": "Castrate local non-descript bulls in the village to prevent regressive backcrossing",
            "veterinary_tip": "Inseminate 10–12 hours after observing standing heat (morning-evening rule).",
        },
        {
            "dam_breed": "Murrah Buffalo",
            "dam_breed_kannada": "ಮುರ್ರಾ ಎಮ್ಮೆ",
            "recommended_sire": "Progeny-Tested Murrah Buffalo Sire Semen (NDDB / CIRB Certified)",
            "recommended_sire_kannada": "ಪ್ರೂವನ್ ಮುರ್ರಾ ಹೋರಿ ವೀರ್ಯ",
            "purpose": "Consolidate elite milk yield (15–20L) and sustain high fat percentage (>7.5%)",
            "expected_gain": "+3 to 4 Litres/day yield increase and shorter service period",
            "inbreeding_caution": "Verify sire dam yield certificate (dam yield >3,500kg per lactation)",
            "veterinary_tip": "Buffaloes exhibit silent heat; check for transparent mucus discharge and tail raising at night.",
        },
        {
            "dam_breed": "Jaffarabadi Buffalo",
            "dam_breed_kannada": "ಜಾಫರಾಬಾದಿ ಎಮ್ಮೆ",
            "recommended_sire": "High-Index Jaffarabadi or Elite Murrah Semen",
            "recommended_sire_kannada": "ಜಾಫರಾಬಾದಿ ಅಥವಾ ಮುರ್ರಾ ವೀರ್ಯ",
            "purpose": "Maintain high body mass and ultra-rich 8% butterfat production",
            "expected_gain": "Enhanced milk solids for high-yield dairy processing",
            "inbreeding_caution": "Ensure proper mating pen spacing to avoid horn injuries",
            "veterinary_tip": "Perform AI during cooler hours (10:00 PM to 6:00 AM) for higher conception rate.",
        },
        {
            "dam_breed": "Local / Non-Descript Buffalo",
            "dam_breed_kannada": "ಸ್ಥಳೀಯ ನಾಟಿ ಎಮ್ಮೆ",
            "recommended_sire": "Pedigree Proven Murrah Buffalo Semen",
            "recommended_sire_kannada": "ಶುದ್ಧ ಮುರ್ರಾ ಹೋರಿ ವೀರ್ಯ",
            "purpose": "Grade up low-yielding local buffaloes into high-producing Murrah-type stock",
            "expected_gain": "+100% milk yield increase (from 4L to 9–12L per day)",
            "inbreeding_caution": "Avoid uncertified village bulls with low reproductive vigour",
            "veterinary_tip": "Deworm dam with Albendazole/Fenbendazole prior to breeding.",
        },
    ]
    for s in sires:
        db.add(models.SireGuide(**s))

    # Livestock Diseases & Behavior Symptoms
    diseases = [
        {
            "symptom_key": "sudden_milk_drop",
            "symptom_display": "Sudden Drop in Milk Yield (20%–50% decrease)",
            "symptom_kannada": "ಹಾಲು ಉತ್ಪಾದನೆಯಲ್ಲಿ ದಿಢೀರ್ ಕುಸಿತ (20%-50% ಇಳಿಕೆ)",
            "suspected_condition": "Subclinical Mastitis, Acute Rumen Acidosis, or Heat Stress",
            "suspected_kannada": "ಕೆಚ್ಚಲು ಬಾವು (ಮಾಸ್ಟಿಟಿಸ್), ಅಜೀರ್ಣ ಅಥವಾ ಉಷ್ಣತೆಯ ಒತ್ತಡ",
            "urgency_level": "Medium",
            "immediate_first_aid": (
                "1. Strip-test milk from each quarter onto a clean plate; check for flakes, clots, or watery fluid.\n"
                "2. Take rectal temperature using a clinical thermometer (Normal: 101.5°F / 38.6°C).\n"
                "3. If temperature is normal but rumen is sluggish, administer 100g yeast bolus and 50g digestive tonic.\n"
                "4. Check for feed change or mouldy straw; provide fresh green fodder and electrolytes in water."
            ),
            "avoid_doing": "Do not inject random antibiotics without checking for mastitis as it contaminates the milk supply and creates antibiotic resistance.",
            "recommended_query": "ಹಸುವಿನಲ್ಲಿ ಹಾಲಿನ ಇಳುವರಿ ಇದ್ದಕ್ಕಿದ್ದಂತೆ ಅರ್ಧದಷ್ಟು ಕಡಿಮೆಯಾಗಿದೆ, ಏನು ಮಾಡಬೇಕು?",
        },
        {
            "symptom_key": "high_fever",
            "symptom_display": "High Fever & Shivering (>103.5°F)",
            "symptom_kannada": "ತೀವ್ರ ಜ್ವರ ಮತ್ತು ನಡುಕ (103.5°F ಗಿಂತ ಹೆಚ್ಚು)",
            "suspected_condition": "Tick Fever (Theileriosis / Babesiosis) or Hemorrhagic Septicemia (HS)",
            "suspected_kannada": "ಉಣ್ಣಿ ಜ್ವರ (ಥೈಲೇರಿಯಾಸಿಸ್/ಬಬೇಸಿಯಾಸಿಸ್) ಅಥವಾ ಗಂಟಲುಬೇನೆ (HS)",
            "urgency_level": "Emergency",
            "immediate_first_aid": (
                "1. Sponge head, neck, and dorsal spine with cold water continuously to prevent heat seizure.\n"
                "2. Inspect urine color: if coffee/red colored, suspected Babesiosis; urgent veterinary antiparasitic injection (Diminazene) needed within 6 hours!\n"
                "3. Administer Meloxicam / Paracetamol veterinary bolus (2 to 3 boluses for adult cattle) for immediate pain and fever relief.\n"
                "4. Immediately dial the Karnataka Pashu Sanjeevini 24/7 Mobile Vet toll-free ambulance (1962)."
            ),
            "avoid_doing": "Do not delay veterinary arrival. Blood protozoan diseases can destroy red blood cells and turn fatal within 24–36 hours.",
            "recommended_query": "ಹಸುವಿಗೆ 104 ಡಿಗ್ರಿ ತೀವ್ರ ಜ್ವರವಿದೆ, ಕಾಫಿ ಬಣ್ಣದ ಮೂತ್ರ ಹೋಗುತ್ತಿದೆ, ತುರ್ತು ಚಿಕಿತ್ಸೆ ಏನು?",
        },
        {
            "symptom_key": "severe_bloating",
            "symptom_display": "Severe Bloating / Swollen Left Flank (Tympanites)",
            "symptom_kannada": "ಹೊಟ್ಟೆ ಉಬ್ಬರ / ಎಡಭಾಗದ ಹೊಟ್ಟೆ ಊದಿಕೊಳ್ಳುವುದು (ಟಿಂಪಾನೈಟಿಸ್)",
            "suspected_condition": "Acute Frothy Bloat from Excess Lush Legumes or Esophageal Choke",
            "suspected_kannada": "ಹೊಟ್ಟೆ ಉಬ್ಬರ (ಟಿಂಪಾನೈಟಿಸ್) - ಉಸಿರುಗಟ್ಟುವ ತುರ್ತು ಸ್ಥಿತಿ",
            "urgency_level": "Emergency",
            "immediate_first_aid": (
                "1. Keep the animal standing with front hooves elevated on a 6-inch mound or ramp to relieve lung compression.\n"
                "2. Secure a 1-inch wooden gag/bit across the mouth with a rope behind horns to stimulate continuous chewing and belching.\n"
                "3. Drench with 200ml sweet edible oil (groundnut, gingelly, or linseed oil) mixed with 20ml turpentine oil to break foam.\n"
                "4. If the animal is grunting and gasping with tongue out, summon a veterinarian for immediate trochar cannula puncture."
            ),
            "avoid_doing": "Do not allow the animal to lie down, as rumen pressure against the diaphragm causes fatal suffocation within minutes.",
            "recommended_query": "ಹಸುವಿನ ಎಡ ಹೊಟ್ಟೆ ಡ್ರಮ್ ತರಹ ಊದಿಕೊಂಡಿದೆ ಮತ್ತು ಉಸಿರಾಟಕ್ಕೆ ಕಷ್ಟಪಡುತ್ತಿದೆ, ತುರ್ತು ಮನೆಮದ್ದು ಏನು?",
        },
        {
            "symptom_key": "loss_of_appetite",
            "symptom_display": "Loss of Appetite / Refusal to Eat Fodder & No Rumination",
            "symptom_kannada": "ಮೇವು ತಿನ್ನದಿರುವುದು / ಹಸಿವು ಕಡಿಮೆಯಾಗುವುದು ಮತ್ತು ಮೆಲಕು ಹಾಕದಿರುವುದು",
            "suspected_condition": "Rumen Acidosis, Ketosis, or Simple Indigestion",
            "suspected_kannada": "ರುಮೆನ್ ಆಸಿಡೋಸಿಸ್, ಕೀಟೋಸಿಸ್ ಅಥವಾ ಹೊಟ್ಟೆ ಕಟ್ಟುವಿಕೆ",
            "urgency_level": "Medium",
            "immediate_first_aid": (
                "1. Stop all cereal grains, rice gruel, and commercial pellet concentrate for 24 hours.\n"
                "2. Drench with 100g baking soda (Sodium Bicarbonate) dissolved in 1 liter lukewarm water to neutralize lactic acid.\n"
                "3. Prepare herbal digestive paste: 50g ginger + 50g garlic + 20g black pepper + 50g jaggery and administer orally.\n"
                "4. Offer soft wilted green fodder in small handfuls along with clean water."
            ),
            "avoid_doing": "Do not force-feed grain flours or sugary gruel which will aggravate ruminal fermentation acidosis.",
            "recommended_query": "ಹಸು ಎರಡು ದಿನದಿಂದ ಮೇವು ತಿನ್ನುತ್ತಿಲ್ಲ ಮತ್ತು ಮೆಲಕು ಹಾಕುತ್ತಿಲ್ಲ, ಜೀರ್ಣಶಕ್ತಿ ಹೆಚ್ಚಿಸಲು ಏನು ಮಾಡಬೇಕು?",
        },
        {
            "symptom_key": "mastitis_signs",
            "symptom_display": "Mastitis Signs / Hot, Swollen Udder with Watery or Clotted Milk",
            "symptom_kannada": "ಕೆಚ್ಚಲು ಬಾವು - ಕೆಚ್ಚಲು ಬಿಸಿ ಮತ್ತು ಹಾಲಿನಲ್ಲಿ ರಕ್ತ ಅಥವಾ ಮೊಸರಿನಂತಹ ಗಂಟುಗಳು",
            "suspected_condition": "Acute Clinical Mastitis (Bacterial Streptococcus / E. Coli Infection)",
            "suspected_kannada": "ಕೆಚ್ಚಲು ಬಾವು ರೋಗ (ಕ್ಲಿನಿಕಲ್ ಮಾಸ್ಟಿಟಿಸ್)",
            "urgency_level": "High",
            "immediate_first_aid": (
                "1. Strip out the infected quarter completely into a separate bowl every 2 hours and bury/discard the milk safely.\n"
                "2. Apply cold ice packs or aloe vera + turmeric paste over the swollen quarter to reduce inflammation.\n"
                "3. Always milk the healthy three quarters first, and milk the affected quarter last to prevent pathogen cross-transfer.\n"
                "4. Call a veterinary doctor for intramammary infusion and anti-inflammatory injection within 12 hours to save the teat."
            ),
            "avoid_doing": "Do not leave residual milk inside the affected teat. Incomplete stripping creates a bacterial breeding incubator.",
            "recommended_query": "ಹಸುವಿನ ಕೆಚ್ಚಲು ಊದಿಕೊಂಡು ಬಿಸಿಯಾಗಿದೆ, ಹಾಲಿನಲ್ಲಿ ಗಂಟು ಬರುತ್ತಿದೆ, ಪ್ರಥಮ ಚಿಕಿತ್ಸೆ ಏನು?",
        },
        {
            "symptom_key": "lameness_limping",
            "symptom_display": "Lameness / Limping in Hoof & Inability to Bear Weight",
            "symptom_kannada": "ಕುಂಟುವುದು / ಕಾಲಿನಲ್ಲಿ ಊತ ಮತ್ತು ಗೊರಸಿನಲ್ಲಿ ಗಾಯ",
            "suspected_condition": "Foot Rot, Interdigital Dermatitis, or Foreign Body Puncture",
            "suspected_kannada": "ಕಾಲು ಕೊಳೆತ ರೋಗ ಅಥವಾ ಗೊರಸಿನಲ್ಲಿ ಮುಳ್ಳು/ಕಲ್ಲು ಚುಚ್ಚಿರುವಿಕೆ",
            "urgency_level": "Medium",
            "immediate_first_aid": (
                "1. Lift and wash the hoof thoroughly with clean water; inspect the interdigital cleft between hooves for stones, wire, or thorns.\n"
                "2. Wash the wound with mild Potassium Permanganate (1:1000 pink solution) to disinfect anaerobic bacteria.\n"
                "3. Apply Povidone-Iodine ointment mixed with zinc oxide powder and wrap lightly with gauze.\n"
                "4. Move the animal to a dry, clean sand-bedded or rubber-matted pen away from slush and slurry."
            ),
            "avoid_doing": "Do not tie the animal in muddy slush or wet concrete where urine and manure accelerate hoof necrosis.",
            "recommended_query": "ಹಸು ಕಾಲಲ್ಲಿ ಕುಂಟುತ್ತಿದೆ ಮತ್ತು ಗೊರಸಿನ ನಡುವೆ ಕೊಳೆತು ವಾಸನೆ ಬರುತ್ತಿದೆ, ಏನು ಹಚ್ಚಬೇಕು?",
        },
        {
            "symptom_key": "restlessness_bellowing",
            "symptom_display": "Restlessness & Continuous Bellowing / Tail Swishing & Colic",
            "symptom_kannada": "ಅಸ್ವಸ್ಥತೆ / ನಿರಂತರ ಕೂಗಾಟ / ಬಾಲ ಬಡಿಯುವುದು ಮತ್ತು ಹೊಟ್ಟೆ ನೋವು (ಕೋಲಿಕ್)",
            "suspected_condition": "Estrus Heat Period, Spasmodic Colic Pain, or Heavy Tick Irritation",
            "suspected_kannada": "ಮದೆಯ ಲಕ್ಷಣ (ಹೀಟ್) ಅಥವಾ ಹೊಟ್ಟೆ ಸೆಳೆತ / ಕರುಳಿನ ನೋವು",
            "urgency_level": "Medium",
            "immediate_first_aid": (
                "1. Check the vulva for clear, glassy stringy mucus discharge and swelling — if present, animal is in standing heat!\n"
                "2. If in heat, schedule Artificial Insemination (AI) 10–12 hours later (morning heat -> evening AI; evening heat -> morning AI).\n"
                "3. If animal is kicking at belly, lying down and getting up frequently (Colic): check for intestinal blockage or torsion.\n"
                "4. Drench with warm carminative mixture (ajwain 20g + asafoetida 5g + jaggery 50g) and walk animal gently for 15 minutes."
            ),
            "avoid_doing": "Do not confine animal tightly if experiencing colic spasm; allow comfortable pacing.",
            "recommended_query": "ಹಸು ನಿರಂತರವಾಗಿ ಅರಚುತ್ತಿದೆ, ಬಾಲ ಬಡಿಯುತ್ತಿದೆ ಮತ್ತು ಮದೆಯಲ್ಲಿದೆಯೇ ಎಂದು ತಿಳಿಯುವುದು ಹೇಗೆ?",
        },
    ]
    for d in diseases:
        db.add(models.LivestockDisease(**d))

    db.commit()


# ============================================================================
# SPRINT 3 SEED FUNCTIONS
# ============================================================================

def seed_notifications(db):
    if db.query(models.Notification).count() > 0:
        return

    STANDARD_DOCS = [
        {"key": "aadhaar", "name": "Farmer Aadhaar Card", "name_kannada": "ರೈತರ ಆಧಾರ್ ಕಾರ್ಡ್"},
        {"key": "bhoomi_rtc", "name": "Bhoomi RTC / Pahani Land Record", "name_kannada": "ಭೂಮಿ ಆರ್‌ಟಿಸಿ / ಪಹಣಿ ಜಮೀನು ದಾಖಲೆ"},
        {"key": "bank_passbook", "name": "Aadhaar-Seeded Bank Passbook / NPCI Linked", "name_kannada": "ಆಧಾರ್ ಲಿಂಕ್ ಆದ ಬ್ಯಾಂಕ್ ಪಾಸ್‌ಬುಕ್"},
        {"key": "sowing_cert", "name": "Village Accountant / Crop Sowing Certificate", "name_kannada": "ಬೆಳೆ ದೃಢೀಕರಣ ಪ್ರಮಾಣಪತ್ರ (ಫ್ರೂಟ್ಸ್ ತಂತ್ರಾಂಶ)"},
    ]

    notifications_data = [
        {
            "category": "training",
            "title": "ICAR & KVK Youth Agri-Fellowship & Precision Farming Stipend 2026-27",
            "title_kannada": "ಐಸಿಎಆರ್ ಮತ್ತು ಕೆವಿಕೆ ಯುವ ಕೃಷಿ ಫೆಲೋಶಿಪ್ ಹಾಗೂ ಮಾಸಿಕ ತರಬೇತಿ ಗೌರವಧನ",
            "summary": "Full 6-month hands-on fellowship for rural youth in polyhouse cultivation, soil testing, drone spraying, and high-density horticulture with a ₹12,000/month stipend and guaranteed working capital loan eligibility.",
            "summary_kannada": "ಗ್ರಾಮೀಣ ಯುವಕರಿಗೆ 6 ತಿಂಗಳ ಸುಧಾರಿತ ಕೃಷಿ ತರಬೇತಿ, ಮಾಸಿಕ ₹12,000 ಶಿಷ್ಯವೇತನ ಮತ್ತು ಕೃಷಿ ಯಂತ್ರೋಪಕರಣ ಸ್ಥಾಪನೆಗೆ ನೆರವು.",
            "benefit_amount": "₹12,000 / month stipend + ₹2 Lakh seed grant",
            "deadline_date": "15 Dec 2026",
            "deadline_timestamp": "2026-12-15T23:59:59",
            "urgency": "High",
            "authority": "Indian Council of Agricultural Research & Karnataka KVK Network",
            "portal_url": "https://icar.org.in/fellowships",
            "helpline": "1800-425-1556",
            "eligibility_rules": json.dumps([
                "Age 18 to 35 years resident in Karnataka rural panchayats",
                "Minimum 10th standard pass or diploma in agriculture",
                "Applicant or parent must hold minimum 1 acre agricultural land (RTC verified)",
                "Preference for SC/ST, women farmers, and marginal landholders"
            ]),
            "checklist_template": json.dumps(STANDARD_DOCS),
        },
        {
            "category": "subsidies",
            "title": "Karnataka PM-KUSUM Component B: 80% Solar Agriculture Pump Subsidy",
            "title_kannada": "ಕರ್ನಾಟಕ ಕುಸುಮ್-ಬಿ ಯೋಜನೆ: ಸೌರಶಕ್ತಿ ಕೃಷಿ ಪಂಪ್‌ಸೆಟ್‌ಗೆ 80% ಭಾರಿ ಸಬ್ಸಿಡಿ",
            "summary": "Karnataka Renewable Energy Development Ltd (KREDL) open enrollment for 5HP to 10HP standalone solar water pumping systems under Souramitra portal. 30% Central + 50% State subsidy = 80% total grant.",
            "summary_kannada": "ರೈತರಿಗೆ 80% ಸಬ್ಸಿಡಿಯಲ್ಲಿ 5HP-10HP ಸೋಲಾರ್ ಪಂಪ್ ವಿತರಣೆ. ರೈತರ ಪಾಲು ಕೇವಲ 20%. ವಿದ್ಯುತ್ ಮಾರ್ಗವಿಲ್ಲದ ತೋಟಗಳಿಗೆ ಆದ್ಯತೆ.",
            "benefit_amount": "Up to ₹2,80,000 subsidy per installation",
            "deadline_date": "31 Dec 2026",
            "deadline_timestamp": "2026-12-31T23:59:59",
            "urgency": "Urgent",
            "authority": "KREDL Souramitra & Ministry of New and Renewable Energy",
            "portal_url": "https://kredl.karnataka.gov.in/souramitra",
            "helpline": "080-22208591",
            "eligibility_rules": json.dumps([
                "Farmer must own agricultural land with borewell/openwell yield clearance",
                "Off-grid farms or waiting for ESCOM grid energization get first priority",
                "Only 20% farmer contribution required upon provisional sanction",
                "5-year comprehensive on-site warranty and remote IoT monitoring included"
            ]),
            "checklist_template": json.dumps(STANDARD_DOCS),
        },
        {
            "category": "subsidies",
            "title": "Pradhan Mantri Krishi Sinchayee Yojana (PMKSY) Drip & Micro-Irrigation Subsidy",
            "title_kannada": "ಸೂಕ್ಷ್ಮ ಹನಿ ನೀರಾವರಿ ಯೋಜನೆ: ಸಣ್ಣ ಮತ್ತು ಅತಿ ಸಣ್ಣ ರೈತರಿಗೆ 90% ಸಹಾಯಧನ",
            "summary": "State horticulture and agriculture department subsidy for inline/online drip irrigation in Arecanut, Ginger, Vegetables, and Pepper gardens. 90% subsidy for SC/ST/Small farmers and 75% for general farmers.",
            "summary_kannada": "ಅಡಿಕೆ, ಶುಂಠಿ, ತರಕಾರಿ ಬೆಳೆಗಾರರಿಗೆ ಹನಿ ನೀರಾವರಿ ಪೈಪ್ ಹಾಗೂ ಫಿಲ್ಟರ್‌ಗಳಿಗೆ ಶೇ. 90 ವರೆಗೆ ಸಹಾಯಧನ.",
            "benefit_amount": "Up to ₹45,000 per acre (Max 5 Acres)",
            "deadline_date": "20 Jan 2027",
            "deadline_timestamp": "2027-01-20T23:59:59",
            "urgency": "High",
            "authority": "Directorate of Horticulture & Watershed Development, Karnataka",
            "portal_url": "https://horticulturedir.karnataka.gov.in",
            "helpline": "080-26571925",
            "eligibility_rules": json.dumps([
                "Small & marginal farmers (holding < 5 acres) verified via FRUITS database",
                "Functional water source (borewell/farm pond/river lift) on the parcel",
                "Empaneled vendor quotation and GPS survey required before installation",
                "Subsidized systems eligible for inspection and direct vendor payment release"
            ]),
            "checklist_template": json.dumps(STANDARD_DOCS),
        },
        {
            "category": "insurance",
            "title": "PMFBY Rabi 2026-27 Crop Insurance Enrollment & Premium Due Reminder",
            "title_kannada": "ಪ್ರಧಾನ ಮಂತ್ರಿ ಫಸಲ್ ಬಿಮಾ ಯೋಜನೆ (PMFBY) ಹಿಂಗಾರು ಬೆಳೆ ವಿಮೆ ನೋಂದಣಿ ಅಂತಿಮ ಗಡುವು",
            "summary": "Enrollment window closes for Rabi Paddy, Maize, Bengal Gram, and Sunflower. Farmers pay nominal 1.5% premium for Rabi field crops and 5% for commercial/horticultural crops. In case of localized weather disaster, report loss within 72 hours via Krishi Rakshak Helpline 14447.",
            "summary_kannada": "ಹಿಂಗಾರು ಬೆಳೆಗಳ ನಷ್ಟ ಪರಿಹಾರಕ್ಕೆ ವಿಮೆ ಮಾಡಿಸಲು ಕೊನೆಯ ದಿನಾಂಕ. ಪ್ರಾಕೃತಿಕ ವಿಕೋಪ ಉಂಟಾದರೆ 72 ಗಂಟೆಯೊಳಗೆ 14447 ಸಹಾಯವಾಣಿಗೆ ಕರೆ ಮಾಡಿ.",
            "benefit_amount": "Sum Insured up to ₹48,000/acre for Paddy & Maize",
            "deadline_date": "10 Dec 2026",
            "deadline_timestamp": "2026-12-10T23:59:59",
            "urgency": "Urgent",
            "authority": "Department of Agriculture, Govt of Karnataka & AIC",
            "portal_url": "https://samrakshane.karnataka.gov.in",
            "helpline": "14447 (Krishi Rakshak National Toll-Free)",
            "eligibility_rules": json.dumps([
                "Both loanee farmers (via PACS/KCC) and non-loanee farmers are eligible",
                "Land tenancy/cultivator agreement accepted for tenant farmers",
                "Must be registered in Samrakshane portal with verified Sowing Certificate",
                "Crop loss notification mandatory within 72 hours of inundation or hailstorm"
            ]),
            "checklist_template": json.dumps(STANDARD_DOCS),
        },
        {
            "category": "relief",
            "title": "Parihara Drought & Flood Input Subsidy Relief Application Window",
            "title_kannada": "ಪರಿಹಾರ ತಂತ್ರಾಂಶ: ಅತಿವೃಷ್ಟಿ ಹಾಗೂ ಬರ ಪರಿಹಾರ ಇನ್‌ಪುಟ್ ಸಬ್ಸಿಡಿ ಅರ್ಜಿ ಸಲ್ಲಿಕೆ",
            "summary": "State disaster management relief window for rainfed and irrigated crop losses exceeding 33%. Direct Benefit Transfer (DBT) of ₹8,500/ha for rainfed, ₹17,000/ha for assured irrigated, and ₹22,500/ha for perennial horticulture crops.",
            "summary_kannada": "ಬರ ಅಥವಾ ಪ್ರವಾಹದಿಂದ ಬೆಳೆ ಹಾನಿಯಾದ ರೈತರಿಗೆ ಹೆಕ್ಟೇರ್‌ಗೆ ₹8,500 ರಿಂದ ₹22,500 ನೇರ ಪರಿಹಾರ ಖಾತೆಗೆ ಜಮೆ.",
            "benefit_amount": "₹8,500 to ₹22,500 per hectare DBT",
            "deadline_date": "05 Dec 2026",
            "deadline_timestamp": "2026-12-05T23:59:59",
            "urgency": "Urgent",
            "authority": "Karnataka State Disaster Management Authority & Revenue Dept",
            "portal_url": "https://parihara.karnataka.gov.in",
            "helpline": "080-22032582",
            "eligibility_rules": json.dumps([
                "Farmer must be located in notified drought/flood taluks",
                "Crop loss percentage must exceed 33% during official joint survey",
                "Bank account must be Aadhaar-seeded on NPCI mapper to receive DBT",
                "Relief cap of maximum 2 hectares per eligible farming family"
            ]),
            "checklist_template": json.dumps(STANDARD_DOCS),
        },
    ]

    for notif in notifications_data:
        n_obj = models.Notification(**notif)
        db.add(n_obj)
        db.flush()

        # Seed initial checklist progress for this notification
        for doc in STANDARD_DOCS:
            # Mark Aadhaar and RTC completed by default as common farmer possession
            is_done = doc["key"] in ["aadhaar", "bhoomi_rtc"]
            prog = models.NotificationChecklistProgress(
                notification_id=n_obj.id,
                doc_key=doc["key"],
                doc_name=doc["name"],
                doc_name_kannada=doc["name_kannada"],
                is_completed=is_done,
            )
            db.add(prog)

    db.commit()


def seed_farm_ledger(db):
    if db.query(models.FarmLedgerEntry).count() > 0:
        return

    # Seed realistic 12-month ledger for a multi-crop farm in Karnataka (Shimoga / Hassan)
    # Growing Paddy (2 acres), Ginger (1 acre), Arecanut (2 acres) + Household Cashflow
    entries = [
        # January 2026
        {"entry_date": "2026-01-10", "crop_tag": "Paddy", "entry_type": "expense", "category": "cultivation", "sub_category": "Seeds & Nursery", "description": "High-yield Jaya & BPT-5204 certified paddy seeds", "amount": 4200.0, "notes": "Purchased from Raitha Samparka Kendra"},
        {"entry_date": "2026-01-18", "crop_tag": "Areca", "entry_type": "expense", "category": "irrigation", "sub_category": "Pump & Power", "description": "Drip emitter cleaning and 5HP pump starter repair", "amount": 3500.0, "notes": "Pre-summer irrigation maintenance"},
        {"entry_date": "2026-01-25", "crop_tag": "General/Household", "entry_type": "expense", "category": "household", "sub_category": "Family Living", "description": "Monthly grocery, milk, provisions & utility bill", "amount": 16500.0, "notes": "January household expenses"},
        {"entry_date": "2026-01-28", "crop_tag": "General/Household", "entry_type": "revenue", "category": "household", "sub_category": "Non-Farm Income", "description": "Dairy society milk payout & poultry egg sales", "amount": 22000.0, "notes": "Monthly dairy cooperative collection"},

        # February 2026
        {"entry_date": "2026-02-08", "crop_tag": "Paddy", "entry_type": "expense", "category": "cultivation", "sub_category": "Fertilizers", "description": "DAP (2 bags), Urea (3 bags) and Zinc Sulphate", "amount": 6800.0, "notes": "Primary basal fertilizer application"},
        {"entry_date": "2026-02-15", "crop_tag": "Paddy", "entry_type": "expense", "category": "cultivation", "sub_category": "Labor & Weeding", "description": "Manual weeding and bund dressing (6 laborers x 2 days)", "amount": 7200.0, "notes": "Hired farm workers"},
        {"entry_date": "2026-02-22", "crop_tag": "General/Household", "entry_type": "expense", "category": "household", "sub_category": "Family Living", "description": "Children school fees and medical checkup", "amount": 14500.0, "notes": "February household outlay"},
        {"entry_date": "2026-02-28", "crop_tag": "General/Household", "entry_type": "revenue", "category": "household", "sub_category": "Non-Farm Income", "description": "Monthly dairy milk collection proceeds", "amount": 21500.0, "notes": "Nandini society credit"},

        # March 2026
        {"entry_date": "2026-03-05", "crop_tag": "Ginger", "entry_type": "expense", "category": "cultivation", "sub_category": "Land Prep", "description": "Deep tractor ploughing and raised bed forming (1 Acre)", "amount": 8500.0, "notes": "Pre-planting Ginger land preparation"},
        {"entry_date": "2026-03-14", "crop_tag": "Paddy", "entry_type": "expense", "category": "irrigation", "sub_category": "Canal & Pumping", "description": "Diesel generator pumping during canal maintenance", "amount": 4800.0, "notes": "Critical flowering irrigation"},
        {"entry_date": "2026-03-22", "crop_tag": "Areca", "entry_type": "expense", "category": "cultivation", "sub_category": "Manure", "description": "Compost farmyard manure (4 tractor loads) for areca palms", "amount": 14000.0, "notes": "Annual organic nourishment"},
        {"entry_date": "2026-03-28", "crop_tag": "General/Household", "entry_type": "expense", "category": "household", "sub_category": "Family Living", "description": "Monthly living expenses and festival celebrations", "amount": 18000.0, "notes": "Ugadi festival & groceries"},
        {"entry_date": "2026-03-30", "crop_tag": "General/Household", "entry_type": "revenue", "category": "household", "sub_category": "Non-Farm Income", "description": "Dairy society milk payout", "amount": 23200.0, "notes": "March milk proceeds"},

        # April 2026
        {"entry_date": "2026-04-10", "crop_tag": "Ginger", "entry_type": "expense", "category": "cultivation", "sub_category": "Seed Rhizomes", "description": "Disease-free Maran/Rio-de-Janeiro ginger seed rhizomes (7 quintals)", "amount": 28000.0, "notes": "Certified seed rhizomes from Hassan growers"},
        {"entry_date": "2026-04-18", "crop_tag": "Paddy", "entry_type": "expense", "category": "harvest", "sub_category": "Combine Harvester", "description": "Custom combine harvester machine rental (2 acres)", "amount": 9000.0, "notes": "Summer crop mechanized harvest"},
        {"entry_date": "2026-04-20", "crop_tag": "Paddy", "entry_type": "expense", "category": "harvest", "sub_category": "Threshing & Transport", "description": "Gunny bags, tractor trolley haulage to Shimoga APMC", "amount": 4500.0, "notes": "Post-harvest transport"},
        {"entry_date": "2026-04-24", "crop_tag": "Paddy", "entry_type": "revenue", "category": "crop_sales", "sub_category": "APMC Sale", "description": "Sale of 48 quintals Grade-A Paddy @ ₹2,350/quintal", "amount": 112800.0, "notes": "Sold at Shimoga APMC mandi auction"},
        {"entry_date": "2026-04-28", "crop_tag": "General/Household", "entry_type": "expense", "category": "household", "sub_category": "Family Living", "description": "Family household provisions", "amount": 15000.0, "notes": "April living costs"},
        {"entry_date": "2026-04-30", "crop_tag": "General/Household", "entry_type": "revenue", "category": "household", "sub_category": "Non-Farm Income", "description": "Dairy society milk collection", "amount": 22400.0, "notes": "Monthly milk yield"},

        # May 2026
        {"entry_date": "2026-05-08", "crop_tag": "Ginger", "entry_type": "expense", "category": "cultivation", "sub_category": "Planting Labor", "description": "Seed rhizome treating and planting labour (12 work-days)", "amount": 9600.0, "notes": "Trichoderma bio-fungicide treatment"},
        {"entry_date": "2026-05-18", "crop_tag": "Areca", "entry_type": "expense", "category": "cultivation", "sub_category": "Bordeaux Spray", "description": "Copper sulphate + lime Bordeaux mixture for Koleroga prevention", "amount": 7800.0, "notes": "Pre-monsoon rot preventative spray"},
        {"entry_date": "2026-05-25", "crop_tag": "General/Household", "entry_type": "expense", "category": "household", "sub_category": "Family Living", "description": "Monthly family groceries and clothing", "amount": 16000.0, "notes": "May household expense"},
        {"entry_date": "2026-05-30", "crop_tag": "General/Household", "entry_type": "revenue", "category": "household", "sub_category": "Non-Farm Income", "description": "Dairy society milk proceeds", "amount": 21800.0, "notes": "Nandini milk payment"},

        # June 2026
        {"entry_date": "2026-06-12", "crop_tag": "Ginger", "entry_type": "expense", "category": "cultivation", "sub_category": "Mulching & Weeding", "description": "Green leaf mulching (first split) and manual weeding", "amount": 6200.0, "notes": "Crucial monsoon weed suppression"},
        {"entry_date": "2026-06-20", "crop_tag": "Areca", "entry_type": "expense", "category": "irrigation", "sub_category": "Drainage Trenches", "description": "Clearing inter-row rainwater drainage trenches", "amount": 4200.0, "notes": "Prevent waterlogging during heavy downpours"},
        {"entry_date": "2026-06-28", "crop_tag": "General/Household", "entry_type": "expense", "category": "household", "sub_category": "Family Living", "description": "School reopening books & uniform expenses", "amount": 19500.0, "notes": "Education and home grocery"},
        {"entry_date": "2026-06-30", "crop_tag": "General/Household", "entry_type": "revenue", "category": "household", "sub_category": "Non-Farm Income", "description": "Dairy society milk collection", "amount": 23000.0, "notes": "June dairy receipt"},

        # July 2026
        {"entry_date": "2026-07-10", "crop_tag": "Ginger", "entry_type": "expense", "category": "cultivation", "sub_category": "Bio-Fertilizer", "description": "Pseudomonas fluorescens & neem cake application", "amount": 5400.0, "notes": "Soil-borne bacterial wilt barrier"},
        {"entry_date": "2026-07-16", "crop_tag": "Areca", "entry_type": "expense", "category": "cultivation", "sub_category": "Second Spraying", "description": "Second round Bordeaux spraying on arecanut bunches", "amount": 8200.0, "notes": "Peak monsoon rot protection"},
        {"entry_date": "2026-07-28", "crop_tag": "General/Household", "entry_type": "expense", "category": "household", "sub_category": "Family Living", "description": "Monthly living expenses", "amount": 15500.0, "notes": "July provisions"},
        {"entry_date": "2026-07-31", "crop_tag": "General/Household", "entry_type": "revenue", "category": "household", "sub_category": "Non-Farm Income", "description": "Dairy milk payout", "amount": 22600.0, "notes": "Monthly milk income"},

        # August 2026
        {"entry_date": "2026-08-12", "crop_tag": "Ginger", "entry_type": "expense", "category": "cultivation", "sub_category": "Earthing Up", "description": "Second mulching and earthing up around ginger rhizomes", "amount": 7500.0, "notes": "Ensures rhizome expansion"},
        {"entry_date": "2026-08-20", "crop_tag": "Areca", "entry_type": "expense", "category": "cultivation", "sub_category": "Micronutrients", "description": "Borax and Zinc sulphate soil booster around palm root-zone", "amount": 4800.0, "notes": "Nut-dropping control"},
        {"entry_date": "2026-08-28", "crop_tag": "General/Household", "entry_type": "expense", "category": "household", "sub_category": "Family Living", "description": "Household expenses & festival preparation", "amount": 17200.0, "notes": "Gowri-Ganesha festival purchases"},
        {"entry_date": "2026-08-31", "crop_tag": "General/Household", "entry_type": "revenue", "category": "household", "sub_category": "Non-Farm Income", "description": "Dairy milk proceeds", "amount": 23500.0, "notes": "August milk proceeds"},

        # September 2026
        {"entry_date": "2026-09-08", "crop_tag": "Paddy", "entry_type": "expense", "category": "cultivation", "sub_category": "Kharif Inputs", "description": "Kharif paddy seed treatment & seedling nursery prep", "amount": 3800.0, "notes": "Short-duration autumn crop"},
        {"entry_date": "2026-09-18", "crop_tag": "Ginger", "entry_type": "expense", "category": "irrigation", "sub_category": "Micro-Sprinklers", "description": "Micro-sprinkler valve overhaul & filter flushing", "amount": 3200.0, "notes": "Post-monsoon dry spell preparation"},
        {"entry_date": "2026-09-28", "crop_tag": "General/Household", "entry_type": "expense", "category": "household", "sub_category": "Family Living", "description": "Monthly family groceries", "amount": 15800.0, "notes": "September living expenses"},
        {"entry_date": "2026-09-30", "crop_tag": "General/Household", "entry_type": "revenue", "category": "household", "sub_category": "Non-Farm Income", "description": "Dairy society milk collection", "amount": 22800.0, "notes": "September milk payout"},

        # October 2026
        {"entry_date": "2026-10-10", "crop_tag": "Areca", "entry_type": "expense", "category": "harvest", "sub_category": "Tree Climbing Labor", "description": "Skilled tree climbers for first harvest round (Chali & tender)", "amount": 16000.0, "notes": "4 climbers x 4 days"},
        {"entry_date": "2026-10-18", "crop_tag": "Areca", "entry_type": "expense", "category": "harvest", "sub_category": "De-husking & Drying", "description": "Manual de-husking labor, drying yard mats, sulfur chamber", "amount": 11500.0, "notes": "Initial drying processing"},
        {"entry_date": "2026-10-25", "crop_tag": "General/Household", "entry_type": "expense", "category": "household", "sub_category": "Family Living", "description": "Deepavali festival celebrations & family shopping", "amount": 21000.0, "notes": "Annual festival expenditure"},
        {"entry_date": "2026-10-30", "crop_tag": "General/Household", "entry_type": "revenue", "category": "household", "sub_category": "Non-Farm Income", "description": "Dairy society milk payout", "amount": 23100.0, "notes": "October milk receipts"},

        # November 2026
        {"entry_date": "2026-11-05", "crop_tag": "Areca", "entry_type": "expense", "category": "harvest", "sub_category": "Second Harvesting", "description": "Second harvest climbing, sorting and bagging", "amount": 14500.0, "notes": "Final bunch clearance"},
        {"entry_date": "2026-11-15", "crop_tag": "Areca", "entry_type": "revenue", "category": "crop_sales", "sub_category": "APMC Sale", "description": "Sale of 18 quintals White Chali Arecanut @ ₹45,200/quintal", "amount": 813600.0, "notes": "Sold at Sirsi & Shivamogga APMC auction"},
        {"entry_date": "2026-11-20", "crop_tag": "Ginger", "entry_type": "expense", "category": "harvest", "sub_category": "Digging Labor", "description": "Manual rhizome digging and sorting labor (10 laborers)", "amount": 12000.0, "notes": "Ginger maturity harvesting"},
        {"entry_date": "2026-11-24", "crop_tag": "Ginger", "entry_type": "revenue", "category": "crop_sales", "sub_category": "Mandi Sale", "description": "Sale of 85 quintals Fresh Green Ginger @ ₹5,100/quintal", "amount": 433500.0, "notes": "Sold directly to wholesale vegetable traders"},
        {"entry_date": "2026-11-26", "crop_tag": "General/Household", "entry_type": "expense", "category": "household", "sub_category": "Family Living", "description": "Monthly household grocery and provisions", "amount": 16000.0, "notes": "November living costs"},
        {"entry_date": "2026-11-28", "crop_tag": "General/Household", "entry_type": "revenue", "category": "household", "sub_category": "Non-Farm Income", "description": "Dairy society milk collection", "amount": 24000.0, "notes": "November milk yield"},
    ]

    for e in entries:
        db.add(models.FarmLedgerEntry(**e))

    db.commit()


def seed_alternative_crop_benchmarks(db):
    if db.query(models.AlternativeCropBenchmark).count() > 0:
        return

    benchmarks = [
        {
            "crop_name": "Ginger (Maran)",
            "crop_kannada": "ಶುಂಠಿ (ಮಾರಾನ್ ತಳಿ)",
            "suitable_soil_types": json.dumps(["Red Sandy Loam", "Laterite Soil", "Clay Loam"]),
            "min_temp_c": 18.0,
            "max_temp_c": 35.0,
            "water_demand_level": "Medium-High",
            "water_requirement_mm": "1200 - 1500 mm",
            "growth_duration_days": 240,
            "avg_cost_per_acre": 85000.0,
            "avg_yield_per_acre": "80 - 100 Quintals",
            "avg_gross_revenue_per_acre": 420000.0,
            "avg_net_profit_per_acre": 335000.0,
            "profit_ratio": 3.94,
            "roi_percent": 394.0,
            "risk_factor": "Medium (Rhizome Rot)",
            "advantages": "Exceptional ROI in shaded/intercropped groves; high mandi export liquidity."
        },
        {
            "crop_name": "Maize / Sweet Corn (Hybrid)",
            "crop_kannada": "ಮುಸುಕಿನ ಜೋಳ (ಹೈಬ್ರಿಡ್)",
            "suitable_soil_types": json.dumps(["Red Sandy Loam", "Black Cotton Soil", "Alluvial Soil"]),
            "min_temp_c": 18.0,
            "max_temp_c": 38.0,
            "water_demand_level": "Medium-Low",
            "water_requirement_mm": "500 - 650 mm",
            "growth_duration_days": 105,
            "avg_cost_per_acre": 24000.0,
            "avg_yield_per_acre": "32 - 38 Quintals",
            "avg_gross_revenue_per_acre": 78000.0,
            "avg_net_profit_per_acre": 54000.0,
            "profit_ratio": 2.25,
            "roi_percent": 225.0,
            "risk_factor": "Low (Fall Armyworm manageable)",
            "advantages": "Very short turnaround (100 days), low water requirement, assured MSP procurement."
        },
        {
            "crop_name": "Black Pepper (Panniyur-1)",
            "crop_kannada": "ಕಾಳುಮೆಣಸು (ಪನ್ನಿಯೂರು-1)",
            "suitable_soil_types": json.dumps(["Laterite Soil", "Red Sandy Loam"]),
            "min_temp_c": 16.0,
            "max_temp_c": 36.0,
            "water_demand_level": "Medium",
            "water_requirement_mm": "1500 - 2000 mm",
            "growth_duration_days": 365,
            "avg_cost_per_acre": 32000.0,
            "avg_yield_per_acre": "6 - 8 Quintals (Dry)",
            "avg_gross_revenue_per_acre": 360000.0,
            "avg_net_profit_per_acre": 328000.0,
            "profit_ratio": 10.25,
            "roi_percent": 1025.0,
            "risk_factor": "Medium (Quick Wilt)",
            "advantages": "Zero extra land footprint when trailed on Arecanut/Silver Oak trunks; premium global value."
        },
        {
            "crop_name": "Pigeon Pea / Tur Dal (BRG-4)",
            "crop_kannada": "ತೊಗರಿ ಬೇಳೆ (ಬಿಆರ್‌ಜಿ-4)",
            "suitable_soil_types": json.dumps(["Black Cotton Soil", "Red Sandy Loam", "Alluvial Soil"]),
            "min_temp_c": 16.0,
            "max_temp_c": 38.0,
            "water_demand_level": "Low (Drought Tolerant)",
            "water_requirement_mm": "400 - 550 mm",
            "growth_duration_days": 140,
            "avg_cost_per_acre": 16000.0,
            "avg_yield_per_acre": "10 - 12 Quintals",
            "avg_gross_revenue_per_acre": 78000.0,
            "avg_net_profit_per_acre": 62000.0,
            "profit_ratio": 3.88,
            "roi_percent": 388.0,
            "risk_factor": "Low",
            "advantages": "Fixes 40kg nitrogen/acre in soil naturally; thrives in semi-arid and low-rainfall spells."
        },
        {
            "crop_name": "Paddy (Semi-Dwarf BPT-5204)",
            "crop_kannada": "ಭತ್ತ (ಬಿಪಿಟಿ ಸೋನಾ ಮಸೂರಿ)",
            "suitable_soil_types": json.dumps(["Clay Loam", "Alluvial Soil", "Red Sandy Loam"]),
            "min_temp_c": 20.0,
            "max_temp_c": 36.0,
            "water_demand_level": "High (Flooded / AWD)",
            "water_requirement_mm": "1100 - 1400 mm",
            "growth_duration_days": 135,
            "avg_cost_per_acre": 28000.0,
            "avg_yield_per_acre": "24 - 28 Quintals",
            "avg_gross_revenue_per_acre": 62000.0,
            "avg_net_profit_per_acre": 34000.0,
            "profit_ratio": 1.21,
            "roi_percent": 121.0,
            "risk_factor": "Low-Medium (Blast & Stem Borer)",
            "advantages": "Staple food security, reliable local APMC procurement and straw byproduct for cattle feed."
        },
        {
            "crop_name": "Areca Nut (Chali Variety)",
            "crop_kannada": "ಅಡಿಕೆ (ಚಾಲಿ ತಳಿ)",
            "suitable_soil_types": json.dumps(["Laterite Soil", "Red Sandy Loam", "Clay Loam"]),
            "min_temp_c": 15.0,
            "max_temp_c": 37.0,
            "water_demand_level": "High (Regular Irrigation)",
            "water_requirement_mm": "1800 - 2400 mm",
            "growth_duration_days": 365,
            "avg_cost_per_acre": 68000.0,
            "avg_yield_per_acre": "14 - 18 Quintals",
            "avg_gross_revenue_per_acre": 680000.0,
            "avg_net_profit_per_acre": 612000.0,
            "profit_ratio": 9.0,
            "roi_percent": 900.0,
            "risk_factor": "Medium (Koleroga & Yellow Leaf Disease)",
            "advantages": "Perennial high-cash yield spanning 25+ productive years; strong cooperative auction support."
        },
    ]

    for b in benchmarks:
        db.add(models.AlternativeCropBenchmark(**b))

    db.commit()


# ============================================================================
# SPRINT 5 SEED FUNCTIONS (HELP DIRECTORY, VET DOCTORS, CATTLE & LIVESTOCK/PETS)
# ============================================================================

def seed_service_contacts(db):
    if db.query(models.ServiceContact).count() > 0:
        return

    contacts = [
        # 1. Agriculture Product Merchants & Buyers
        {
            "name": "Malnad Arecanut & Pepper Traders",
            "category": "Agriculture Product Merchants & Buyers",
            "phone": "+91 94481 24510",
            "location": "APMC Yard, Shivamogga",
            "notes": "Direct farm-gate procurement of Chali & Red arecanut, black pepper, and dry ginger with spot weighing.",
        },
        {
            "name": "Sri Basaveshwara Grain & Maize Buyers",
            "category": "Agriculture Product Merchants & Buyers",
            "phone": "+91 98452 67321",
            "location": "Davanagere APMC Road, Davanagere",
            "notes": "Bulk buyers of paddy, hybrid maize, and tur dal; arranges lorry pickup for orders above 30 quintals.",
        },
        # 2. Agricultural Machineries (Tractors, Harvesters, Tree Cutters)
        {
            "name": "Cauvery Custom Hiring & Combine Harvesters",
            "category": "Agricultural Machineries (Tractors, Harvesters, Tree Cutters)",
            "phone": "+91 99002 45198",
            "location": "Mandya – Maddur Main Road, Mandya",
            "notes": "4WD tractors with rotavator, chain-type paddy combine harvesters, and laser land levelers on hourly rental.",
        },
        {
            "name": "Sharavathi Tree Cutters & Farm Machinery Rental",
            "category": "Agricultural Machineries (Tractors, Harvesters, Tree Cutters)",
            "phone": "+91 94495 11284",
            "location": "Sagara, Shivamogga",
            "notes": "Stihl chainsaws, brush cutters, mini power tillers, and telescopic areca/coconut tree pruners.",
        },
        # 3. Pesticide Sprayermen
        {
            "name": "Nagaraj Malnad Areca & Pepper Spraying Team",
            "category": "Pesticide Sprayermen",
            "phone": "+91 97412 88904",
            "location": "Sirsi, Uttara Kannada",
            "notes": "Trained climbers & carbon-fiber pole sprayers for Bordeaux mixture spraying on tall arecanut palms.",
        },
        {
            "name": "Kaveri Agri Drone & Power Sprayer Services",
            "category": "Pesticide Sprayermen",
            "phone": "+91 96118 34092",
            "location": "Channarayapatna, Hassan",
            "notes": "DGCA-certified agri spraying drones (10L payload) and tractor-mounted boom sprayers for paddy and maize.",
        },
        # 4. Farm Work Contractors
        {
            "name": "Manjunatha Rural Farm Labour Group",
            "category": "Farm Work Contractors",
            "phone": "+91 99804 55312",
            "location": "Holenarasipura, Hassan",
            "notes": "15-member experienced team for paddy transplanting, ginger bed preparation, weeding, and harvest bagging.",
        },
        {
            "name": "Tungabhadra Plantation & Trenching Contractors",
            "category": "Farm Work Contractors",
            "phone": "+91 94483 77620",
            "location": "Koppa, Chikkamagaluru",
            "notes": "Contract teams for coconut/arecanut harvesting, bund repair, and monsoon drainage trench cleaning.",
        },
        # 5. Tree Planting Sketchers
        {
            "name": "Harish Layout & Pit Marking Specialist",
            "category": "Tree Planting Sketchers",
            "phone": "+91 98807 61423",
            "location": "Tiptur, Tumakuru",
            "notes": "Precision geometric row/square/triangular layout sketching for coconut, arecanut, mango, and silver oak.",
        },
        {
            "name": "Sahyadri Horticulture Survey & Sketchers",
            "category": "Tree Planting Sketchers",
            "phone": "+91 94809 32145",
            "location": "Puttur, Dakshina Kannada",
            "notes": "Contour-line marking on sloped Malnad estates for intercropping cocoa, pepper, and banana.",
        },
        # 6. Machine & Pump Set Mechanics
        {
            "name": "Ravi Submersible & Borewell Pump Works",
            "category": "Machine & Pump Set Mechanics",
            "phone": "+91 98441 90345",
            "location": "Tumakuru – Gubbi Gate, Tumakuru",
            "notes": "Motor rewinding, 5HP–15HP submersible pump lifting, bush/bearing overhaul, and Kirloskar diesel pump repair.",
        },
        {
            "name": "Vijayanagara Power Tiller & Chaff Cutter Garage",
            "category": "Machine & Pump Set Mechanics",
            "phone": "+91 99456 28710",
            "location": "Ranebennur, Haveri",
            "notes": "On-farm breakdown service for VST/Kubota power tillers, sprayers, brush cutters, and dairy chaff cutters.",
        },
        # 7. Electricians
        {
            "name": "Prakash Agri Starter & 3-Phase Line Electrician",
            "category": "Electricians",
            "phone": "+91 94489 65230",
            "location": "Kolar Town, Kolar",
            "notes": "Auto-starter panels, dry-run preventer relays, capacitor bank setup, and solar pump DC/AC wiring.",
        },
        {
            "name": "Mahesh Rural Motor & Shed Electricals",
            "category": "Electricians",
            "phone": "+91 98863 41209",
            "location": "Nanjangud, Mysuru",
            "notes": "Dairy shed lighting, electric milking machine earthing, and borewell phase-failure protector installation.",
        },
        # 8. Carpenters
        {
            "name": "Vishwakarma Agri Cart & Wooden Tool Works",
            "category": "Carpenters",
            "phone": "+91 97405 19822",
            "location": "Belagavi – Gokak Road, Belagavi",
            "notes": "Bullock cart wheel repair, wooden plough yokes, cattle manger troughs, and farm shed timber roofing.",
        },
        {
            "name": "Ganesh Timber & Farm Gate Carpentry",
            "category": "Carpenters",
            "phone": "+91 94492 38411",
            "location": "Thirthahalli, Shivamogga",
            "notes": "Custom drying-yard wooden racks, pepper ladder fabrication, and cattle shed partition doors.",
        },
        # 9. Pipe Connections & Water Jet Mounters
        {
            "name": "Kaveri Drip, Sprinkler & HDPE Pipeline Fitters",
            "category": "Pipe Connections & Water Jet Mounters",
            "phone": "+91 99164 70831",
            "location": "Arsikere, Hassan",
            "notes": "HDPE butt-fusion jointing, borewell column pipe lowering, venturi fertilizer injectors, and sprinkler jets.",
        },
        {
            "name": "Suhas Borewell Jet & Sub-Main Plumbing",
            "category": "Pipe Connections & Water Jet Mounters",
            "phone": "+91 98457 82340",
            "location": "Chikkaballapur",
            "notes": "High-pressure water jet mounters for areca/banana irrigation, filter cleaning, and air-release valves.",
        },
        # 10. Agricultural Products Shop Owners
        {
            "name": "Raitha Mitra Seeds, Fertilizers & Agro Centre",
            "category": "Agricultural Products Shop Owners",
            "phone": "+91 94480 99415",
            "location": "Near KSRTC Stand, Hassan",
            "notes": "Licensed dealer for IFFCO/MCF fertilizers, certified paddy & maize seeds, micronutrients, and bio-fungicides.",
        },
        {
            "name": "Annapoorneshwari Agro Inputs & Cattle Feed Depot",
            "category": "Agricultural Products Shop Owners",
            "phone": "+91 98802 14567",
            "location": "APMC Link Road, Hubballi",
            "notes": "Nandini Gold cattle feed, mineral mixtures, drip spares, tarpaulins, and knapsack battery sprayers.",
        },
    ]

    for c in contacts:
        db.add(models.ServiceContact(**c))
    db.commit()


def seed_vet_doctors(db):
    if db.query(models.VetDoctor).count() > 0:
        return

    doctors = [
        {
            "name": "Pashu Sanjeevini Mobile Veterinary Unit (Govt of Karnataka)",
            "doctor_type": "Veterinary Doctor",
            "specialization": "24x7 Mobile Emergency ICU, Calving Assistance, Bloat & Snakebite Treatment",
            "phone": "1962",
            "location": "All Karnataka Districts (Toll-Free Mobile Van)",
            "availability": "24/7 Emergency Toll-Free Dispatch",
            "emergency_available": True,
        },
        {
            "name": "Dr. Raghavendra Kulkarni (BVSc & AH)",
            "doctor_type": "Veterinary Doctor",
            "specialization": "Dairy Cattle Obstetrics, Mastitis Treatment & High-Yield Reproductive Health",
            "phone": "+91 94482 31094",
            "location": "Shivamogga Taluk Veterinary Hospital",
            "availability": "Mon–Sat 9:00 AM – 6:30 PM (On-call night emergencies)",
            "emergency_available": True,
        },
        {
            "name": "Dr. Kavitha Gowda (MVSc Veterinary Medicine)",
            "doctor_type": "Veterinary Doctor",
            "specialization": "FMD/HS Vaccination, Calf Scours, Tick Fever (Theileriosis) & Buffalo Care",
            "phone": "+91 98453 74128",
            "location": "Hassan – Channarayapatna Veterinary Polyclinic",
            "availability": "Mon–Sat 8:30 AM – 5:30 PM",
            "emergency_available": True,
        },
        {
            "name": "Dr. Basavaraj Patil (BVSc)",
            "doctor_type": "Veterinary Doctor",
            "specialization": "Murrah Buffalo Infertility, Rumen Surgery & Mineral Deficiency Protocols",
            "phone": "+91 99005 62819",
            "location": "Belagavi – Bailhongal Road",
            "availability": "Daily 9:00 AM – 7:00 PM",
            "emergency_available": False,
        },
        {
            "name": "Shivanna Gowda (Senior Paravet & AI Specialist)",
            "doctor_type": "Local Cow Doctor",
            "specialization": "Artificial Insemination (Sexed Semen), Pregnancy Diagnosis & Deworming",
            "phone": "+91 97415 48902",
            "location": "Maddur, Mandya",
            "availability": "Daily 6:00 AM – 8:00 PM (Farm visits within 25 km)",
            "emergency_available": True,
        },
        {
            "name": "Puttaraju Shetty (Experienced Local Cow Doctor)",
            "doctor_type": "Local Cow Doctor",
            "specialization": "Bloat / Tympany Relief, Hoof Trimming, Retained Placenta First Aid & Herbal Care",
            "phone": "+91 94491 53760",
            "location": "Sirsi, Uttara Kannada",
            "availability": "Daily 6:30 AM – 7:30 PM",
            "emergency_available": True,
        },
        {
            "name": "Nanjundaswamy K. (MPCS Dairy Paravet)",
            "doctor_type": "Local Cow Doctor",
            "specialization": "Routine Vaccination, Milk Fever Calcium Drip & Udder Hygiene Management",
            "phone": "+91 98809 21654",
            "location": "Gubbi, Tumakuru",
            "availability": "Mon–Sun 7:00 AM – 6:00 PM",
            "emergency_available": False,
        },
        {
            "name": "Mallikarjunappa H. (Local Livestock Healer & AI Tech)",
            "doctor_type": "Local Cow Doctor",
            "specialization": "Hallikar & Native Cow Care, Heat Detection & Goat/Sheep Vaccination",
            "phone": "+91 96114 89230",
            "location": "Hunsur, Mysuru",
            "availability": "Daily 7:00 AM – 5:30 PM",
            "emergency_available": False,
        },
    ]

    for d in doctors:
        db.add(models.VetDoctor(**d))
    db.commit()


def seed_cattle_listings(db):
    if db.query(models.CattleListing).count() > 0:
        return

    listings = [
        {
            "title": "High-Yield HF Crossbred Cow (2nd Lactation, Female Calf)",
            "breed": "HF Cross",
            "animal_type": "Cow",
            "price_inr": 76000.0,
            "milk_yield_liters_per_day": 21.5,
            "age_years": 4.5,
            "location": "Channarayapatna, Hassan",
            "owner_name": "Ramesh Gowda",
            "owner_phone": "+91 98451 23890",
            "description": "Calved 25 days ago with healthy female calf. Calm temperament, machine-milking trained, vaccinated against FMD & HS.",
        },
        {
            "title": "Pure Murrah Buffalo — High 7.6% Fat Milk Yielder",
            "breed": "Murrah Buffalo",
            "animal_type": "Buffalo",
            "price_inr": 95000.0,
            "milk_yield_liters_per_day": 14.5,
            "age_years": 5.0,
            "location": "Gokak, Belagavi",
            "owner_name": "Mallappa Angadi",
            "owner_phone": "+91 94484 71205",
            "description": "Jet-black Murrah buffalo in 2nd lactation giving 14.5L/day rich milk fetching ₹62/L at Nandini society.",
        },
        {
            "title": "Authentic Malnad Gidda Cow (A2 Milk, Hardy Native Breed)",
            "breed": "Malnad Gidda",
            "animal_type": "Cow",
            "price_inr": 32000.0,
            "milk_yield_liters_per_day": 4.0,
            "age_years": 4.0,
            "location": "Sirsi, Uttara Kannada",
            "owner_name": "Ganapathi Hegde",
            "owner_phone": "+91 94498 12045",
            "description": "Zero-maintenance indigenous Malnad Gidda adapted to heavy coastal/Malnad rain; high-immunity A2 milk.",
        },
        {
            "title": "Jersey Crossbred Dairy Cow (4.6% Fat, 1st Lactation)",
            "breed": "Jersey",
            "animal_type": "Cow",
            "price_inr": 58000.0,
            "milk_yield_liters_per_day": 15.0,
            "age_years": 3.5,
            "location": "Devanahalli, Bengaluru Rural",
            "owner_name": "Venkatesh Murthy",
            "owner_phone": "+91 99001 66742",
            "description": "Compact heat-tolerant Jersey crossbred cow consuming moderate fodder with steady 15L daily milk output.",
        },
        {
            "title": "Purebred Gir Cow with Male Calf (Saurashtra Lineage)",
            "breed": "Gir",
            "animal_type": "Cow",
            "price_inr": 84000.0,
            "milk_yield_liters_per_day": 12.5,
            "age_years": 4.5,
            "location": "Dharwad Rural, Dharwad",
            "owner_name": "Prashant Deshpande",
            "owner_phone": "+91 98443 51908",
            "description": "Docile pure Gir cow with curved horns and pendulous ears; yields rich golden A2 milk suitable for ghee production.",
        },
        {
            "title": "Karnataka Hallikar Cow (Traditional Amritmahal/Hallikar Stock)",
            "breed": "Hallikar",
            "animal_type": "Cow",
            "price_inr": 54000.0,
            "milk_yield_liters_per_day": 5.5,
            "age_years": 4.0,
            "location": "Maddur, Mandya",
            "owner_name": "Kempegowda S.",
            "owner_phone": "+91 97420 88314",
            "description": "Well-proportioned Hallikar cow prized for disease resistance, drought hardiness, and strong calf progeny.",
        },
        {
            "title": "Pregnant HF Cross Heifer (8 Months Pregnant, Sexed Semen)",
            "breed": "HF Cross",
            "animal_type": "Heifer",
            "price_inr": 62000.0,
            "milk_yield_liters_per_day": 0.0,
            "age_years": 2.2,
            "location": "Kolar – Mulbagal Road, Kolar",
            "owner_name": "Narayanaswamy R.",
            "owner_phone": "+91 99807 43122",
            "description": "Healthy first-calving heifer inseminated with ABS sexed semen; expected delivery in 4 weeks.",
        },
        {
            "title": "Jersey Crossbred Heifer (7 Months Pregnant)",
            "breed": "Jersey",
            "animal_type": "Heifer",
            "price_inr": 45000.0,
            "milk_yield_liters_per_day": 0.0,
            "age_years": 2.0,
            "location": "Nanjangud, Mysuru",
            "owner_name": "Siddaraju M.",
            "owner_phone": "+91 96112 90876",
            "description": "Strong-framed Jersey cross heifer from a 17L/day dam; dewormed and vaccinated.",
        },
        {
            "title": "Murrah Buffalo Female Calf (9 Months Old, Pedigree Sire)",
            "breed": "Murrah Buffalo",
            "animal_type": "Calf",
            "price_inr": 24000.0,
            "milk_yield_liters_per_day": 0.0,
            "age_years": 0.8,
            "location": "Bagalkote Town, Bagalkote",
            "owner_name": "Shivanand Meti",
            "owner_phone": "+91 94487 65432",
            "description": "Well-nourished female Murrah calf from a 16L/day mother; ideal future dairy replacement stock.",
        },
        {
            "title": "Gir Female Calf (6 Months Old, Vaccinated)",
            "breed": "Gir",
            "animal_type": "Calf",
            "price_inr": 26500.0,
            "milk_yield_liters_per_day": 0.0,
            "age_years": 0.5,
            "location": "Tiptur, Tumakuru",
            "owner_name": "Shivakumar B.",
            "owner_phone": "+91 98804 71829",
            "description": "Healthy red-speckled Gir heifer calf raised on natural grazing and mother's milk.",
        },
    ]

    for item in listings:
        db.add(models.CattleListing(**item))
    db.commit()


def seed_livestock_pet_listings(db):
    if db.query(models.LivestockPetListing).count() > 0:
        return

    listings = [
        # Poultry
        {
            "title": "Pure Naati Koli (Desi Country Chicken) Breeding Flock",
            "category": "Poultry",
            "breed_or_type": "Naati Koli",
            "quantity": 15,
            "age": "6 months",
            "price_inr": 7500.0,
            "location": "Malavalli, Mandya",
            "owner_name": "Chikkanna Gowda",
            "owner_phone": "+91 98456 33219",
            "description": "Free-range desi hens and 2 roosters vaccinated against Ranikhet; great for backyard egg & meat income.",
        },
        {
            "title": "Giriraja & Swarnadhara Dual-Purpose Poultry Chicks",
            "category": "Poultry",
            "breed_or_type": "Giriraja",
            "quantity": 25,
            "age": "4 weeks",
            "price_inr": 3500.0,
            "location": "Hessarghatta, Bengaluru Rural",
            "owner_name": "Anand Kumar",
            "owner_phone": "+91 99008 44120",
            "description": "Brooded 1-month-old Giriraja chicks from university-certified hatchery stock; hardy and fast growing.",
        },
        {
            "title": "Khaki Campbell Layer Ducks (High Egg-Laying Batch)",
            "category": "Poultry",
            "breed_or_type": "Ducks (Khaki Campbell)",
            "quantity": 10,
            "age": "5 months",
            "price_inr": 4800.0,
            "location": "Kundapura, Udupi",
            "owner_name": "Sudhakar Poojary",
            "owner_phone": "+91 94485 21908",
            "description": "Ideal for coastal paddy fields and farm ponds; pest-foraging ducks laying up to 280 eggs/year.",
        },
        # Goats & Sheep
        {
            "title": "Osmanabadi Goat Breeding Pair (1 Buck + 2 Pregnant Does)",
            "category": "Goats & Sheep",
            "breed_or_type": "Osmanabadi Goat",
            "quantity": 3,
            "age": "1.5 years",
            "price_inr": 34000.0,
            "location": "Vijayapura Rural, Vijayapura",
            "owner_name": "Basappa Biradar",
            "owner_phone": "+91 97419 50284",
            "description": "Twin-bearing Osmanabadi goats suited for stall-fed and semi-intensive dryland goat farming.",
        },
        {
            "title": "Pure Bannur (Mandya) Sheep Pair — Premium Meat Lineage",
            "category": "Goats & Sheep",
            "breed_or_type": "Bannur Sheep",
            "quantity": 2,
            "age": "1 year",
            "price_inr": 26000.0,
            "location": "Bannur, Mysuru",
            "owner_name": "Mahadevaiah K.",
            "owner_phone": "+91 98805 64310",
            "description": "Short-legged compact Bannur ram and ewe with high dressing percentage; PPR & ET vaccinated.",
        },
        # Pets
        {
            "title": "Mudhol Hound Puppies (Traditional North Karnataka Lineage)",
            "category": "Pets",
            "breed_or_type": "Mudhol Hound",
            "quantity": 2,
            "age": "2 months",
            "price_inr": 14000.0,
            "location": "Mudhol, Bagalkote",
            "owner_name": "Hanumanth Desai",
            "owner_phone": "+91 94481 77539",
            "description": "Alert, loyal farm guard & companion Mudhol Hound puppies (male & female); first deworming and Parvo shot done.",
        },
        {
            "title": "Indian Pariah (Desi Guard) Puppies — Healthy & Vaccinated",
            "category": "Pets",
            "breed_or_type": "Indian Pariah Puppies",
            "quantity": 3,
            "age": "7 weeks",
            "price_inr": 1500.0,
            "location": "Bhadravathi, Shivamogga",
            "owner_name": "Lakshmi Narayana",
            "owner_phone": "+91 96119 38274",
            "description": "Intelligent, zero-maintenance native farm guard puppies accustomed to cattle sheds and rural outdoors.",
        },
        {
            "title": "New Zealand White & Grey Giant Farm Rabbits",
            "category": "Pets",
            "breed_or_type": "Rabbits",
            "quantity": 4,
            "age": "3 months",
            "price_inr": 2400.0,
            "location": "Belur, Hassan",
            "owner_name": "Praveen Shetty",
            "owner_phone": "+91 99452 10938",
            "description": "2 breeding pairs raised on lucerne, carrot tops, and clean pellet feed; calm and easy to house.",
        },
        # Domestic Animals
        {
            "title": "Trained Hallikar Ploughing Bullock Pair (matched pair)",
            "category": "Domestic Animals",
            "breed_or_type": "Hallikar Working Bullocks",
            "quantity": 2,
            "age": "4 years",
            "price_inr": 115000.0,
            "location": "Arsikere, Hassan",
            "owner_name": "Thimme Gowda",
            "owner_phone": "+91 98448 61207",
            "description": "Well-matched pair of trained Hallikar draft bullocks for ploughing, carting, and inter-row cultivation.",
        },
        {
            "title": "Farm Guard Geese & Domestic Watch Pair (White Embden)",
            "category": "Domestic Animals",
            "breed_or_type": "Domestic Farm Geese",
            "quantity": 2,
            "age": "8 months",
            "price_inr": 5200.0,
            "location": "Sakleshpur, Hassan",
            "owner_name": "Pramod Alva",
            "owner_phone": "+91 94490 73812",
            "description": "Natural orchard weeders and vocal farm-perimeter guards that deter snakes and stray intruders.",
        },
    ]

    for item in listings:
        db.add(models.LivestockPetListing(**item))
    db.commit()


def seed_wealth_plan_profile(db):
    if db.query(models.WealthPlanProfile).count() > 0:
        return

    # Compute live farm net profit from seeded ledger entries
    entries = db.query(models.FarmLedgerEntry).all()
    farm_cost = sum(
        e.amount for e in entries if e.category in ("cultivation", "irrigation", "harvest")
    )
    crop_rev = sum(e.amount for e in entries if e.category == "crop_sales")
    net_profit = round(crop_rev - farm_cost, 2)

    profile = models.WealthPlanProfile(
        net_profit=net_profit if net_profit > 0 else 450000.0,
        household_reserve=180000.0,
        next_cultivation_reserve=120000.0,
        harvest_reserve=65000.0,
        other_reserve=35000.0,
        life_commitments=["child_education", "emergency_medical", "land_tractor"],
    )
    db.add(profile)
    db.commit()


def seed():
    db = SessionLocal()
    try:
        seed_commodities(db)
        seed_cross_mandi_prices(db)
        seed_two_week_history(db)
        seed_seasonal_prices(db)
        seed_news_articles(db)
        seed_dairy_module(db)
        seed_notifications(db)
        seed_farm_ledger(db)
        seed_alternative_crop_benchmarks(db)
        seed_service_contacts(db)
        seed_vet_doctors(db)
        seed_cattle_listings(db)
        seed_livestock_pet_listings(db)
        seed_wealth_plan_profile(db)
        print("✅ Farm Advisor Sprint 1, 2, 3 & 5 database successfully seeded!")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
