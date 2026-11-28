"""Tests for Milestone 11 automatic content routing, headerless phishing, and UI accessibility."""
from pathlib import Path

from fastapi.testclient import TestClient

from scamshield import main
from scamshield.engine import analyze


def test_auto_routing_never_fabricates_sms_or_whatsapp():
    plain = analyze("Hello team, please review the agenda before our 3 PM sync.")
    assert plain["channel"] == "auto"
    assert plain["level"] == "no_clear_signal"


def test_auto_routing_headerless_phishing_url_email_qr_upi():
    # Headerless polished phishing text -> caught at review without escalating benign text
    headerless = analyze(
        "Dear Valued Client, our quarterly compliance review requires confirming your online "
        "banking preferences. Please sign in at our verification portal."
    )
    assert headerless["level"] in {"review", "caution", "high"}

    # Standalone URL
    url_res = analyze("http://192.0.2.44/sbi-kyc/verify-login")
    assert url_res["level"] in {"caution", "high"}

    # Email with headers
    email_res = analyze(
        "From: HDFC Bank <alerts@hdfc-notice.example>\n"
        "Subject: Account Verification\n\nPlease sign in to confirm your preferences."
    )
    assert email_res["channel"] == "email"
    assert email_res["level"] in {"caution", "high"}

    # UPI URI
    upi_res = analyze("upi://pay?pa=scammer@ybl&pn=Refund&am=1500&cu=INR")
    assert upi_res["channel"] == "upi"

    # QR payload
    qr_res = analyze(
        "Scan QR to receive Rs 1500 refund.",
        qr_payloads=["upi://pay?pa=scammer@ybl&pn=Refund&am=1500&cu=INR"],
    )
    assert qr_res["channel"] == "image"
    assert qr_res["level"] == "high"


def test_api_default_channel_auto_and_ui_accessibility():
    client = TestClient(main.app)
    r = client.post("/api/analyze", json={"text": "https://icicibank.com.portal-auth.example/session"})
    assert r.status_code == 200
    assert r.json()["level"] in {"caution", "high"}

    html = Path("static/index.html").read_text(encoding="utf-8")
    css = Path("static/styles.css").read_text(encoding="utf-8")
    assert '<details class="advanced-options">' in html
    assert '<option value="auto" selected>' in html
    assert 'id="ocr-auto" checked' in html
    assert ".tool-area select" in css and ".voice-btn" in css and ".sub-tab" in css
