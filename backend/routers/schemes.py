"""
State-Aware Scheme, Subsidy, Insurance & Relief Alerts Router.
Provides dynamic, localized agricultural scheme and relief alerts based on
the user's selected state, district, location_name, category, and language,
with SQLite TTL caching keyed by (state, language).
"""
import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/schemes", tags=["schemes"])

CACHE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "farm_advisor.db")
CACHE_TTL_SECONDS = 6 * 3600  # 6 hours

# Map city / district / location_name keywords to canonical Indian state names
LOCATION_TO_STATE: Dict[str, str] = {
    "bengaluru": "Karnataka",
    "bangalore": "Karnataka",
    "mysuru": "Karnataka",
    "mysore": "Karnataka",
    "shivamogga": "Karnataka",
    "davanagere": "Karnataka",
    "hassan": "Karnataka",
    "belagavi": "Karnataka",
    "dharwad": "Karnataka",
    "kalaburagi": "Karnataka",
    "mangaluru": "Karnataka",
    "tumakuru": "Karnataka",
    "mandya": "Karnataka",
    "chikkamagaluru": "Karnataka",
    "ballari": "Karnataka",
    "raichur": "Karnataka",
    "kolar": "Karnataka",
    "udupi": "Karnataka",
    "indore": "Madhya Pradesh",
    "bhopal": "Madhya Pradesh",
    "ujjain": "Madhya Pradesh",
    "jabalpur": "Madhya Pradesh",
    "gwalior": "Madhya Pradesh",
    "hyderabad": "Telangana",
    "warangal": "Telangana",
    "nizamabad": "Telangana",
    "karimnagar": "Telangana",
    "rangareddy": "Telangana",
    "pune": "Maharashtra",
    "nashik": "Maharashtra",
    "nagpur": "Maharashtra",
    "mumbai": "Maharashtra",
    "aurangabad": "Maharashtra",
    "kolhapur": "Maharashtra",
    "ahmedabad": "Gujarat",
    "surat": "Gujarat",
    "rajkot": "Gujarat",
    "vadodara": "Gujarat",
    "ludhiana": "Punjab",
    "amritsar": "Punjab",
    "jalandhar": "Punjab",
    "patiala": "Punjab",
    "karnal": "Haryana",
    "hisar": "Haryana",
    "lucknow": "Uttar Pradesh",
    "varanasi": "Uttar Pradesh",
    "kanpur": "Uttar Pradesh",
    "agra": "Uttar Pradesh",
    "meerut": "Uttar Pradesh",
    "coimbatore": "Tamil Nadu",
    "chennai": "Tamil Nadu",
    "madurai": "Tamil Nadu",
    "thanjavur": "Tamil Nadu",
    "guntur": "Andhra Pradesh",
    "vijayawada": "Andhra Pradesh",
    "visakhapatnam": "Andhra Pradesh",
    "kurnool": "Andhra Pradesh",
    "jaipur": "Rajasthan",
    "jodhpur": "Rajasthan",
    "udaipur": "Rajasthan",
    "kota": "Rajasthan",
    "thrissur": "Kerala",
    "kochi": "Kerala",
    "kolkata": "West Bengal",
    "hooghly": "West Bengal",
    "patna": "Bihar",
    "cuttack": "Odisha",
}

STATE_LAND_DOCS: Dict[str, str] = {
    "Karnataka": "Bhoomi RTC / Pahani",
    "Maharashtra": "7/12 Extract (Satbara) & 8A",
    "Madhya Pradesh": "Khasra / B1 Khatauni",
    "Uttar Pradesh": "e-Khasra / Khatauni (B1)",
    "Andhra Pradesh": "Adangal / 1B Land Record",
    "Telangana": "Dharani Passbook / Adangal 1B",
    "Tamil Nadu": "Chitta / Adangal Extract",
    "Gujarat": "7/12 & 8A Land Record (AnyROR)",
    "Punjab": "Jamabandi / Fard Land Record",
    "Haryana": "Jamabandi / Fard Land Record",
    "Rajasthan": "Apna Khata Jamabandi / Khasra",
}

LANGUAGE_PREFIXES: Dict[str, str] = {
    "en": "en",
    "hi": "hi",
    "kn": "kn",
    "te": "te",
    "ta": "ta",
    "mr": "mr",
    "ml": "ml",
    "bn": "bn",
    "gu": "gu",
    "pa": "pa",
}

LOCALIZED_SUBTITLES: Dict[str, str] = {
    "en": "Schemes, Subsidies & Relief Alerts",
    "hi": "योजनाएं, सब्सिडी और राहत अलर्ट",
    "kn": "ಯೋಜನೆ, ಸಬ್ಸಿಡಿ ಮತ್ತು ಪರಿಹಾರ ಅಧಿಸೂಚನೆಗಳು",
    "te": "పథకాలు, సబ్సిడీలు & సహాయక హెచ్చరికలు",
    "ta": "திட்டங்கள், மானியங்கள் & நிவாரண அறிவிப்புகள்",
    "mr": "योजना, अनुदान आणि मदत सूचना",
    "ml": "പദ്ധതികൾ, സബ്സിഡികൾ & ദുരിതാശ്വാസ അറിയിപ്പുകൾ",
    "bn": "প্রকল্প, ভর্তুকি ও ত্রাণ সতর্কতা",
    "gu": "યોજનાઓ, સબસિડી અને રાહત ચેતવણીઓ",
    "pa": "ਸਕੀਮਾਂ, ਸਬਸਿਡੀਆਂ ਅਤੇ ਰਾਹਤ ਅਲਰਟ",
}


def _normalize_lang(language: str) -> str:
    if not language:
        return "en"
    short = language.split("-")[0].lower().strip()
    return LANGUAGE_PREFIXES.get(short, "en")


def normalize_state(state: Optional[str], location_name: Optional[str]) -> str:
    if state and state.strip():
        return state.strip()
    if location_name:
        loc_lower = location_name.lower()
        for keyword, mapped_state in LOCATION_TO_STATE.items():
            if keyword in loc_lower:
                return mapped_state
    return "Karnataka"


def _deadline_str(days_left: int) -> str:
    target = datetime.utcnow() + timedelta(days=days_left)
    return target.strftime("%Y-%m-%d")


def _init_cache_table() -> None:
    try:
        conn = sqlite3.connect(CACHE_DB_PATH)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scheme_alerts_cache (
                cache_key TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _get_cached(state: str, lang: str) -> Optional[List[Dict[str, Any]]]:
    _init_cache_table()
    key = f"{state.lower()}::{lang}"
    try:
        conn = sqlite3.connect(CACHE_DB_PATH)
        row = conn.execute(
            "SELECT payload_json, created_at FROM scheme_alerts_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
        conn.close()
        if row:
            payload_json, created_at = row
            if (time.time() - created_at) < CACHE_TTL_SECONDS:
                return json.loads(payload_json)
    except Exception:
        pass
    return None


def _set_cached(state: str, lang: str, items: List[Dict[str, Any]]) -> None:
    _init_cache_table()
    key = f"{state.lower()}::{lang}"
    try:
        conn = sqlite3.connect(CACHE_DB_PATH)
        conn.execute(
            """
            INSERT OR REPLACE INTO scheme_alerts_cache (cache_key, payload_json, created_at)
            VALUES (?, ?, ?)
            """,
            (key, json.dumps(items, ensure_ascii=False), time.time()),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _build_central_schemes(state: str, land_doc: str, lang: str) -> List[Dict[str, Any]]:
    return [
        {
            "id": f"central-pmfby-{state.lower().replace(' ', '-')}",
            "category": "insurance",
            "days_left": 18,
            "title": f"PMFBY Rabi 2026-27 Crop Insurance ({state})",
            "localized_title": (
                "प्रधानमंत्री फसल बीमा योजना (रबी 2026-27)" if lang == "hi"
                else "ಪ್ರಧಾನ ಮಂತ್ರಿ ಫಸಲ್ ಬಿಮಾ ಯೋಜನೆ (ರಬಿ 2026-27)" if lang == "kn"
                else "ప్రధాన మంత్రి ఫసల్ బీమా యోజన (రబీ 2026-27)" if lang == "te"
                else "பிரதமர் பயிர் காப்பீட்டுத் திட்டம் (ரபி 2026-27)" if lang == "ta"
                else "प्रधानमंत्री पीक विमा योजना (रब्बी 2026-27)" if lang == "mr"
                else f"PMFBY Rabi 2026-27 Crop Insurance ({state})"
            ),
            "description": f"Enroll Rabi crops against unseasonal rain, hailstorm & yield loss in {state}. Call KRPH helpline 14447 for claim status.",
            "benefit": "Up to ₹50,000/ha coverage (1.5% Rabi farmer premium)",
            "deadline": _deadline_str(18),
            "documents_required": ["Aadhaar Card", land_doc, "Bank Passbook", "Sowing Certificate"],
            "portal_url": "https://pmfby.gov.in/",
            "authority": f"Ministry of Agriculture & {state} Agri Dept",
            "helpline": "14447 (KRPH)",
            "urgency": "high",
        },
        {
            "id": "central-pm-kisan",
            "category": "subsidies",
            "days_left": 25,
            "title": "PM-KISAN 19th Installment e-KYC & DBT Verification",
            "localized_title": (
                "पीएम-किसान ई-केवाईसी और डीबीटी सत्यापन" if lang == "hi"
                else "ಪಿಎಂ-ಕಿಸಾನ್ ಇ-ಕೆವೈಸಿ ಮತ್ತು ಡಿಬಿಟಿ ಪರಿಶೀಲನೆ" if lang == "kn"
                else "పిఎం-కిసాన్ ఇ-కెవైసి & డిబిటి ధృవీకరణ" if lang == "te"
                else "பிஎம்-கிசான் இ-கேஒய்சி & டிபிடி சரிபார்ப்பு" if lang == "ta"
                else "पीएम-किसान ई-केवायसी व डीबीटी पडताळणी" if lang == "mr"
                else "PM-KISAN e-KYC & DBT Verification"
            ),
            "description": "Complete mandatory Aadhaar e-KYC and land seeding to receive ₹2,000 DBT installment without interruption.",
            "benefit": "₹6,000 / year (₹2,000 per installment)",
            "deadline": _deadline_str(25),
            "documents_required": ["Aadhaar Card", land_doc, "Aadhaar-linked Bank Account"],
            "portal_url": "https://pmkisan.gov.in/",
            "authority": "Department of Agriculture & Farmers Welfare",
            "helpline": "155261 / 011-24300606",
            "urgency": "medium",
        },
        {
            "id": "central-pm-kusum",
            "category": "subsidies",
            "days_left": 32,
            "title": "PM-KUSUM Solar Pump & Grid-Connected Subsidy",
            "localized_title": (
                "पीएम-कुसुम सोलर पंप सब्सिडी" if lang == "hi"
                else "ಪಿಎಂ-ಕುಸುಮ್ ಸೋಲಾರ್ ಪಂಪ್ ಸಬ್ಸಿಡಿ" if lang == "kn"
                else "పిఎం-కుసుమ్ సోలార్ పంప్ సబ్సిడి" if lang == "te"
                else "பிஎம்-குசும் சூரிய சக்தி பம்ப் மானியம்" if lang == "ta"
                else "पीएम-कुसुम सौर पंप अनुदान" if lang == "mr"
                else "PM-KUSUM Solar Pump Subsidy"
            ),
            "description": f"Apply for 3HP to 7.5HP standalone solar agricultural pumps with up to 60% central + {state} state subsidy.",
            "benefit": "60% Subsidy + 30% Bank Loan",
            "deadline": _deadline_str(32),
            "documents_required": ["Aadhaar Card", land_doc, "Water Source Proof", "Bank Passbook"],
            "portal_url": "https://pmkusum.mnre.gov.in/",
            "authority": "MNRE & State Renewable Energy Agency",
            "helpline": "1800-180-3333",
            "urgency": "medium",
        },
        {
            "id": "central-icar-fellowship",
            "category": "fellowships",
            "days_left": 29,
            "title": f"ICAR-JRF/SRF & {state} Agri Skill Fellowship",
            "localized_title": (
                "आईसीएआर कृषि अनुसंधान और प्रशिक्षण फेलोशिप" if lang == "hi"
                else "ಐಸಿಎಆರ್ ಕೃಷಿ ಸಂಶೋಧನೆ ಮತ್ತು ತರಬೇತಿ ಫೆಲೋಶಿಪ್" if lang == "kn"
                else "ఐసిఎఆర్ వ్యవసాయ పరిశోధన & శిక్షణ ఫెలోషిప్" if lang == "te"
                else "ஐசிஏஆர் வேளாண் ஆராய்ச்சி & பயிற்சி உதவித்தொகை" if lang == "ta"
                else "आयसीएआर कृषी संशोधन व प्रशिक्षण फेलोशिप" if lang == "mr"
                else f"ICAR-JRF/SRF & {state} Agri Skill Fellowship"
            ),
            "description": f"Stipendiary fellowship & KVK precision farming training for young farmers and agri graduates in {state}.",
            "benefit": "₹12,000 - ₹31,000/month stipend",
            "deadline": _deadline_str(29),
            "documents_required": ["Aadhaar Card", "Educational / KVK Certificate", "Bank Passbook"],
            "portal_url": "https://icar.org.in/",
            "authority": "Indian Council of Agricultural Research (ICAR)",
            "helpline": "011-25843301",
            "urgency": "low",
        },
    ]


def _build_state_schemes(state: str, district: str, land_doc: str, lang: str) -> List[Dict[str, Any]]:
    dist_note = f" ({district} district)" if district else ""

    if state == "Karnataka":
        return [
            {
                "id": "ka-parihara",
                "category": "drought",
                "days_left": 11,
                "title": f"Karnataka Parihara Drought & Flood Input Subsidy{dist_note}",
                "localized_title": "ಕರ್ನಾಟಕ ಪರಿಹಾರ ಬರ ಮತ್ತು ಪ್ರವಾಹ ಬೆಳೆ ನಷ್ಟ ಪರಿಹಾರ" if lang == "kn" else "Karnataka Parihara Drought & Flood Input Subsidy",
                "description": "Direct Benefit Transfer (DBT) compensation for Kharif/Rabi crop loss due to drought or excess rainfall via Parihara portal.",
                "benefit": "₹8,500 - ₹22,500 / hectare",
                "deadline": _deadline_str(11),
                "documents_required": ["Aadhaar Card", "Bhoomi RTC / Pahani", "Bank Passbook", "Crop Loss Panchanama"],
                "portal_url": "https://parihara.karnataka.gov.in/",
                "authority": "Revenue & Agriculture Dept, Govt of Karnataka",
                "helpline": "1800-425-3553",
                "urgency": "high",
            },
            {
                "id": "ka-raitha-siri-krishi-bhagya",
                "category": "subsidies",
                "days_left": 21,
                "title": "Raitha Siri, Krishi Bhagya & Ganga Kalyana Subsidies",
                "localized_title": "ರೈತ ಸಿರಿ, ಕೃಷಿ ಭಾಗ್ಯ ಮತ್ತು ಗಂಗಾ ಕಲ್ಯಾಣ ಸಬ್ಸಿಡಿ" if lang == "kn" else "Raitha Siri, Krishi Bhagya & Ganga Kalyana Subsidies",
                "description": "Up to 90% subsidy for micro-irrigation, farm ponds (Krishi Honda), millet cultivation (₹10,000/ha), and borewell energization.",
                "benefit": "Up to ₹1,50,000 / 90% Subsidy",
                "deadline": _deadline_str(21),
                "documents_required": ["Aadhaar Card", "Bhoomi RTC / Pahani", "FRUITS ID", "Caste/Income Cert (if applicable)"],
                "portal_url": "https://raitamitra.karnataka.gov.in/",
                "authority": "Karnataka State Department of Agriculture",
                "helpline": "1800-425-3553",
                "urgency": "medium",
            },
            {
                "id": "ka-samrakshane",
                "category": "insurance",
                "days_left": 15,
                "title": "Karnataka Samrakshane PMFBY Crop Insurance Portal",
                "localized_title": "ಕರ್ನಾಟಕ ಸಂರಕ್ಷಣೆ ಬೆಳೆ ವಿಮೆ ಯೋಜನೆ" if lang == "kn" else "Karnataka Samrakshane PMFBY Crop Insurance",
                "description": "Verify FRUITS ID and enroll notified horticulture & field crops on Samrakshane portal before cutoff.",
                "benefit": "100% Sum Insured on notified crop loss",
                "deadline": _deadline_str(15),
                "documents_required": ["FRUITS ID", "Bhoomi RTC / Pahani", "Sowing Declaration", "Bank Passbook"],
                "portal_url": "https://samrakshane.karnataka.gov.in/",
                "authority": "Karnataka Crop Insurance Cell",
                "helpline": "1800-425-3553",
                "urgency": "high",
            },
        ]

    if state == "Madhya Pradesh":
        return [
            {
                "id": "mp-cmkky",
                "category": "subsidies",
                "days_left": 14,
                "title": f"Mukhyamantri Kisan Kalyan Yojana (CMKKY) Top-Up DBT{dist_note}",
                "localized_title": "मुख्यमंत्री किसान कल्याण योजना (CMKKY) सहायता" if lang == "hi" else "Mukhyamantri Kisan Kalyan Yojana (CMKKY) Top-Up",
                "description": "State top-up financial assistance of ₹6,000/year over PM-KISAN for registered Madhya Pradesh farmers.",
                "benefit": "₹6,000 / year state top-up",
                "deadline": _deadline_str(14),
                "documents_required": ["Samagra ID", "Aadhaar Card", "Khasra / B1 Khatauni", "Bank Passbook"],
                "portal_url": "https://saara.mp.gov.in/",
                "authority": "Revenue & Farmer Welfare Dept, Govt of MP",
                "helpline": "181 (CM Helpline)",
                "urgency": "high",
            },
            {
                "id": "mp-euparjan-rbc64",
                "category": "drought",
                "days_left": 9,
                "title": "MP e-Uparjan & RBC 6(4) Natural Calamity Crop Loss Relief",
                "localized_title": "म.प्र. ई-उपार्जन एवं आरबीसी 6(4) फसल क्षति राहत" if lang == "hi" else "MP e-Uparjan & RBC 6(4) Crop Loss Relief",
                "description": "Apply for RBC 6(4) relief for hailstorm, frost, or drought crop damage and MSP procurement slot booking on MP e-Uparjan.",
                "benefit": "Up to ₹32,000 / hectare relief",
                "deadline": _deadline_str(9),
                "documents_required": ["Khasra / B1 Khatauni", "Aadhaar Card", "Patwari Survey Report", "Bank Passbook"],
                "portal_url": "https://mpeuparjan.nic.in/",
                "authority": "MP Food, Civil Supplies & Revenue Dept",
                "helpline": "1800-233-0044",
                "urgency": "high",
            },
        ]

    if state == "Telangana":
        return [
            {
                "id": "ts-rythu-bharosa",
                "category": "subsidies",
                "days_left": 16,
                "title": f"Telangana Rythu Bharosa Investment Support{dist_note}",
                "localized_title": "తెలంగాణ రైతు భరోసా పెట్టుబడి సాయం" if lang == "te" else "Telangana Rythu Bharosa Investment Support",
                "description": "Seasonal crop investment support per acre credited directly to farmer bank accounts for Kharif & Rabi.",
                "benefit": "₹12,000 / acre / year",
                "deadline": _deadline_str(16),
                "documents_required": ["Dharani Passbook / Adangal 1B", "Aadhaar Card", "Bank Passbook"],
                "portal_url": "https://rythubandhu.telangana.gov.in/",
                "authority": "Dept of Agriculture, Govt of Telangana",
                "helpline": "1800-425-1110",
                "urgency": "high",
            },
            {
                "id": "ts-rythu-bima",
                "category": "insurance",
                "days_left": 22,
                "title": "Rythu Bima Farmer Life & Crop Loss Insurance",
                "localized_title": "రైతు బీమా & పంట నష్ట పరిహారం" if lang == "te" else "Rythu Bima Farmer Life & Crop Loss Insurance",
                "description": "₹5 Lakh life insurance coverage for enrolled Telangana pattadar farmers plus state crop loss & drip subsidy.",
                "benefit": "₹5,00,000 Life Cover + Drip Subsidy",
                "deadline": _deadline_str(22),
                "documents_required": ["Dharani Passbook / Adangal 1B", "Aadhaar Card", "Nominee Details"],
                "portal_url": "https://rythubima.telangana.gov.in/",
                "authority": "Telangana Agriculture & Cooperation Dept",
                "helpline": "1800-425-1110",
                "urgency": "medium",
            },
        ]

    if state == "Maharashtra":
        return [
            {
                "id": "mh-namo-shetkari",
                "category": "subsidies",
                "days_left": 13,
                "title": f"Namo Shetkari Mahasanman Nidhi & MahaDBT{dist_note}",
                "localized_title": "नमो शेतकरी महासन्मान निधी व महाडीबीटी अनुदान" if lang == "mr" else "Namo Shetkari Mahasanman Nidhi & MahaDBT",
                "description": "₹6,000/year state top-up + MahaDBT subsidies for drip irrigation, sprinklers, tractors, and farm mechanization.",
                "benefit": "₹6,000/yr + up to 80% Drip Subsidy",
                "deadline": _deadline_str(13),
                "documents_required": ["7/12 Extract (Satbara) & 8A", "Aadhaar Card", "Bank Passbook"],
                "portal_url": "https://mahadbt.maharashtra.gov.in/",
                "authority": "Dept of Agriculture, Govt of Maharashtra",
                "helpline": "1800-120-8040",
                "urgency": "high",
            },
            {
                "id": "mh-epik-pahani-ndrf",
                "category": "drought",
                "days_left": 10,
                "title": "e-Pik Pahani & NDRF/SDRF Heavy Rain / Drought Relief",
                "localized_title": "ई-पीक पाहणी व अतिवृष्टी/दुष्काळ नुकसान भरपाई" if lang == "mr" else "e-Pik Pahani & NDRF/SDRF Crop Loss Relief",
                "description": "Complete e-Pik Pahani crop registration to claim NDRF/SDRF heavy rain, flood, or drought crop loss compensation.",
                "benefit": "₹13,600 - ₹27,000 / hectare",
                "deadline": _deadline_str(10),
                "documents_required": ["7/12 Extract (Satbara) & 8A", "e-Pik Pahani Receipt", "Aadhaar Card"],
                "portal_url": "https://mahabhulekh.maharashtra.gov.in/",
                "authority": "Maharashtra Revenue & Relief Dept",
                "helpline": "1077 (Disaster Helpline)",
                "urgency": "high",
            },
        ]

    if state == "Gujarat":
        return [
            {
                "id": "gj-ikhedut",
                "category": "subsidies",
                "days_left": 17,
                "title": f"Gujarat iKhedut Drip, Tractor & Solar Subsidy{dist_note}",
                "localized_title": "ગુજરાત આઇ-ખેડૂત સબસિડી પોર્ટલ" if lang == "gu" else "Gujarat iKhedut Agri Subsidy Portal",
                "description": "Apply online on iKhedut portal for farm mechanization, micro-irrigation, and Mukhyamantri Kisan Sahay crop relief.",
                "benefit": "Up to 70% Subsidy / ₹25,000/ha relief",
                "deadline": _deadline_str(17),
                "documents_required": ["7/12 & 8A Land Record (AnyROR)", "Aadhaar Card", "Bank Passbook"],
                "portal_url": "https://ikhedut.gujarat.gov.in/",
                "authority": "Agriculture, Farmers Welfare & Cooperation Dept, Gujarat",
                "helpline": "1800-180-1551",
                "urgency": "medium",
            },
        ]

    if state in ("Punjab", "Haryana"):
        portal = "https://fasal.haryana.gov.in/" if state == "Haryana" else "https://agripunjab.gov.in/"
        return [
            {
                "id": f"{state.lower()}-fasal-dbt",
                "category": "subsidies",
                "days_left": 14,
                "title": f"{state} Meri Fasal Mera Byora & Agri Mechanization DBT{dist_note}",
                "localized_title": f"{state} ਫਸਲ ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਅਤੇ ਮਸ਼ੀਨਰੀ ਸਬਸਿਡੀ" if lang == "pa" else f"{state} Crop Registration & Mechanization DBT",
                "description": "Register crops for MSP procurement, crop diversification incentives, and Happy Seeder / Super SMS subsidies.",
                "benefit": "₹7,000/acre diversification + 50% CRM subsidy",
                "deadline": _deadline_str(14),
                "documents_required": ["Jamabandi / Fard Land Record", "Aadhaar Card", "Bank Passbook"],
                "portal_url": portal,
                "authority": f"Dept of Agriculture & Farmers Welfare, {state}",
                "helpline": "1800-180-2117",
                "urgency": "high",
            },
        ]

    if state == "Uttar Pradesh":
        return [
            {
                "id": "up-agri-dbt",
                "category": "subsidies",
                "days_left": 15,
                "title": f"UP Agriculture DBT & e-Khasra Crop Relief{dist_note}",
                "localized_title": "यूपी कृषि डीबीटी व ई-खसरा फसल राहत" if lang == "hi" else "UP Agriculture DBT & e-Khasra Crop Relief",
                "description": "Register on UP Agriculture portal for seed/fertilizer DBT, solar pump subsidy, and natural calamity crop loss relief.",
                "benefit": "Up to 50% Seed/Equipment Subsidy",
                "deadline": _deadline_str(15),
                "documents_required": ["e-Khasra / Khatauni (B1)", "Aadhaar Card", "Bank Passbook"],
                "portal_url": "https://upagriculture.com/",
                "authority": "UP Department of Agriculture",
                "helpline": "1800-180-1551",
                "urgency": "medium",
            },
        ]

    if state == "Tamil Nadu":
        return [
            {
                "id": "tn-uzhavan",
                "category": "subsidies",
                "days_left": 16,
                "title": f"Tamil Nadu Uzhavan & Kuruvai/Samba Relief Package{dist_note}",
                "localized_title": "தமிழ்நாடு உழவன் & பயிர் நிவாரணத் திட்டம்" if lang == "ta" else "Tamil Nadu Uzhavan & Crop Relief Package",
                "description": "Access TN Agriculture DBT, micro-irrigation subsidy, and crop damage relief via Uzhavan portal.",
                "benefit": "₹13,500 - ₹20,000 / ha relief",
                "deadline": _deadline_str(16),
                "documents_required": ["Chitta / Adangal Extract", "Aadhaar Card", "Bank Passbook"],
                "portal_url": "https://www.tnagrisnet.tn.gov.in/",
                "authority": "Dept of Agriculture, Govt of Tamil Nadu",
                "helpline": "1800-425-1444",
                "urgency": "medium",
            },
        ]

    if state == "Andhra Pradesh":
        return [
            {
                "id": "ap-annadata",
                "category": "subsidies",
                "days_left": 15,
                "title": f"AP Annadata Sukhibhava & e-Crop Relief{dist_note}",
                "localized_title": "ఏపీ అన్నదాత సుఖీభవ & ఇ-క్రాప్ సహాయం" if lang == "te" else "AP Annadata Sukhibhava & e-Crop Relief",
                "description": "Verify e-Crop booking for Annadata Sukhibhava investment support and natural calamity input subsidy.",
                "benefit": "₹20,000 / year combined support",
                "deadline": _deadline_str(15),
                "documents_required": ["Adangal / 1B Land Record", "Aadhaar Card", "Bank Passbook"],
                "portal_url": "https://karshak.ap.gov.in/",
                "authority": "Dept of Agriculture, Govt of Andhra Pradesh",
                "helpline": "1902 / 155251",
                "urgency": "high",
            },
        ]

    # Generic fallback for Rajasthan & other Indian states
    return [
        {
            "id": f"{state.lower().replace(' ', '-')}-state-relief",
            "category": "drought",
            "days_left": 14,
            "title": f"{state} State Agriculture DBT & Crop Loss Relief{dist_note}",
            "localized_title": f"{state} State Agriculture DBT & Crop Loss Relief",
            "description": f"State-level input subsidy, micro-irrigation support, and SDRF crop loss compensation for {state} farmers.",
            "benefit": "₹8,500 - ₹22,500 / hectare",
            "deadline": _deadline_str(14),
            "documents_required": ["Aadhaar Card", land_doc, "Bank Passbook"],
            "portal_url": "https://agricoop.nic.in/",
            "authority": f"Department of Agriculture, Govt of {state}",
            "helpline": "1800-180-1551",
            "urgency": "medium",
        },
    ]


@router.get("")
@router.get("/")
def get_schemes(
    state: str = Query("Karnataka"),
    district: str = Query(""),
    location_name: str = Query(""),
    category: str = Query("all", description="all, fellowships, subsidies, insurance, drought"),
    language: str = Query("en-IN"),
):
    resolved_state = normalize_state(state, location_name)
    lang = _normalize_lang(language)
    land_doc = STATE_LAND_DOCS.get(resolved_state, "Land Record / Patta / Khasra")

    cached_items = _get_cached(resolved_state, lang)
    if cached_items is None:
        state_items = _build_state_schemes(resolved_state, district, land_doc, lang)
        central_items = _build_central_schemes(resolved_state, land_doc, lang)
        cached_items = state_items + central_items
        _set_cached(resolved_state, lang, cached_items)

    cat_norm = (category or "all").lower().strip()
    cat_alias = {"training": "fellowships", "relief": "drought"}.get(cat_norm, cat_norm)

    if cat_alias != "all":
        filtered = [item for item in cached_items if item.get("category") == cat_alias]
    else:
        filtered = cached_items

    return {
        "state": resolved_state,
        "district": district,
        "location_name": location_name,
        "language": language,
        "subtitle": LOCALIZED_SUBTITLES.get(lang, LOCALIZED_SUBTITLES["en"]),
        "total": len(filtered),
        "unread_count": len(filtered),
        "schemes": filtered,
    }
