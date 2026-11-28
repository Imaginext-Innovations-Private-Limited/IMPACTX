"""Regression tests ensuring ordinary UPI payment QRs do not trigger false positives."""
import io

import qrcode
from fastapi.testclient import TestClient

from scamshield import cloud, main
from scamshield.engine import analyze


def _upi_qr_bytes(payload: str) -> bytes:
    qr = qrcode.QRCode(box_size=8, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_benign_upi_qr_offline_no_false_positive_and_details_preserved():
    for payload in (
        "upi://pay?pa=merchant@okaxis&pn=Local%20Shop&cu=INR",
        "upi://pay?pa=merchant@okaxis&pn=Local%20Shop&am=250&cu=INR&tn=Coffee",
    ):
        res = analyze("", channel="image", language="en", qr_payloads=[payload])
        assert res["level"] == "no_clear_signal"
        assert res["score"] == 0
        assert res["indicators"] == []
        upi_item = res["qr_analysis"]["payloads"][0]
        assert upi_item["upi"]["pa"] == "merchant@okaxis"
        assert upi_item["upi"]["pn"] == "Local Shop"
        assert upi_item["upi"]["cu"] == "INR"
        assert upi_item["upi"]["action"] == "pay"
        assert "not independently verified" in upi_item["unverified_name_note"]


def test_ocr_symbol_noise_with_benign_upi_qr_does_not_escalate():
    noise = "| [] # @ 12 / \\ == -- _ * ^ %"
    res = analyze(
        noise,
        channel="image",
        language="en",
        qr_payloads=["upi://pay?pa=shop@ybl&pn=Tea%20Stall&cu=INR"],
    )
    assert res["level"] == "no_clear_signal"
    assert res["indicators"] == []


def test_benign_upi_qr_hybrid_mode_not_escalated(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    class FakeBenignAssessment:
        level = "no_clear_signal"
        category = ""
        findings = []

    monkeypatch.setattr(cloud, "ask", lambda *a, **kw: FakeBenignAssessment())
    client = TestClient(main.app)
    r = client.post(
        "/api/analyze",
        json={
            "text": "",
            "channel": "image",
            "language": "en",
            "cloud_consent": True,
            "qr_payloads": ["upi://pay?pa=shop@ybl&pn=Tea%20Stall&am=40&cu=INR"],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["level"] == "no_clear_signal"
    assert body["qr_analysis"]["payloads"][0]["upi"]["pa"] == "shop@ybl"
    assert body["qr_analysis"]["payloads"][0]["upi"]["am"] == 40.0
