"""
FasalSaarathi — Module 4: WhatsApp-Style Farm Passbook & Daily Voice Briefing
=============================================================================
Unifies Profile (Module 1), Kitchen Waste & Compost Logs (Module 2),
PMFBY Crop Insurance Shield (Module 3), Live Weather, and APMC Mandi Prices
into a conversational WhatsApp-style daily message & voice note across 6 languages.
"""

from contextlib import closing
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from tools.auth_tool import DEFAULT_USERS_DB, get_user_profile, init_auth_db
from tools.insurance_tool import (
    evaluate_weather_claim_alert,
    init_insurance_db,
    list_insurance_policies,
)
from tools.mandi_tool import fetch_mandi_prices
from tools.weather_tool import fetch_live_weather

LANGS = ("en", "kn", "hi", "ta", "te", "mr")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_passbook_db(db_path: str = DEFAULT_USERS_DB) -> None:
    """Ensure `users`, insurance tables, `compost_logs`, and `passbook_messages` exist."""
    init_auth_db(db_path)
    init_insurance_db(db_path)
    with closing(_connect(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS compost_logs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                waste_type TEXT NOT NULL,
                waste_kg REAL NOT NULL,
                browns_kg REAL NOT NULL,
                ready_date TEXT NOT NULL,
                money_saved_inr INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS passbook_messages (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                text TEXT NOT NULL,
                speech_text TEXT DEFAULT '',
                metadata_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _get_compost_summary(user_id: str, db_path: str) -> Dict[str, Any]:
    with closing(_connect(db_path)) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS entries,
                   COALESCE(SUM(waste_kg), 0.0) AS total_waste_kg,
                   COALESCE(SUM(money_saved_inr), 0) AS total_saved_inr
            FROM compost_logs
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    return {
        "entries": int(row["entries"] or 0),
        "total_waste_kg": round(float(row["total_waste_kg"] or 0.0), 1),
        "total_saved_inr": int(row["total_saved_inr"] or 0),
    }


def _save_message(
    user_id: str,
    sender: str,
    text: str,
    speech_text: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    db_path: str = DEFAULT_USERS_DB,
) -> Dict[str, Any]:
    msg_id = f"msg_{uuid.uuid4().hex[:10]}"
    now = _now_iso()
    meta_json = json.dumps(metadata or {}, ensure_ascii=False)
    with closing(_connect(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO passbook_messages (id, user_id, sender, text, speech_text, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (msg_id, user_id, sender, text, speech_text or text, meta_json, now),
        )
        conn.commit()
    return {
        "id": msg_id,
        "user_id": user_id,
        "sender": sender,
        "text": text,
        "speech_text": speech_text or text,
        "metadata": metadata or {},
        "created_at": now,
    }


def get_passbook_history(
    user_id: str,
    limit: int = 30,
    db_path: str = DEFAULT_USERS_DB,
) -> List[Dict[str, Any]]:
    init_passbook_db(db_path)
    uid = (user_id or "guest").strip() or "guest"
    with closing(_connect(db_path)) as conn:
        rows = conn.execute(
            """
            SELECT * FROM passbook_messages
            WHERE user_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (uid, max(1, min(100, int(limit)))),
        ).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        try:
            item["metadata"] = json.loads(item.pop("metadata_json", "{}") or "{}")
        except Exception:
            item["metadata"] = {}
        out.append(item)
    return out


def clear_passbook_history(user_id: str, db_path: str = DEFAULT_USERS_DB) -> None:
    init_passbook_db(db_path)
    uid = (user_id or "guest").strip() or "guest"
    with closing(_connect(db_path)) as conn:
        conn.execute("DELETE FROM passbook_messages WHERE user_id = ?", (uid,))
        conn.commit()


def _clean_speech(text: str) -> str:
    cleaned = re.sub(r"[🌾🌤️♻️🛡️💰📍⚠️🚨✅📌🔊•*]+", " ", text)
    cleaned = re.sub(r"\n+", ". ", cleaned)
    return re.sub(r"\s{2,}", " ", cleaned).strip()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Daily WhatsApp Briefing Builder
# ─────────────────────────────────────────────────────────────────────────────
def build_daily_passbook_briefing(
    user_id: str = "guest",
    location_override: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    commodity: str = "tomato",
    language: Optional[str] = None,
    save_to_history: bool = True,
    db_path: str = DEFAULT_USERS_DB,
    weather_data: Optional[Dict[str, Any]] = None,
    mandi_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble today's unified WhatsApp Passbook briefing across all modules."""
    init_passbook_db(db_path)
    uid = (user_id or "guest").strip() or "guest"
    profile = get_user_profile(uid, db_path=db_path) or {
        "user_id": "guest",
        "name": "Farmer",
        "persona": "farmer",
        "language": "en",
        "location_query": "",
    }

    lang = (language or profile.get("language") or "en").strip().lower()
    if lang not in LANGS:
        lang = "en"

    user_name = profile.get("name") or "Farmer"
    loc = (location_override if location_override is not None else profile.get("location_query") or "").strip()
    u_lat = lat if lat is not None else profile.get("lat")
    u_lon = lon if lon is not None else profile.get("lon")

    # 1. Live Weather & Watering
    if weather_data is None and (loc or (u_lat is not None and u_lon is not None)):
        weather_data = fetch_live_weather(location_query=loc or None, lat=u_lat, lon=u_lon)

    w_ok = weather_data and weather_data.get("status") in ("success", "cached_real")
    if w_ok:
        disp_loc = weather_data.get("display_location") or weather_data.get("location") or loc
        rain_mm = float(weather_data.get("rain_today_mm") or 0.0)
        temp_c = float(weather_data.get("current_temperature_c") or 0.0)
        irr_note = weather_data.get("irrigation_action") or f"{temp_c}°C, {rain_mm} mm rain today."
        alert_res = evaluate_weather_claim_alert(
            location_query=disp_loc,
            language=lang,
            weather_data=weather_data,
        )
    else:
        disp_loc = loc or "Your Farm"
        irr_note = None
        alert_res = {"alert_level": "UNKNOWN", "advisory": ""}

    # 2. Compost & Kitchen Waste
    compost = _get_compost_summary(uid, db_path)

    # 3. Insurance Policies
    policies = list_insurance_policies(uid, db_path=db_path)
    pol_count = len(policies)

    # 4. Mandi Rate
    comm_q = (commodity or "tomato").strip() or "tomato"
    if mandi_data is None:
        mandi_data = fetch_mandi_prices(comm_q, location_hint=loc, lat=u_lat, lon=u_lon, language=lang)
    m_ok = mandi_data and mandi_data.get("status") in ("success", "cached_real")

    # Build localized message lines
    greetings = {
        "en": f"Namaskara {user_name}! Here is your FasalSaarathi Farm Passbook for {disp_loc}:",
        "kn": f"ನಮಸ್ಕಾರ {user_name}! {disp_loc} ಗಾಗಿ ಇಂದಿನ ನಿಮ್ಮ ಫಸಲ್ ಸಾರಥಿ ಪಾಸ್‌ಬುಕ್:",
        "hi": f"नमस्ते {user_name}! {disp_loc} के लिए आज की आपकी फसल सारथी पासबुक:",
        "ta": f"வணக்கம் {user_name}! {disp_loc} பகுதிக்கான இன்றைய ஃபசல் சாரதி பாஸ்புக்:",
        "te": f"నమస్కారం {user_name}! {disp_loc} కోసం నేటి మీ ఫసల్ సారథి పాస్‌బుక్:",
        "mr": f"नमस्कार {user_name}! {disp_loc} साठी आजचे तुमचे फसल सारथी पासबुक:",
    }

    if w_ok:
        rain_tom = float(weather_data.get("rain_tomorrow_mm") or 0.0)
        skip_water = rain_mm >= 5.0 or rain_tom >= 8.0
        if lang == "en":
            water_msg = irr_note
        elif skip_water:
            water_msg = {
                "kn": "ಮಳೆ ಸಾಧ್ಯತೆ ಇರುವುದರಿಂದ ಇಂದು ನೀರು ಹಾಕುವುದು ಬೇಡ.",
                "hi": "बारिश की संभावना है, आज सिंचाई टाल दें।",
                "ta": "மழை வாய்ப்பு உள்ளதால் இன்று நீர் பாய்ச்ச வேண்டாம்.",
                "te": "వర్షం అవకాశం ఉన్నందున నేడు నీరు పోయకండి.",
                "mr": "पावसाची शक्यता आहे, आज पाणी देणे टाळा.",
            }[lang]
        else:
            water_msg = {
                "kn": "ಬೆಳಗಿನ ವೇಳೆಯಲ್ಲಿ ಸಾಮಾನ್ಯವಾಗಿ ನೀರು ಕೊಡಿ.",
                "hi": "सुबह के समय सामान्य सिंचाई करें।",
                "ta": "காலை நேரத்தில் வழக்கம்போல் நீர் பாய்ச்சவும்.",
                "te": "ఉదయం వేళలో సాధారణంగా నీరు పెట్టండి.",
                "mr": "सकाळच्या वेळी नेहमीप्रमाणे पाणी द्या.",
            }[lang]
        weather_line = {
            "en": f"🌤️ Weather & Watering: {temp_c}°C • {water_msg}",
            "kn": f"🌤️ ಹವಾಮಾನ ಮತ್ತು ನೀರು: {temp_c}°C • ಮಳೆ {rain_mm} ಮಿ.ಮೀ — {water_msg}",
            "hi": f"🌤️ मौसम व सिंचाई: {temp_c}°C • बारिश {rain_mm} मिमी — {water_msg}",
            "ta": f"🌤️ வானிலை & நீர்: {temp_c}°C • மழை {rain_mm} மி.மீ — {water_msg}",
            "te": f"🌤️ వాతావరణం & నీరు: {temp_c}°C • వర్షం {rain_mm} మి.మీ — {water_msg}",
            "mr": f"🌤️ हवामान व पाणी: {temp_c}°C • पाऊस {rain_mm} मिमी — {water_msg}",
        }[lang]
    else:
        weather_line = {
            "en": "🌤️ Weather & Watering: Add your village/PIN in Profile or below to get live watering updates.",
            "kn": "🌤️ ಹವಾಮಾನ: ನಿಮ್ಮ ಗ್ರಾಮ ಅಥವಾ PIN ನಮೂದಿಸಿದರೆ ಇಂದಿನ ನೀರಿನ ಸಲಹೆ ಸಿಗುತ್ತದೆ.",
            "hi": "🌤️ मौसम: लाइव सिंचाई सलाह के लिए अपनी लोकेशन या पिन डालें।",
            "ta": "🌤️ வானிலை: உங்கள் ஊர் அல்லது PIN ஐ சேர்த்தால் நேரடி நீர் ஆலோசனை கிடைக்கும்.",
            "te": "🌤️ వాతావరణం: లైవ్ నీటి సలహా కోసం మీ గ్రామం లేదా PIN నమోదు చేయండి.",
            "mr": "🌤️ हवामान: थेट पाणी सल्ल्यासाठी तुमचे गाव किंवा पिन कोड टाका.",
        }[lang]

    if compost["entries"] > 0:
        compost_line = {
            "en": f"♻️ Kitchen Waste & Compost: {compost['total_waste_kg']} kg recycled so far (₹{compost['total_saved_inr']} saved on compost!). Tap below whenever you add kitchen peels.",
            "kn": f"♻️ ಅಡುಗೆ ತ್ಯಾಜ್ಯ ಮತ್ತು ಗೊಬ್ಬರ: ಇದುವರೆಗೆ {compost['total_waste_kg']} ಕೆ.ಜಿ ಕಸದಿಂದ ಗೊಬ್ಬರ (₹{compost['total_saved_inr']} ಉಳಿತಾಯ!).",
            "hi": f"♻️ रसोई कचरा व खाद: अब तक {compost['total_waste_kg']} किलो कचरा रीसायकल (₹{compost['total_saved_inr']} की बचत!)।",
            "ta": f"♻️ சமையலறை கழிவு & உரம்: இதுவரை {compost['total_waste_kg']} கிலோ உரம் தயாரானது (₹{compost['total_saved_inr']} சேமிப்பு!).",
            "te": f"♻️ వంటగది వ్యర్థాలు & ఎరువు: ఇప్పటివరకు {compost['total_waste_kg']} కిలోలు రీసైకిల్ (₹{compost['total_saved_inr']} ఆదా!).",
            "mr": f"♻️ स्वयंपाकघर कचरा व खत: आतापर्यंत {compost['total_waste_kg']} किलो कचरा वापरला (₹{compost['total_saved_inr']} बचत!).",
        }[lang]
    else:
        compost_line = {
            "en": "♻️ Kitchen Waste & Compost: 0 kg logged yet. Tap 'Added 1kg Kitchen Waste' below to start earning compost savings!",
            "kn": "♻️ ಅಡುಗೆ ತ್ಯಾಜ್ಯ ಮತ್ತು ಗೊಬ್ಬರ: ಇನ್ನೂ ದಾಖಲಾಗಿಲ್ಲ. ಪ್ರಾರಂಭಿಸಲು ಕೆಳಗಿನ '1 ಕೆ.ಜಿ ಅಡುಗೆ ತ್ಯಾಜ್ಯ' ಬಟನ್ ಒತ್ತಿ!",
            "hi": "♻️ रसोई कचरा व खाद: अभी कोई एंट्री नहीं। शुरू करने के लिए नीचे '1 किलो रसोई कचरा' दबाएं!",
            "ta": "♻️ சமையலறை கழிவு: இன்னும் பதிவு இல்லை. தொடங்க கீழே உள்ள பொத்தானை அழுத்தவும்!",
            "te": "♻️ వంటగది వ్యర్థాలు: ఇంకా నమోదు కాలేదు. ప్రారంభించడానికి కింది బటన్ నొక్కండి!",
            "mr": "♻️ स्वयंपाकघर कचरा: अजून नोंद नाही. सुरू करण्यासाठी खालील बटण दाबा!",
        }[lang]

    alert_lvl = alert_res.get("alert_level", "UNKNOWN")
    if alert_lvl == "RED_72H_CLAIM":
        ins_line = f"🚨 Crop Shield ({pol_count} active): {alert_res.get('advisory')}"
    elif pol_count > 0:
        ins_line = {
            "en": f"🛡️ Crop Insurance: {pol_count} active policy(ies) • Weather is safe today.",
            "kn": f"🛡️ ಬೆಳೆ ವಿಮೆ: {pol_count} ಸಕ್ರಿಯ ಪಾಲಿಸಿ ಇದೆ • ಇಂದು ಹವಾಮಾನ ಸುರಕ್ಷಿತವಾಗಿದೆ.",
            "hi": f"🛡️ फसल बीमा: {pol_count} सक्रिय पॉलिसी • आज मौसम सुरक्षित है।",
            "ta": f"🛡️ பயிர் காப்பீடு: {pol_count} செயலில் உள்ள பாலிசி • இன்று வானிலை பாதுகாப்பானது.",
            "te": f"🛡️ పంట బీమా: {pol_count} యాక్టివ్ పాలసీలు • నేడు వాతావరణం సురక్షితం.",
            "mr": f"🛡️ पीक विमा: {pol_count} सक्रिय पॉलिसी • आज हवामान सुरक्षित आहे.",
        }[lang]
    else:
        ins_line = {
            "en": "🛡️ Crop Insurance: No policy saved yet — open Crop Shield tab to calculate PMFBY cover (from 1.5%).",
            "kn": "🛡️ ಬೆಳೆ ವಿಮೆ: ಇನ್ನೂ ಪಾಲಿಸಿ ಉಳಿಸಿಲ್ಲ — PMFBY ವಿಮೆ ಲೆಕ್ಕಹಾಕಲು 'ಬೆಳೆ ವಿಮೆ' ವಿಭಾಗ ನೋಡಿ.",
            "hi": "🛡️ फसल बीमा: अभी कोई पॉलिसी सेव नहीं — PMFBY कवर देखने के लिए 'फसल बीमा' टैब खोलें।",
            "ta": "🛡️ பயிர் காப்பீடு: பாலிசி சேமிக்கப்படவில்லை — PMFBY விவரம் காண பயிர் காப்பீடு தாவலைப் பார்க்கவும்.",
            "te": "🛡️ పంట బీమా: పాలసీ సేవ్ కాలేదు — PMFBY కవర్ చూడటానికి పంట బీమా ట్యాబ్ తెరవండి.",
            "mr": "🛡️ पीक विमा: अजून पॉलिसी सेव्ह नाही — PMFBY हप्ता पाहण्यासाठी पीक विमा टॅब उघडा.",
        }[lang]

    if m_ok:
        mandi_line = {
            "en": f"💰 Mandi Rate ({mandi_data.get('commodity')}): ₹{mandi_data.get('price_per_kg')}/kg at {mandi_data.get('primary_mandi')} ({mandi_data.get('trend')}).",
            "kn": f"💰 ಮಂಡಿ ದರ ({mandi_data.get('commodity')}): {mandi_data.get('primary_mandi')} ನಲ್ಲಿ ಕೆ.ಜಿ ಗೆ ₹{mandi_data.get('price_per_kg')} ({mandi_data.get('trend')}).",
            "hi": f"💰 मंडी भाव ({mandi_data.get('commodity')}): {mandi_data.get('primary_mandi')} में ₹{mandi_data.get('price_per_kg')}/किलो ({mandi_data.get('trend')})।",
            "ta": f"💰 சந்தை விலை ({mandi_data.get('commodity')}): {mandi_data.get('primary_mandi')} — ₹{mandi_data.get('price_per_kg')}/கிலோ.",
            "te": f"💰 మండీ ధర ({mandi_data.get('commodity')}): {mandi_data.get('primary_mandi')} లో ₹{mandi_data.get('price_per_kg')}/కిలో.",
            "mr": f"💰 बाजारभाव ({mandi_data.get('commodity')}): {mandi_data.get('primary_mandi')} मध्ये ₹{mandi_data.get('price_per_kg')}/किलो.",
        }[lang]
    else:
        mandi_line = {
            "en": "💰 Mandi Rate: Open Agro Tools or ask for a crop price (Tomato, Onion, Paddy).",
            "kn": "💰 ಮಂಡಿ ದರ: ಬೆಳೆ ದರ ತಿಳಿಯಲು ಕೆಳಗೆ ಕೇಳಿ ಅಥವಾ ಅಗ್ರೋ ಟೂಲ್ಸ್ ನೋಡಿ.",
            "hi": "💰 मंडी भाव: फसल का भाव जानने के लिए नीचे पूछें या एग्रो टूल्स देखें।",
            "ta": "💰 சந்தை விலை: பயிர் விலையை கீழே கேட்கவும் அல்லது அக்ரோ கருவிகளைப் பார்க்கவும்.",
            "te": "💰 మండీ ధర: పంట ధర తెలుసుకోవడానికి కింద అడగండి లేదా అగ్రో టూల్స్ చూడండి.",
            "mr": "💰 बाजारभाव: पिकाचा भाव जाणून घेण्यासाठी खाली विचारा किंवा ॲग्रो टूल्स पहा.",
        }[lang]

    full_text = "\n\n".join([greetings[lang], weather_line, compost_line, ins_line, mandi_line])
    speech_text = _clean_speech(full_text)

    meta = {
        "type": "daily_briefing",
        "lang": lang,
        "location": disp_loc,
        "alert_level": alert_lvl,
        "waste_kg": compost["total_waste_kg"],
        "saved_inr": compost["total_saved_inr"],
        "active_policies": pol_count,
    }
    msg = _save_message(uid, "bot", full_text, speech_text=speech_text, metadata=meta, db_path=db_path) if save_to_history else {
        "id": "preview",
        "user_id": uid,
        "sender": "bot",
        "text": full_text,
        "speech_text": speech_text,
        "metadata": meta,
        "created_at": _now_iso(),
    }

    return {
        "status": "success",
        "message": msg,
        "stats": {
            "user_name": user_name,
            "location": disp_loc,
            "waste_kg": compost["total_waste_kg"],
            "saved_inr": compost["total_saved_inr"],
            "active_policies": pol_count,
            "alert_level": alert_lvl,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Two-Way WhatsApp Reply Handler
# ─────────────────────────────────────────────────────────────────────────────
def handle_passbook_reply(
    user_id: str = "guest",
    action: str = "",
    text: str = "",
    location_override: Optional[str] = None,
    commodity: str = "tomato",
    language: Optional[str] = None,
    db_path: str = DEFAULT_USERS_DB,
    weather_data: Optional[Dict[str, Any]] = None,
    mandi_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Process a WhatsApp quick-reply chip or free-text message and update SQLite."""
    init_passbook_db(db_path)
    uid = (user_id or "guest").strip() or "guest"
    profile = get_user_profile(uid, db_path=db_path) or {"language": "en", "location_query": ""}

    lang = (language or profile.get("language") or "en").strip().lower()
    if lang not in LANGS:
        lang = "en"

    clean_text = (text or "").strip()
    act = (action or "").strip().lower()
    low = clean_text.lower()

    if not act:
        if any(w in low for w in ("waste", "peel", "compost", "kitchen", "ಕಸ", "गೊಬ್ಬರ", "कचरा", "खाद")):
            act = "log_waste"
        elif any(w in low for w in ("insur", "claim", "storm", "alert", "pmfby", "ವಿಮೆ", "बीमा", "காப்பீடு", "బీమా", "विमा")):
            act = "check_insurance"
        elif any(w in low for w in ("mandi", "price", "rate", "market", "onion", "tomato", "paddy", "ದರ", "भाव")):
            act = "check_mandi"
        else:
            act = "daily_briefing"

    user_chip_i18n = {
        "log_waste": {
            "en": "♻️ Added 1 kg kitchen waste",
            "kn": "♻️ 1 ಕೆ.ಜಿ ಅಡುಗೆ ತ್ಯಾಜ್ಯ ಸೇರಿಸಲಾಗಿದೆ",
            "hi": "♻️ 1 किलो रसोई कचरा जोड़ा",
            "ta": "♻️ 1 கிலோ சமையலறை கழிவு சேர்த்தேன்",
            "te": "♻️ 1 కిలో వంటగది వ్యర్థాలు వేశాను",
            "mr": "♻️ 1 किलो स्वयंपाकघर कचरा टाकला",
        },
        "check_insurance": {
            "en": "🛡️ Check my Crop Insurance alert",
            "kn": "🛡️ ನನ್ನ ಬೆಳೆ ವಿಮೆ ಎಚ್ಚರಿಕೆ ಪರಿಶೀಲಿಸಿ",
            "hi": "🛡️ मेरा फसल बीमा अलर्ट जांचें",
            "ta": "🛡️ எனது பயிர் காப்பீட்டு எச்சரிக்கை பார்",
            "te": "🛡️ నా పంట బీమా హెచ్చరిక చూడండి",
            "mr": "🛡️ माझा पीक विमा इशारा तपासा",
        },
        "check_mandi": {
            "en": f"💰 Check {commodity} mandi rate",
            "kn": "💰 ಇಂದಿನ ಮಂಡಿ ದರ ತಿಳಿಸಿ",
            "hi": "💰 आज का मंडी भाव बताएं",
            "ta": "💰 இன்றைய சந்தை விலை என்ன?",
            "te": "💰 నేటి మండీ ధర చెప్పండి",
            "mr": "💰 आजचा बाजारभाव सांगा",
        },
        "daily_briefing": {
            "en": "☀️ Send today's Farm Passbook",
            "kn": "☀️ ಇಂದಿನ ಫಾರ್ಮ್ ಪಾಸ್‌ಬುಕ್ ಕಳುಹಿಸಿ",
            "hi": "☀️ आज की फ़ार्म पासबुक भेजें",
            "ta": "☀️ இன்றைய பண்ணை பாஸ்புக் அனுப்பு",
            "te": "☀️ నేటి ఫార్మ్ పాస్‌బుక్ పంపండి",
            "mr": "☀️ आजचे फार्म पासबुक पाठवा",
        },
    }
    user_display = clean_text or user_chip_i18n.get(act, {}).get(lang, "Hi FasalSaarathi")

    user_msg = _save_message(uid, "user", user_display, db_path=db_path)

    loc = (location_override if location_override is not None else profile.get("location_query") or "").strip()

    if act == "log_waste":
        m_kg = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|kilo)", low)
        kg = float(m_kg.group(1)) if m_kg else 1.0
        kg = max(0.2, min(50.0, round(kg, 1)))
        browns_kg = round(kg * 1.0, 1)  # 1:1 dry leaves/cocopeat by weight prevents odor
        handfuls = max(2, int(round(browns_kg * 6)))
        saved_inr = int(round(kg * 30))
        ready_days = 45
        now_iso = _now_iso()
        log_id = f"cmp_{uuid.uuid4().hex[:10]}"

        with closing(_connect(db_path)) as conn:
            conn.execute(
                """
                INSERT INTO compost_logs (id, user_id, waste_type, waste_kg, browns_kg, ready_date, money_saved_inr, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (log_id, uid, "kitchen_peels", kg, browns_kg, f"{ready_days} days", saved_inr, now_iso),
            )
            conn.commit()

        compost = _get_compost_summary(uid, db_path)
        reply_map = {
            "en": (
                f"✅ Logged {kg} kg kitchen waste! Mix in ~{browns_kg} kg ({handfuls} handfuls) of dry leaves or cocopeat so the bin never smells.\n"
                f"♻️ Total recycled: {compost['total_waste_kg']} kg (₹{compost['total_saved_inr']} saved!). Avoid adding oily cooked food or dairy."
            ),
            "kn": (
                f"✅ {kg} ಕೆ.ಜಿ ಅಡುಗೆ ತ್ಯಾಜ್ಯ ದಾಖಲಾಗಿದೆ! ವಾಸನೆ ಬಾರದಂತೆ ಸುಮಾರು {browns_kg} ಕೆ.ಜಿ ({handfuls} ಹಿಡಿ) ಒಣ ಎಲೆ ಅಥವಾ ಕೊಕೊಪೀಟ್ ಬೆರೆಸಿ.\n"
                f"♻️ ಒಟ್ಟು ಉಳಿತಾಯ: {compost['total_waste_kg']} ಕೆ.ಜಿ (₹{compost['total_saved_inr']} ಉಳಿತಾಯ!). ಎಣ್ಣೆ ಪದಾರ್ಥ ಹಾಕಬೇಡಿ."
            ),
            "hi": (
                f"✅ {kg} किलो रसोई कचरा जुड़ गया! बदबू से बचने के लिए ~{browns_kg} किलो ({handfuls} मुट्ठी) सूखे पत्ते या कोकोपीट मिलाएं।\n"
                f"♻️ कुल रीसायकल: {compost['total_waste_kg']} किलो (₹{compost['total_saved_inr']} की बचत!)। तला-भुना व डेयरी न डालें।"
            ),
            "ta": (
                f"✅ {kg} கிலோ சமையலறை கழிவு சேர்க்கப்பட்டது! துர்நாற்றம் வராமல் இருக்க {browns_kg} கிலோ ({handfuls} கைப்பிடி) உலர்ந்த இலை சேர்க்கவும்.\n"
                f"♻️ மொத்த சேமிப்பு: ₹{compost['total_saved_inr']}."
            ),
            "te": (
                f"✅ {kg} కిలోల వంటగది వ్యర్థాలు నమోదయ్యాయి! వాసన రాకుండా {browns_kg} కిలోల ({handfuls} గుప్పెళ్ళు) ఎండు ఆకులు కలపండి.\n"
                f"♻️ మొత్తం ఆదా: ₹{compost['total_saved_inr']}."
            ),
            "mr": (
                f"✅ {kg} किलो स्वयंपाकघर कचरा नोंदवला! वास येऊ नये म्हणून {browns_kg} किलो ({handfuls} मुठी) वाळलेली पाने मिसळा.\n"
                f"♻️ एकूण बचत: ₹{compost['total_saved_inr']}."
            ),
        }
        bot_text = reply_map.get(lang, reply_map["en"])
        bot_msg = _save_message(uid, "bot", bot_text, speech_text=_clean_speech(bot_text), db_path=db_path)

    elif act == "check_insurance":
        policies = list_insurance_policies(uid, db_path=db_path)
        if loc or weather_data is not None:
            alert = evaluate_weather_claim_alert(location_query=loc or None, language=lang, weather_data=weather_data)
            adv = alert.get("advisory") or alert.get("message") or ""
        else:
            adv = {
                "en": "Set your village/PIN in Profile or Crop Shield tab to check live 72-hour storm alerts.",
                "kn": "72 ಗಂಟೆಗಳ ಹವಾಮಾನ ಎಚ್ಚರಿಕೆ ನೋಡಲು ನಿಮ್ಮ ಗ್ರಾಮ ಅಥವಾ PIN ನಮೂದಿಸಿ.",
                "hi": "72 घंटे का तूफ़ान अलर्ट देखने के लिए प्रोफ़ाइल में अपना गांव या पिन डालें।",
                "ta": "72 மணி நேர புயல் எச்சரிக்கை காண உங்கள் ஊர் அல்லது PIN ஐ உள்ளிடவும்.",
                "te": "72 గంటల తుఫాను హెచ్చరిక కోసం మీ గ్రామం లేదా PIN నమోదు చేయండి.",
                "mr": "72 तासांचा वादळ इशारा पाहण्यासाठी तुमचे गाव किंवा पिन कोड टाका.",
            }[lang]
        pol_hdr = {
            "en": f"🛡️ Active Policies: {len(policies)}",
            "kn": f"🛡️ ಸಕ್ರಿಯ ಪಾಲಿಸಿಗಳು: {len(policies)}",
            "hi": f"🛡️ सक्रिय पॉलिसी: {len(policies)}",
            "ta": f"🛡️ செயலில் உள்ள பாலிசிகள்: {len(policies)}",
            "te": f"🛡️ యాక్టివ్ పాలసీలు: {len(policies)}",
            "mr": f"🛡️ सक्रिय पॉलिसी: {len(policies)}",
        }[lang]
        bot_text = f"{pol_hdr}\n{adv}"
        bot_msg = _save_message(uid, "bot", bot_text, speech_text=_clean_speech(bot_text), db_path=db_path)

    elif act == "check_mandi":
        chosen_crop = commodity
        for candidate in ("onion", "potato", "paddy", "rice", "chilli", "coffee", "cotton", "maize", "tomato"):
            if candidate in low:
                chosen_crop = candidate
                break
        m = mandi_data if mandi_data is not None else fetch_mandi_prices(chosen_crop, location_hint=loc, language=lang)
        if m.get("status") in ("success", "cached_real"):
            rate_lbl = {
                "en": f"💰 {m.get('commodity')} at {m.get('primary_mandi')} ({m.get('primary_state')}):\n₹{m.get('price_per_kg')}/kg (₹{m.get('modal_price')}/100 kg) • {m.get('trend')}.",
                "kn": f"💰 {m.get('primary_mandi')} ನಲ್ಲಿ {m.get('commodity')} ದರ:\nಕೆ.ಜಿ ಗೆ ₹{m.get('price_per_kg')} (ಕ್ವಿಂಟಲ್‌ಗೆ ₹{m.get('modal_price')}) • {m.get('trend')}.",
                "hi": f"💰 {m.get('primary_mandi')} में {m.get('commodity')} भाव:\n₹{m.get('price_per_kg')}/किलो (₹{m.get('modal_price')}/क्विंटल) • {m.get('trend')}।",
                "ta": f"💰 {m.get('primary_mandi')} — {m.get('commodity')} விலை:\n₹{m.get('price_per_kg')}/கிலோ (₹{m.get('modal_price')}/100 கிலோ) • {m.get('trend')}.",
                "te": f"💰 {m.get('primary_mandi')} లో {m.get('commodity')} ధర:\n₹{m.get('price_per_kg')}/కిలో (₹{m.get('modal_price')}/క్వింటాల్) • {m.get('trend')}.",
                "mr": f"💰 {m.get('primary_mandi')} मध्ये {m.get('commodity')} भाव:\n₹{m.get('price_per_kg')}/किलो (₹{m.get('modal_price')}/क्विंटल) • {m.get('trend')}.",
            }[lang]
            bot_text = f"{rate_lbl}\n{m.get('selling_advisory', '')}"
        else:
            bot_text = m.get("message") or "Could not fetch mandi prices right now."
        bot_msg = _save_message(uid, "bot", bot_text, speech_text=_clean_speech(bot_text), db_path=db_path)

    else:
        brief = build_daily_passbook_briefing(
            user_id=uid,
            location_override=loc,
            commodity=commodity,
            language=lang,
            save_to_history=True,
            db_path=db_path,
            weather_data=weather_data,
            mandi_data=mandi_data,
        )
        return {
            "status": "success",
            "user_message": user_msg,
            "bot_message": brief["message"],
            "stats": brief["stats"],
        }

    compost = _get_compost_summary(uid, db_path)
    policies = list_insurance_policies(uid, db_path=db_path)
    return {
        "status": "success",
        "user_message": user_msg,
        "bot_message": bot_msg,
        "stats": {
            "location": loc or "Your Farm",
            "waste_kg": compost["total_waste_kg"],
            "saved_inr": compost["total_saved_inr"],
            "active_policies": len(policies),
        },
    }
