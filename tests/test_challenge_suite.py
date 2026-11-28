"""Dedicated challenge suite for polished phishing, identity, URL, QR, and zero-key UX.

Uses only harmless reserved domains (.example, .invalid) and RFC 5737 IPs (192.0.2.x).
"""
import io
from pathlib import Path

import httpx
import pytest
import qrcode
from fastapi.testclient import TestClient

from scamshield import main
from scamshield.engine import analyze
from scamshield.identity_verifier import parse_eml_bytes


def _qr_bytes(payload: str) -> bytes:
    qr = qrcode.QRCode(box_size=8, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


POLISHED_PHISHING_CASES = [
    (
        "polished_phishing_email_no_scam_keywords",
        "From: State Bank of India <advisory@sbi-client-portal.example>\n"
        "Subject: Quarterly Compliance Confirmation\n\n"
        "Dear Valued Client, our records indicate your annual profile confirmation is pending. "
        "Please sign in via our portal to review your preferences: https://sbi-client-portal.example/confirm",
        None,
        None,
    ),
    (
        "sender_reply_to_mismatch",
        "From: HDFC Bank Corporate <notices@hdfcbank.com>\n"
        "Reply-To: desk@audit-response.example\n"
        "Subject: Account Preference Update\n\n"
        "Please reply with your updated correspondence address for our annual audit.",
        None,
        None,
    ),
    (
        "misleading_subdomain",
        "Dear customer, review your account statement at https://icicibank.com.portal-auth.example/session",
        None,
        None,
    ),
    (
        "deceptive_hyperlink_eml",
        None,
        b"From: Axis Bank <alerts@axisbank.com>\r\n"
        b"Subject: Scheduled Maintenance Notice\r\n"
        b"Content-Type: text/html; charset=utf-8\r\n\r\n"
        b"<html><body><p>Confirm your session at "
        b"<a href='https://session-harvest.example/login'>https://www.axisbank.com/netbanking</a>"
        b"</p></body></html>",
        None,
    ),
    (
        "standalone_suspicious_url",
        "http://192.0.2.44/sbi-kyc/verify-login",
        None,
        None,
    ),
    (
        "qr_only_apk_input",
        "",
        None,
        ["http://192.0.2.99/secure-update.apk"],
    ),
    (
        "refund_message_with_outgoing_upi_qr",
        "Your merchant refund of Rs 1,500 is approved. Scan the attached QR to receive funds.",
        None,
        ["upi://pay?pa=refunddesk@ybl&pn=Refund%20Desk&am=1500&cu=INR"],
    ),
]

BENIGN_CHALLENGE_CASES = [
    (
        "legitimate_professional_email",
        "From: Priya Sharma <priya@acme-consulting.example>\n"
        "Subject: Q4 Architecture Review\n\n"
        "Hi team, please review the attached agenda before Thursday's 3 PM architecture sync.",
        None,
        None,
    ),
    (
        "legitimate_official_domain_notice",
        "From: HDFC Bank <alerts@hdfcbank.com>\n"
        "Subject: Monthly e-Statement\n\n"
        "Your monthly e-statement is available in the official mobile banking application.",
        None,
        None,
    ),
    (
        "standalone_benign_official_url",
        "https://www.sbi.co.in/web/personal-banking",
        None,
        None,
    ),
]


@pytest.mark.parametrize("name,text,eml_bytes,qr_payloads", POLISHED_PHISHING_CASES)
def test_challenge_polished_attacks_detected(name, text, eml_bytes, qr_payloads):
    if eml_bytes is not None:
        parsed = parse_eml_bytes(eml_bytes)
        res = analyze(parsed["combined_text"], channel="email", language="en", email_meta=parsed)
    else:
        res = analyze(text, channel="image" if qr_payloads else "email", language="en", qr_payloads=qr_payloads)
    assert res["level"] in {"caution", "high"}, f"{name} missed: got {res['level']}"


@pytest.mark.parametrize("name,text,eml_bytes,qr_payloads", BENIGN_CHALLENGE_CASES)
def test_challenge_benign_cases_not_escalated(name, text, eml_bytes, qr_payloads):
    res = analyze(text, channel="email", language="en", qr_payloads=qr_payloads)
    assert res["level"] in {"no_clear_signal", "review"}, f"{name} false positive: {res['level']}"


def test_challenge_eml_upload_and_missing_cloud_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    client = TestClient(main.app)
    eml = (
        b"From: Paytm Support <help@paytm-verify-desk.example>\r\n"
        b"Reply-To: external@collect-reply.example\r\n"
        b"Subject: Merchant Verification\r\n\r\n"
        b"Please review your merchant settlement details."
    )
    up = client.post("/api/parse-email", files={"file": ("notice.eml", eml, "message/rfc822")})
    assert up.status_code == 200
    up_data = up.json()

    an = client.post(
        "/api/analyze",
        json={
            "text": up_data["text"],
            "channel": "email",
            "language": "en",
            "cloud_consent": True,
            "email_meta": up_data["email_meta"],
        },
    )
    assert an.status_code == 200
    body = an.json()
    assert body["analysis_mode"] == "offline_fallback"
    assert body["level"] in {"caution", "high"}


def test_challenge_cloud_failure_preserves_local_finding(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-never-used-real")
    def fail_post(*args, **kwargs):
        raise httpx.TimeoutException("simulated timeout")
    monkeypatch.setattr(httpx, "post", fail_post)

    client = TestClient(main.app)
    an = client.post(
        "/api/analyze",
        json={
            "text": "From: SBI <alert@sbi-desk.example>\nPlease confirm your profile.",
            "channel": "email",
            "language": "en",
            "cloud_consent": True,
        },
    )
    assert an.status_code == 200
    body = an.json()
    assert body["analysis_mode"] == "offline_fallback"
    assert body["level"] in {"caution", "high"}


def test_challenge_auto_protect_stale_cancellation_and_no_keys_in_js():
    js = Path("static/app.js").read_text(encoding="utf-8")
    html = Path("static/index.html").read_text(encoding="utf-8")
    assert 'id="auto-protect"' in html
    assert "AbortController" in js
    assert "pendingRequest.abort()" in js
    assert "scheduleAutoProtect" in js
    assert "lastSignature" in js
    assert "gsk_" not in js and "GROQ_API_KEY" not in js and "SARVAM_API_KEY" not in js
