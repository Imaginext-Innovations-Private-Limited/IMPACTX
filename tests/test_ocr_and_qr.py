"""Verify actual Tesseract OCR + OpenCV QR decoding together on a combined screenshot."""
import io
import os
from pathlib import Path

import pytest
import qrcode
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from scamshield import main


def _has_tesseract() -> bool:
    import shutil
    if shutil.which("tesseract"):
        return True
    candidate = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Tesseract-OCR" / "tesseract.exe"
    return candidate.is_file()


@pytest.mark.skipif(not _has_tesseract(), reason="Tesseract OCR binary not installed")
def test_combined_screenshot_ocr_and_qr_decoding():
    qr = qrcode.QRCode(box_size=6, border=2)
    payload = "upi://pay?pa=scammer@ybl&pn=Cashback&am=2500&cu=INR"
    qr.add_data(payload)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    canvas = Image.new("RGB", (900, 380), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 24), "Scan QR to receive Rs 2500 cashback", fill="black", font_size=28)
    canvas.paste(qr_img, (24, 90))

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")

    client = TestClient(main.app)
    ocr_resp = client.post("/api/ocr?language=en", files={"file": ("combo.png", buf.getvalue(), "image/png")})
    assert ocr_resp.status_code == 200, ocr_resp.text
    ocr_data = ocr_resp.json()
    assert "cashback" in ocr_data["text"].lower() or "scan" in ocr_data["text"].lower()
    assert payload in ocr_data["qr_payloads"]

    an_resp = client.post(
        "/api/analyze",
        json={
            "text": ocr_data["text"],
            "channel": "image",
            "language": "en",
            "qr_payloads": ocr_data["qr_payloads"],
        },
    )
    assert an_resp.status_code == 200
    assert an_resp.json()["level"] == "high"
