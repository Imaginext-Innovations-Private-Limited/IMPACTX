"""Run identical privacy-safe test cases in Offline and Online modes.

Never substitutes mocked results for live API calls; reports exact provider
status (unavailable / success / fallback) and per-case latency.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from fastapi.testclient import TestClient

from scamshield import live_reputation, main

CASES = [
    ("polished_phishing_email", "email", "From: State Bank of India <advisory@sbi-client-portal.example>\nSubject: Quarterly Confirmation\n\nDear client, please sign in at https://sbi-client-portal.example/confirm to review your profile.", None),
    ("genuine_professional_email", "email", "From: Priya Sharma <priya@acme-consulting.example>\nSubject: Q4 Architecture Sync\n\nHi team, please review the agenda before Thursday's 3 PM meeting.", None),
    ("digital_arrest_scam", "call", "I am a CBI officer. Your Aadhaar is linked to money laundering. You are under digital arrest. Stay on video call and transfer Rs 25000 immediately.", None),
    ("upi_refund_fraud", "upi", "Congratulations! Your Rs 3000 cashback is waiting. Enter your UPI PIN and approve the collect request to receive money.", None),
    ("quishing_upi_refund", "image", "Scan this QR code to receive your Rs 1500 merchant refund.", ["upi://pay?pa=refunddesk@ybl&pn=Refund%20Desk&am=1500&cu=INR"]),
    ("suspicious_phishing_url", "sms", "http://192.0.2.44/sbi-kyc/verify-login", None),
    ("unseen_phishing_url", "sms", "https://icicibank.com.portal-auth.example/session", None),
    ("legitimate_official_url", "sms", "https://www.sbi.co.in/web/personal-banking", None),
    ("sender_impersonation", "email", "From: HDFC Bank <alerts@hdfcbank.com>\nReply-To: audit@external-desk.example\nSubject: Profile Update\n\nPlease reply with your updated correspondence address.", None),
]


def main_run() -> None:
    client = TestClient(main.app)
    groq_ok = bool(os.environ.get("GROQ_API_KEY", "").strip())
    gsb_ok = live_reputation.configured()

    rows = []
    for name, channel, text, qr in CASES:
        payload_off = {"text": text, "channel": channel, "language": "en", "cloud_consent": False, "qr_payloads": qr}
        t0 = time.perf_counter()
        off = client.post("/api/analyze", json=payload_off).json()
        off_ms = round((time.perf_counter() - t0) * 1000, 2)

        payload_on = {"text": text, "channel": channel, "language": "en", "cloud_consent": True, "qr_payloads": qr}
        t1 = time.perf_counter()
        on = client.post("/api/analyze", json=payload_on).json()
        on_ms = round((time.perf_counter() - t1) * 1000, 2)

        rows.append({
            "case": name,
            "offline_level": off["level"],
            "offline_ms": off_ms,
            "online_level": on["level"],
            "online_mode": on["analysis_mode"],
            "online_ms": on_ms,
            "live_url_status": (on.get("live_reputation") or {}).get("status", "not_requested"),
            "engines": on.get("engine_contributions", {}),
        })

    report = {
        "groq_configured": groq_ok,
        "google_safe_browsing_configured": gsb_ok,
        "cases": rows,
    }
    out = Path(__file__).resolve().parent.parent / "benchmark" / "live_offline_verification.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main_run()
