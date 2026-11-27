"""
Automated Backend Smoke Test Suite for Farm Advisor (Sprint 5).
Tests all critical endpoints end-to-end using FastAPI's TestClient:
1. POST /api/scan across all 4 modes (crop, disease, agrochemical, soil)
2. POST /api/voice-query with Kannada (kn-IN) and English (en-IN) text queries
3. GET /api/weather (16-day forecast + farm action advisories)
4. GET /api/markets/Paddy and GET /api/markets/Areca (14-day history, cross-mandi comparison, 6-year chart series)
5. GET /api/news (all 9 agricultural categories)
6. GET /api/dairy (Nandini, Amul, Dodla, Heritage, Tirumala milk rates, breeds, rations, semen matching, symptom advisor)
7. GET /api/notifications and checklist persistence
8. GET & POST /api/finance/ledger, /api/finance/profit-comparison, and /api/finance/advisory
"""
import io
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_check():
    """Verify backend health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "modules" in data


# 1. 4-Mode Scanner Smoke Tests
@pytest.mark.parametrize("mode,expected_field", [
    ("crop", "detected_crop"),
    ("disease", "disease_name"),
    ("agrochemical", "product_name"),
    ("soil", "soil_type"),
])
def test_scan_all_four_modes(mode, expected_field):
    """POST /api/scan across all 4 modes (crop, disease, agrochemical, soil)."""
    dummy_image = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00test_image_data")
    response = client.post(
        "/api/scan",
        files={"file": (f"test_{mode}.jpg", dummy_image, "image/jpeg")},
        data={"mode": mode},
    )
    assert response.status_code == 200, f"Scan failed for mode {mode}: {response.text}"
    data = response.json()
    assert data["mode"] == mode
    assert data["status"] in ["live", "demo"]
    assert "result" in data
    assert expected_field in data["result"], f"Expected field '{expected_field}' missing in {mode} result"


# 2. Voice Query Smoke Tests (Indic Speech Guardrails & Multilingual)
@pytest.mark.parametrize("query_text,language_code", [
    ("ಭತ್ತದ ಪ್ರಸ್ತುತ ಮಾರುಕಟ್ಟೆ ದರ ಎಷ್ಟು?", "kn-IN"),
    ("What is the current APMC mandi price of Paddy and Areca?", "en-IN"),
])
def test_voice_query_kannada_and_english(query_text, language_code):
    """POST /api/voice-query with Kannada (kn-IN) and English (en-IN) text queries."""
    response = client.post(
        "/api/voice-query",
        json={"query": query_text, "language": language_code},
    )
    assert response.status_code == 200, f"Voice query failed for {language_code}: {response.text}"
    data = response.json()
    assert "response" in data and len(data["response"]) > 0
    assert data["language"] == language_code
    assert "keyterms" in data and len(data["keyterms"]) >= 5
    # Verify keyterms include core agricultural domain terms
    for term in ["Paddy", "Areca", "Mandi"]:
        assert term in data["keyterms"]


# 3. Weather 16-Day Forecast & Advisories
def test_weather_forecast_and_advisories():
    """GET /api/weather (16-day forecast + farm action advisories)."""
    response = client.get("/api/weather")
    assert response.status_code == 200, f"Weather API failed: {response.text}"
    data = response.json()
    assert "daily" in data
    assert len(data["daily"]) == 16, f"Expected 16 days forecast, got {len(data['daily'])}"
    assert "advisories" in data and len(data["advisories"]) > 0
    assert "current" in data
    assert "soil_moisture" in data["current"] or "soil_moisture_pct" in data["current"]


# 4. Commodity Markets Analytics (Paddy & Areca)
@pytest.mark.parametrize("commodity", ["Paddy", "Areca"])
def test_market_analytics_paddy_and_areca(commodity):
    """GET /api/markets/Paddy and GET /api/markets/Areca."""
    response = client.get(f"/api/markets/{commodity}")
    assert response.status_code == 200, f"Market API failed for {commodity}: {response.text}"
    data = response.json()
    # 14-day history
    assert "two_week_history" in data
    assert len(data["two_week_history"]) == 14, f"Expected 14-day history, got {len(data['two_week_history'])}"
    # Cross-mandi comparison
    assert "cross_mandi_comparison" in data and len(data["cross_mandi_comparison"]) > 0
    # 6-year chart series
    assert "six_year_seasonal" in data and len(data["six_year_seasonal"]) > 0
    assert "monthly_pattern" in data and len(data["monthly_pattern"]) == 12
    assert "selling_advisory" in data


# 5. Agricultural News (All 9 Categories)
def test_news_all_nine_categories():
    """GET /api/news (all 9 agricultural categories)."""
    response = client.get("/api/news")
    assert response.status_code == 200, f"News API failed: {response.text}"
    data = response.json()
    assert "articles" in data and len(data["articles"]) > 0
    assert "categories" in data
    assert len(data["categories"]) == 9, f"Expected 9 categories, got {len(data['categories'])}"

    # Check categories endpoint
    cat_response = client.get("/api/news/categories")
    assert cat_response.status_code == 200
    categories = cat_response.json()
    assert len(categories) == 9
    category_ids = {c["id"] for c in categories}
    assert category_ids == set(range(1, 10))


# 6. Animal Husbandry & Dairy Module
def test_dairy_rates_breeds_rations_semen_symptoms():
    """
    GET /api/dairy:
    Nandini, Amul, Dodla, Heritage, Tirumala milk rates, breeds, rations, semen matching, symptom advisor.
    """
    response = client.get("/api/dairy")
    assert response.status_code == 200, f"Dairy API failed: {response.text}"
    data = response.json()

    # Procurement rates for major dairies
    assert "procurement_rates" in data and len(data["procurement_rates"]) > 0
    dairy_names = [r["dairy_name"].lower() for r in data["procurement_rates"]]
    for expected_brand in ["nandini", "amul", "dodla", "heritage", "tirumala"]:
        assert any(expected_brand in d for d in dairy_names), f"Missing dairy brand '{expected_brand}' in rates"

    # Breeds
    assert "breeds" in data and len(data["breeds"]) > 0

    # Rations (feed plans)
    assert ("rations" in data or "feed_plans" in data)
    rations = data.get("rations") or data.get("feed_plans")
    assert len(rations) > 0

    # Semen matching (breeding guide)
    assert ("semen_matching" in data or "breeding_guide" in data)
    semen = data.get("semen_matching") or data.get("breeding_guide")
    assert len(semen) > 0

    # Symptom / disease advisor
    assert ("symptom_advisor" in data or "disease_advisor" in data)
    symptoms = data.get("symptom_advisor") or data.get("disease_advisor")
    assert len(symptoms) > 0


# 7. Notifications & Document Checklist Persistence
def test_notifications_and_checklist_persistence():
    """GET /api/notifications and checklist persistence."""
    response = client.get("/api/notifications")
    assert response.status_code == 200, f"Notifications API failed: {response.text}"
    data = response.json()
    assert "notifications" in data and len(data["notifications"]) > 0

    notif = data["notifications"][0]
    notif_id = notif["id"]
    checklist = notif.get("checklist", [])
    assert len(checklist) > 0, "Notification has no checklist items"
    doc_key = checklist[0]["doc_key"]

    # Toggle to True
    toggle_res = client.post(
        f"/api/notifications/{notif_id}/checklist/{doc_key}",
        json={"is_completed": True},
    )
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_completed"] is True

    # Verify persisted in subsequent GET
    get_res = client.get("/api/notifications")
    updated_notif = next(n for n in get_res.json()["notifications"] if n["id"] == notif_id)
    updated_item = next(c for c in updated_notif["checklist"] if c["doc_key"] == doc_key)
    assert updated_item["is_completed"] is True, "Checklist completion status was not persisted"


# 8. Farm Finance Ledger, Profit Comparison, and Advisory (GET & POST)
def test_finance_endpoints_get_and_post():
    """GET & POST /api/finance/ledger, /api/finance/profit-comparison, and /api/finance/advisory."""
    # 1. Ledger GET
    ledger_get = client.get("/api/finance/ledger")
    assert ledger_get.status_code == 200
    ledger_data = ledger_get.json()
    assert "balance_sheet" in ledger_data
    assert "entries" in ledger_data

    # 2. Ledger POST
    new_entry = {
        "entry_date": "2026-11-25",
        "crop_tag": "Paddy",
        "entry_type": "expense",
        "category": "cultivation",
        "sub_category": "fertilizer",
        "description": "Organic Neem Cake 50kg for Paddy Tillering",
        "amount": 1400.0,
        "notes": "Purchased from PACS Davangere",
    }
    ledger_post = client.post("/api/finance/ledger", json=new_entry)
    assert ledger_post.status_code == 200
    assert ledger_post.json().get("success") is True

    # 3. Profit Comparison GET & POST
    profit_get = client.get("/api/finance/profit-comparison?soil_type=Red+Sandy+Loam&temp_c=27.0")
    assert profit_get.status_code == 200
    assert "recommended_alternatives" in profit_get.json()

    profit_post = client.post("/api/finance/profit-comparison", json={"soil_type": "Clay Loam", "temp_c": 26.0})
    assert profit_post.status_code == 200
    assert "recommended_alternatives" in profit_post.json()

    # 4. Credit Advisory GET & POST
    advisory_get = client.get("/api/finance/advisory")
    assert advisory_get.status_code == 200
    assert "credit_pillars" in advisory_get.json()
    assert len(advisory_get.json()["credit_pillars"]) >= 6

    advisory_post = client.post("/api/finance/advisory", json={"crop": "Paddy", "location": "Davangere"})
    assert advisory_post.status_code == 200
    assert "credit_pillars" in advisory_post.json()


# 9. Meta WhatsApp Cloud API Webhook Verification & Message Simulator
def test_whatsapp_webhook_verification():
    """GET /api/whatsapp/webhook verification challenge."""
    # Valid subscription challenge
    response = client.get(
        "/api/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "krishimitra_verify",
            "hub.challenge": "115325236",
        },
    )
    assert response.status_code == 200
    assert response.text == "115325236"

    # Invalid token mismatch -> 403 Forbidden
    bad_resp = client.get(
        "/api/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "99999",
        },
    )
    assert bad_resp.status_code == 403


def test_whatsapp_simulate_text():
    """POST /api/whatsapp/simulate with text query."""
    sim_payload = {
        "type": "text",
        "text": "What is the current mandi price of Paddy?",
        "from": "919876543210",
    }
    response = client.post("/api/whatsapp/simulate", json=sim_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    result = data["result"]
    assert result["type"] == "text"
    assert "reply_text" in result
    assert len(result["reply_text"]) > 0


def test_whatsapp_simulate_audio():
    """POST /api/whatsapp/simulate with voice note."""
    sim_payload = {
        "type": "audio",
        "from": "919876543210",
    }
    response = client.post("/api/whatsapp/simulate", json=sim_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    result = data["result"]
    assert result["type"] == "audio"
    assert "reply_text" in result
    assert len(result["reply_text"]) > 0
    assert "reply_audio_base64" in result
    assert result.get("voice") is True



def test_whatsapp_simulate_image_disease_and_caption_modes():
    """POST /api/whatsapp/simulate with leaf image (disease, soil, agrochemical)."""
    # 1. Disease by default
    resp_disease = client.post(
        "/api/whatsapp/simulate",
        json={"type": "image", "caption": "Leaf spots on tomato plant"},
    )
    assert resp_disease.status_code == 200
    res_d = resp_disease.json()["result"]
    assert res_d["mode"] == "disease"
    assert "Diagnosis" in res_d["reply_text"] or "Treatment" in res_d["reply_text"]

    # 2. Agrochemical caption
    resp_chem = client.post(
        "/api/whatsapp/simulate",
        json={"type": "image", "caption": "Check fertilizer / pesticide bottle dosage"},
    )
    assert resp_chem.status_code == 200
    res_c = resp_chem.json()["result"]
    assert res_c["mode"] == "agrochemical"
    assert "Dosage" in res_c["reply_text"]
    assert "Per Acre" in res_c["reply_text"]
    assert "Per 200L Barrel" in res_c["reply_text"]

    # 3. Soil caption
    resp_soil = client.post(
        "/api/whatsapp/simulate",
        json={"type": "image", "caption": "Red laterite soil sample test"},
    )
    assert resp_soil.status_code == 200
    res_s = resp_soil.json()["result"]
    assert res_s["mode"] == "soil"
    assert "Soil" in res_s["reply_text"]


def test_whatsapp_webhook_incoming_post():
    """POST /api/whatsapp/webhook with standard WhatsApp Cloud API payload."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550234567",
                                "phone_number_id": "1234567890",
                            },
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "wamid.HBgL...",
                                    "timestamp": "1732523456",
                                    "text": {"body": "Areca price update"},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }
    response = client.post("/api/whatsapp/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_whatsapp_webhook_incoming_audio_voice_note_mocked_graph_api(monkeypatch):
    """
    Test live Meta WhatsApp Cloud API two-way voice notes with mocked httpx calls:
    1. Send read receipt for incoming audio message
    2. Query GET https://graph.facebook.com/v26.0/{media_id} for media metadata
    3. Download raw OGG audio bytes from the returned URL
    4. Transcribe + synthesize reply via voice router
    5. Convert to OGG/Opus & upload to POST https://graph.facebook.com/v26.0/{phone_number_id}/media
    6. Send voice-note playable bubble ({"type": "audio", "audio": {"id": uploaded_media_id, "voice": true}})
    7. Send follow-up concise text summary
    """
    import httpx
    import config

    # Enable mock WhatsApp credentials
    monkeypatch.setattr(config, "WHATSAPP_ACCESS_TOKEN", "mock_wa_access_token_12345")
    monkeypatch.setattr(config, "WHATSAPP_PHONE_NUMBER_ID", "1234567890")

    recorded_calls = []

    # Mock handler for all external Graph API endpoints
    def custom_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        recorded_calls.append({"method": request.method, "url": url_str})

        # 1. Media metadata lookup: GET /v26.0/incoming_voice_media_123
        if request.method == "GET" and "incoming_voice_media_123" in url_str:
            return httpx.Response(
                status_code=200,
                json={"url": "https://lookaside.fbsbx.com/whatsapp_business/media/download_audio_bytes"},
            )

        # 2. Binary audio download from returned URL
        if request.method == "GET" and "download_audio_bytes" in url_str:
            # Minimal mock OggS stream bytes
            dummy_ogg = b"OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00mock_opus_audio"
            return httpx.Response(
                status_code=200,
                content=dummy_ogg,
                headers={"Content-Type": "audio/ogg"},
            )

        # 3. Media upload: POST /v26.0/1234567890/media
        if request.method == "POST" and "/media" in url_str:
            return httpx.Response(status_code=200, json={"id": "uploaded_ogg_media_999"})

        # 4. Message sending: POST /v26.0/1234567890/messages (read receipt, audio voice note, text summary)
        if request.method == "POST" and "/messages" in url_str:
            body = request.read()
            import json as _json
            try:
                parsed_body = _json.loads(body)
                recorded_calls.append({"sent_body": parsed_body})
            except Exception:
                pass
            return httpx.Response(status_code=200, json={"messages": [{"id": "wamid.outbound_123"}]})

        return httpx.Response(status_code=200, json={"status": "ok"})

    transport = httpx.MockTransport(custom_handler)

    # Monkeypatch AsyncClient in whatsapp_bot to use MockTransport
    orig_async_client = httpx.AsyncClient

    def mock_async_client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return orig_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mock_async_client_factory)

    audio_webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550234567",
                                "phone_number_id": "1234567890",
                            },
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "wamid.inbound_audio_001",
                                    "timestamp": "1732523456",
                                    "type": "audio",
                                    "audio": {
                                        "id": "incoming_voice_media_123",
                                        "mime_type": "audio/ogg; codecs=opus",
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    response = client.post("/api/whatsapp/webhook", json=audio_webhook_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify calls made
    urls = [c.get("url") for c in recorded_calls if "url" in c]
    assert any("incoming_voice_media_123" in u for u in urls), "Media metadata URL not requested"
    assert any("download_audio_bytes" in u for u in urls), "Media download URL not fetched"
    assert any("/media" in u for u in urls), "Outbound OGG media was not uploaded to Meta"
    assert any("/messages" in u for u in urls), "Messages endpoint was not called"

    # Verify message bodies sent (read receipt, audio with voice=True, and summary text)
    sent_bodies = [c.get("sent_body") for c in recorded_calls if "sent_body" in c]
    has_read_receipt = any(b.get("status") == "read" and b.get("message_id") == "wamid.inbound_audio_001" for b in sent_bodies)
    assert has_read_receipt, f"Read receipt was not sent: {sent_bodies}"

    has_voice_note = any(
        b.get("type") == "audio"
        and b.get("audio", {}).get("id") == "uploaded_ogg_media_999"
        and b.get("audio", {}).get("voice") is True
        for b in sent_bodies
    )
    assert has_voice_note, f"Outbound voice note with voice=true was not sent: {sent_bodies}"

    has_text_summary = any(b.get("type") == "text" for b in sent_bodies)
    assert has_text_summary, f"Text summary follow-up was not sent: {sent_bodies}"


