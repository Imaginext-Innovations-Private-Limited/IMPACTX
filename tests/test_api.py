from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from scamshield.main import app

client=TestClient(app)

def test_home_and_assets():
    r=client.get("/")
    assert r.status_code==200
    assert "ScamShield AI" in r.text
    assert client.get("/static/app.js").status_code==200
    assert client.get("/static/styles.css").status_code==200

def test_health():
    assert client.get("/api/health").json()["status"]=="ok"

def test_analysis_json():
    r=client.post("/api/analyze",json={"text":"Enter your UPI PIN to receive your cashback refund immediately", "channel":"upi"})
    assert r.status_code==200
    assert r.json()["level"]=="high"
    assert r.json()["indicators"]

def test_input_validation():
    assert client.post("/api/analyze",json={"text":""}).status_code==422
    assert client.post("/api/analyze",json={"text":"a"*6001}).status_code==422
    assert client.post("/api/analyze",json={"text":"valid", "channel":"telegram"}).status_code==422

def test_no_server_storage_history_endpoint():
    assert client.get("/api/history").status_code==404

def test_reject_unsupported_image():
    r=client.post("/api/ocr",files={"file":("bad.txt",b"hello", "text/plain")})
    assert r.status_code==415

def test_reject_malformed_image():
    r=client.post("/api/ocr",files={"file":("bad.png",b"not a png", "image/png")})
    assert r.status_code==422

def test_reject_too_large_image():
    r=client.post("/api/ocr",files={"file":("huge.png",b"x"*(4*1024*1024+5), "image/png")})
    assert r.status_code==413

def test_ocr_english_if_available():
    try:
        from PIL import Image, ImageDraw
        import pytesseract
        _=pytesseract.get_tesseract_version()
    except Exception:
        pytest.skip("Tesseract not installed")
    im=Image.new("RGB",(760,125),"white")
    ImageDraw.Draw(im).text((20,25),"Share your OTP right now",fill="black",stroke_width=1)
    bio=BytesIO(); im.save(bio,"PNG")
    r=client.post("/api/ocr",files={"file":("message.png",bio.getvalue(),"image/png")})
    assert r.status_code==200, r.text
    assert len(r.json()["text"])>5


def test_api_returns_complaint_and_entities():
    from fastapi.testclient import TestClient
    from scamshield.main import app
    r = TestClient(app).post("/api/analyze", json={"text": "Your SBI account will be blocked today. Update PAN: http://sbi-kyc-update.xyz/login"})
    assert r.status_code == 200
    body = r.json()
    assert body["level"] == "high"
    assert "COMPLAINT DRAFT" in body["complaint"]
    assert body["entities"]["urls"]


def test_api_does_not_disclose_otp_in_displayed_indicators():
    r=client.post("/api/analyze",json={"text":"Your OTP is 123456. Share OTP 123456 with our support desk to verify your account immediately."})
    assert r.status_code==200
    body=r.json()
    assert body["level"]=="high"
    assert "123456" not in str(body["indicators"])
    assert "123456" not in body["complaint"]
