"""End-to-end tests for multimodal QR, UPI, and URL ML/threat-DB integration."""
import io

import qrcode
from fastapi.testclient import TestClient

from scamshield import main
from scamshield.engine import analyze


def _qr_png(payload: str) -> bytes:
    qr = qrcode.QRCode(box_size=8, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_engine_quishing_cross_modal_high_risk():
    res = analyze(
        "Congratulations! Scan this QR code to receive your Rs 2500 cashback refund immediately.",
        channel="image",
        language="en",
        qr_payloads=["upi://pay?pa=scammer@ybl&pn=Cashback&am=2500&cu=INR"],
    )
    assert res["level"] == "high"
    assert res["score"] >= 7
    ids = {i["id"] for i in res["indicators"]}
    assert "qr_receive_mismatch" in ids
    assert res["qr_analysis"]["qr_count"] == 1


def test_engine_qr_apk_high_risk_without_ocr_text():
    res = analyze(
        "",
        channel="image",
        language="en",
        qr_payloads=["http://192.168.1.10/rbi-update.apk"],
    )
    assert res["level"] in {"caution", "high"}
    ids = {i["id"] for i in res["indicators"]}
    assert "qr_apk_download" in ids


def test_api_ocr_decodes_qr_and_analyze_uses_qr_payloads():
    client = TestClient(main.app)
    payload = "upi://pay?pa=fraud@okaxis&pn=KYC%20Desk&am=1999&cu=INR"
    png_bytes = _qr_png(payload)
    ocr_resp = client.post(
        "/api/ocr?language=en",
        files={"file": ("qr.png", png_bytes, "image/png")},
    )
    assert ocr_resp.status_code == 200
    ocr_data = ocr_resp.json()
    assert payload in ocr_data["qr_payloads"]
    assert ocr_data["qr_analysis"][0]["type"] == "upi_payment"

    an_resp = client.post(
        "/api/analyze",
        json={
            "text": "Your bank KYC is suspended. Scan the QR to verify.",
            "channel": "image",
            "language": "en",
            "qr_payloads": ocr_data["qr_payloads"],
        },
    )
    assert an_resp.status_code == 200
    an_data = an_resp.json()
    assert an_data["level"] == "high"
    assert "qr_authority_mismatch" in {i["id"] for i in an_data["indicators"]}
