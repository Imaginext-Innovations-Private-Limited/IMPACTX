"""
KisanVaani Comprehensive Test Suite — 15 Integration Tests
Tests:
 1.  App startup & home page
 3.  Weather tool (live or fallback)
 4.  Soil health tool
 5.  Mandi price tool
 6.  Agent status endpoint
 7.  Kannada response — no English leakage
 8.  Hindi response — no English leakage
 9.  Tamil response
10.  Telugu response
11.  Marathi response
12.  TTS endpoint
13.  Leaf disease diagnostic (sample image)
14.  Missing location handling (ask, don't silently default)
15.  Invalid image upload rejected
"""

import sys
import os
import io
import json

# Ensure clean env for tests (no Gemini key so we use rule-based deterministic path)
os.environ.setdefault("GEMINI_API_KEY", "")

from app import app

# ─────────────────────────────────────────────────────────────
PASS = 0
FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  ✅  {label}")
        PASS += 1
    else:
        print(f"  ❌  {label}" + (f" — {detail}" if detail else ""))
        FAIL += 1

def run_tests():
    global PASS, FAIL
    PASS = FAIL = 0

    print("=" * 60)
    print("🌾  FASALSAARATHI — COMPREHENSIVE TEST SUITE  (15 Tests)")
    print("=" * 60)

    client = app.test_client()

    # ── Test 1: App startup ──────────────────────────────────
    print("\n[1/15] App Startup & Home Page")
    r = client.get("/")
    check("HTTP 200", r.status_code == 200)
    html = r.get_data(as_text=True)
    check("FasalSaarathi in page", "fasalsaarathi" in html.lower())


    # ── Test 3: Weather tool ───────────────
    print("\n[3/15] Weather Tool")
    r_empty = client.get("/api/tools/weather")
    check("Missing location rejected (HTTP 400)", r_empty.status_code == 400)

    r = client.get("/api/tools/weather?location=Mandya")
    check("HTTP 200", r.status_code == 200)
    w = r.get_json()
    if w.get("status") in ("success", "cached_real"):
        check("Has live/cached temperature", isinstance(w.get("current_temperature_c"), (int, float)))
        check("Has humidity", isinstance(w.get("humidity_pct"), (int, float)))
        check("Has rain prob", isinstance(w.get("rain_today_probability_pct"), (int, float)))
        check("Has 7-day forecast", len(w.get("daily_forecast", [])) == 7)
        check("Has crop ET0", w.get("et0_today_mm") is not None)
        print(f"       Location: {w.get('display_location')} | Temp: {w.get('current_temperature_c')}°C | "
              f"ET0: {w.get('et0_today_mm')} mm | Status: {w.get('status')}")
    else:
        check("Honest offline status (no fake 27.5°C fallback)", w.get("status") == "service_unavailable" and "current_temperature_c" not in w)
        print(f"       Offline status verified: {w.get('status')} (zero fabricated telemetry)")

    # ── Test 4: Soil health Tool ────────────
    print("\n[4/15] Soil Health Tool (250m Geospatial Grid)")
    r_s_empty = client.get("/api/tools/soil")
    check("Missing district rejected (HTTP 400)", r_s_empty.status_code == 400)

    r = client.get("/api/tools/soil?district=Mandya&crop=sugarcane")
    check("HTTP 200", r.status_code == 200)
    s = r.get_json()
    if s.get("status") in ("success", "cached_real"):
        check("Has root-zone moisture", isinstance(s.get("moisture_percentage"), (int, float)))
        check("Has 250m mapped pH", isinstance(s.get("ph"), (int, float)))
        check("Has nutrients & OC", "nutrients" in s and s["nutrients"].get("organic_carbon_pct") is not None)
        check("Has 5-depth moisture profile", "root_depths_moisture_pct" in s)
        print(f"       District: {s.get('district')} | Soil: {s.get('soil_type')} | "
              f"Moisture: {s.get('moisture_percentage')}% | pH: {s.get('ph')} | OC: {s['nutrients'].get('organic_carbon_pct')}%")
    else:
        check("Honest offline status (no fake benchmark fallback)", s.get("status") == "service_unavailable" and "ph" not in s)
        print(f"       Offline status verified: {s.get('status')} (zero fabricated soil data)")

    # ── Test 5: Mandi price tool ───────────
    print("\n[5/15] Mandi Price Tool")
    r_m_empty = client.get("/api/tools/mandi?commodity=")
    check("Missing commodity rejected (HTTP 400)", r_m_empty.status_code == 400)

    r = client.get("/api/tools/mandi?commodity=tomato&location=kolar")
    check("HTTP 200", r.status_code == 200)
    m = r.get_json()
    if m.get("status") in ("success", "cached_real"):
        check("Has modal_price", isinstance(m.get("modal_price"), (int, float)) and m.get("modal_price") > 0)
        check("Has selling_advisory", bool(m.get("selling_advisory")))
        print(f"       Commodity: {m.get('commodity')} | Mandi: {m.get('primary_mandi')} | "
              f"Price: ₹{m.get('modal_price')}/qtl | Status: {m.get('status')}")
    else:
        check("Honest offline status (no fake ₹2850 fallback)", m.get("status") == "service_unavailable" and "modal_price" not in m)
        print(f"       Offline status verified: {m.get('status')} (zero fabricated mandi prices)")

    # ── Test 6: Status endpoint ──────────────────────────────
    print("\n[6/15] API Status Endpoint")
    r = client.get("/api/status")
    check("HTTP 200", r.status_code == 200)
    st = r.get_json()
    check("Has status=online", st.get("status") == "online")
    check("Has agent_mode", "agent_mode" in st)
    print(f"       Mode: {st.get('agent_mode')}")

    # ── Test 7: Kannada response ─────────────────────────────
    print("\n[7/15] Kannada Response (No English Leakage)")
    r = client.post("/api/chat", json={
        "query": "ಕೋಲಾರದಲ್ಲಿ ಟೊಮೆಟೊ ಬೆಳೆಗೆ ನೀರು ಹಾಯಿಸಬೇಕೆ? ಮಂಡಿ ದರ ಎಷ್ಟು?",
        "language": "kn"
    })
    check("HTTP 200", r.status_code == 200)
    kn = r.get_json()
    check("Status success", kn.get("status") == "success", kn.get("message", ""))
    check("ಫಸಲ್ ಸಾರಥಿ in response", "ಫಸಲ್ ಸಾರಥಿ" in kn.get("response_text", ""))
    check("ನಮಸ್ಕಾರ in speech", "ನಮಸ್ಕಾರ" in kn.get("speech_text", ""))
    check("No English 'DO NOT IRRIGATE'", "DO NOT IRRIGATE" not in kn.get("response_text", ""))
    check("No English 'HOLD OR DIVERT'", "HOLD OR DIVERT" not in kn.get("response_text", ""))

    # ── Test 8: Hindi response ───────────────────────────────
    print("\n[8/15] Hindi Response (No English Leakage)")
    r = client.post("/api/chat", json={
        "query": "क्या आज बारिश होगी? टमाटर का मंडी भाव क्या है?",
        "language": "hi"
    })
    check("HTTP 200", r.status_code == 200)
    hi = r.get_json()
    check("Status success", hi.get("status") == "success")
    check("फसल सारथी in response", "फसल सारथी" in hi.get("response_text", ""))
    check("नमस्ते in speech", "नमस्ते" in hi.get("speech_text", ""))

    # ── Test 9: Tamil response ───────────────────────────────
    print("\n[9/15] Tamil Response")
    r = client.post("/api/chat", json={
        "query": "கோயம்புத்தூரில் தக்காளி விலை என்ன? இன்று பாசனம் தேவையா?",
        "language": "ta"
    })
    check("HTTP 200", r.status_code == 200)
    ta = r.get_json()
    check("Status success", ta.get("status") == "success")
    check("Tamil header present", "ஃபசல் சாரதி" in ta.get("response_text", ""))
    check("Tamil speech present", "வணக்கம்" in ta.get("speech_text", ""))

    # ── Test 10: Telugu response ─────────────────────────────
    print("\n[10/15] Telugu Response")
    r = client.post("/api/chat", json={
        "query": "గుంటూరులో మిర్చి ధర ఎంత? ఈరోజు నీరు పెట్టాలా?",
        "language": "te"
    })
    check("HTTP 200", r.status_code == 200)
    te = r.get_json()
    check("Status success", te.get("status") == "success")
    check("Telugu header present", "ఫసల్ సారథి" in te.get("response_text", ""))
    check("Telugu speech present", "నమస్కారం" in te.get("speech_text", ""))

    # ── Test 11: Marathi response ────────────────────────────
    print("\n[11/15] Marathi Response")
    r = client.post("/api/chat", json={
        "query": "नाशिकमध्ये कांद्याचा बाजारभाव काय? आज पाणी द्यायचे का?",
        "language": "mr"
    })
    check("HTTP 200", r.status_code == 200)
    mr = r.get_json()
    check("Status success", mr.get("status") == "success")
    check("Marathi header present", "फसल सारथी" in mr.get("response_text", ""))
    check("Marathi speech present", "नमस्कार" in mr.get("speech_text", ""))

    # ── Test 12: TTS endpoint ────────────────────────────────
    print("\n[12/15] TTS Audio Endpoint")
    for lang_code, text in [("kn", "ನಮಸ್ಕಾರ"), ("hi", "नमस्ते"), ("en", "Hello farmer")]:
        r = client.get(f"/api/tts?lang={lang_code}&text={text}")
        check(f"TTS {lang_code} HTTP 200", r.status_code == 200)
    r = client.get("/api/tts?lang=kn&text=")
    check("Empty text returns 400", r.status_code == 400)

    # ── Test 13: Leaf disease diagnostic ─────────────────────
    print("\n[13/15] Leaf Disease Diagnostic (Sample Image)")
    r = client.post("/api/diagnose-sample", json={
        "sample_name": "coffee_rust.jpg",
        "crop_hint": "coffee"
    })
    check("HTTP 200", r.status_code == 200)
    diag = r.get_json()
    check("Status success", diag.get("status") == "success")
    check("Has disease_name", bool(diag.get("disease_name")))
    check("Has confidence_score", diag.get("confidence_score", 0) > 0)
    print(f"       Disease: {diag.get('disease_name')} | Confidence: {diag.get('confidence_score')}%")

    # Reject unknown sample
    r = client.post("/api/diagnose-sample", json={"sample_name": "../../etc/passwd"})
    check("Unknown sample rejected", r.status_code == 400)

    # ── Test 14: Missing location — still responds gracefully ─
    print("\n[14/15] Missing Location Handling")
    r = client.post("/api/chat", json={
        "query": "What is the weather today?",
        "language": "en"
    })
    check("HTTP 200 (no crash)", r.status_code == 200)
    gen = r.get_json()
    check("Status success (graceful)", gen.get("status") == "success")
    # Should not silently pretend a specific location
    check("Response has content", len(gen.get("response_text", "")) > 50)
    check("Does not silently default to Kolar", "kolar" not in gen.get("response_text", "").lower())

    # ── Test 15: Invalid image upload rejected ────────────────
    print("\n[15/15] Invalid Image Upload Validation")
    # Non-image file
    data = {"file": (io.BytesIO(b"This is not an image"), "malicious.exe")}
    r = client.post("/api/upload-leaf", data=data, content_type="multipart/form-data")
    check("Rejected non-image extension", r.status_code == 400)

    # Empty filename
    data = {"file": (io.BytesIO(b""), "")}
    r = client.post("/api/upload-leaf", data=data, content_type="multipart/form-data")
    check("Rejected empty filename", r.status_code == 400)

    # No file at all
    r = client.post("/api/upload-leaf", data={}, content_type="multipart/form-data")
    check("Rejected missing file", r.status_code == 400)

    # ── Test 16: Terrace & Beginner Farming Module ───────────
    print("\n[16/16] Terrace & Beginner Farming Module")
    check("Terrace tab present in HTML", 'id="tab-terrace"' in html)
    r_tp_empty = client.get("/api/tools/terrace/plan")
    check("Terrace plan rejects missing location/dimensions (HTTP 400)", r_tp_empty.status_code == 400)
    r_tg_empty = client.get("/api/tools/terrace/guide")
    check("Terrace guide rejects empty crop (HTTP 400)", r_tg_empty.status_code == 400)
    r_tg = client.get("/api/tools/terrace/guide?crop=methi&language=en")
    check("Terrace guide HTTP 200 for Methi", r_tg.status_code == 200 and r_tg.get_json().get("status") == "success")

    # ── Summary ───────────────────────────────────────────────
    total = PASS + FAIL
    print("\n" + "=" * 60)
    if FAIL == 0:
        print(f"🎉  ALL {total} TESTS PASSED!")
    else:
        print(f"⚠️   {PASS}/{total} PASSED — {FAIL} FAILED")
    print("=" * 60)
    return FAIL == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
