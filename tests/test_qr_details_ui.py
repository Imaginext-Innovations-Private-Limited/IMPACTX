"""Tests for Milestone 12 explainable QR payload details, Swagger schema, and safe UI."""
from pathlib import Path

from fastapi.testclient import TestClient

from scamshield import main


def test_api_qr_details_upi_and_url_and_swagger_schema():
    client = TestClient(main.app)

    # 1. UPI QR details
    r_upi = client.post(
        "/api/analyze",
        json={
            "text": "Scan QR to receive your Rs 1500 refund.",
            "qr_payloads": ["upi://pay?pa=refund@ybl&pn=Refund%20Center&am=1500&cu=INR&tn=Claim"],
        },
    )
    assert r_upi.status_code == 200
    upi_item = r_upi.json()["qr_analysis"]["payloads"][0]
    assert upi_item["qr_type"] == "UPI Pay QR"
    assert upi_item["upi"]["pa"] == "refund@ybl"
    assert upi_item["upi"]["pn"] == "Refund Center"
    assert upi_item["upi"]["am"] == 1500.0
    assert upi_item["upi"]["cu"] == "INR"
    assert upi_item["upi"]["tn"] == "Claim"
    assert upi_item["cross_modal_mismatch"] is True
    assert "not independently verified" in upi_item["unverified_name_note"]

    # 2. URL QR details
    r_url = client.post(
        "/api/analyze",
        json={
            "text": "",
            "qr_payloads": ["https://sbi.co.in.verify-portal.example/login"],
        },
    )
    assert r_url.status_code == 200
    url_item = r_url.json()["qr_analysis"]["payloads"][0]
    assert url_item["qr_type"] == "URL QR"
    assert url_item["protocol"] == "https"
    assert url_item["registered_domain"] == "verify-portal.example"
    assert "url_assessment" in url_item

    # 3. Other QR type (plain text)
    r_txt = client.post(
        "/api/analyze",
        json={"text": "", "qr_payloads": ["WIFI:T:WPA;S:GuestNet;P:1234;;"]},
    )
    assert r_txt.status_code == 200
    txt_item = r_txt.json()["qr_analysis"]["payloads"][0]
    assert txt_item["qr_type"] == "Plain Text QR"
    assert txt_item["category"] == "plain_text"

    # 4. Swagger / OpenAPI schema visibility
    schema = client.get("/openapi.json").json()
    assert "AnalysisResponse" in schema["components"]["schemas"]
    assert "QRAnalysisOut" in schema["components"]["schemas"]
    assert "QRPayloadDetail" in schema["components"]["schemas"]


def test_frontend_qr_details_panel_is_expandable_and_inert():
    html = Path("static/index.html").read_text(encoding="utf-8")
    js = Path("static/app.js").read_text(encoding="utf-8")
    assert '<details id="qr-details"' in html
    assert 'id="qr-detail-list"' in html
    assert "renderQrDetails" in js
    assert "innerHTML" not in js
