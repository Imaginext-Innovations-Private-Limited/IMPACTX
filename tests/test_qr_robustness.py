"""Tests for Milestone 13 robust real-world QR decoding and status handling."""
import io

import pytest
import qrcode
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFilter

from scamshield import main
from scamshield.engine import analyze
from scamshield.qr_decoder import decode_qr_detailed_from_bytes, decode_qr_detailed_from_pil

UPI_PAYLOAD = "upi://pay?pa=merchant@okicici&pn=Demo%20Store&am=500&cu=INR"


def _make_qr_img(payload: str, box_size: int = 8, border: int = 4, fill="black", back="white", ec=qrcode.constants.ERROR_CORRECT_M) -> Image.Image:
    qr = qrcode.QRCode(box_size=box_size, border=border, error_correction=ec)
    qr.add_data(payload)
    qr.make(fit=True)
    return qr.make_image(fill_color=fill, back_color=back).convert("RGB")


def test_realistic_qr_conditions():
    results = {}

    # 1. WhatsApp-style JPEG compression
    im_jpg = _make_qr_img(UPI_PAYLOAD).resize((260, 260))
    buf = io.BytesIO()
    im_jpg.save(buf, format="JPEG", quality=25)
    r1 = decode_qr_detailed_from_bytes(buf.getvalue())
    results["whatsapp_jpeg_q25"] = r1["status"] == "decoded" and UPI_PAYLOAD in r1["payloads"]

    # 2. Low resolution
    im_low = _make_qr_img(UPI_PAYLOAD, box_size=3, border=2)
    r2 = decode_qr_detailed_from_pil(im_low)
    results["low_resolution"] = r2["status"] == "decoded" and UPI_PAYLOAD in r2["payloads"]

    # 3. Embedded center logo (PhonePe/GPay style)
    im_logo = _make_qr_img(UPI_PAYLOAD, box_size=10, border=4, ec=qrcode.constants.ERROR_CORRECT_H)
    w, h = im_logo.size
    draw = ImageDraw.Draw(im_logo)
    lw = int(w * 0.18)
    draw.rectangle([(w - lw) // 2, (h - lw) // 2, (w + lw) // 2, (h + lw) // 2], fill="#0f766e")
    r3 = decode_qr_detailed_from_pil(im_logo)
    results["embedded_logo"] = r3["status"] == "decoded" and UPI_PAYLOAD in r3["payloads"]

    # 4. Rotated QR (18 degrees)
    im_rot = _make_qr_img(UPI_PAYLOAD, box_size=8, border=4).rotate(18, expand=True, fillcolor="white")
    r4 = decode_qr_detailed_from_pil(im_rot)
    results["rotated_18deg"] = r4["status"] == "decoded" and UPI_PAYLOAD in r4["payloads"]

    # 5. Low contrast
    im_lowc = _make_qr_img(UPI_PAYLOAD, fill=(95, 95, 95), back=(195, 195, 195))
    r5 = decode_qr_detailed_from_pil(im_lowc)
    results["low_contrast"] = r5["status"] == "decoded" and UPI_PAYLOAD in r5["payloads"]

    # 6. Cropped borders (border=0)
    im_crop = _make_qr_img(UPI_PAYLOAD, box_size=8, border=0)
    r6 = decode_qr_detailed_from_pil(im_crop)
    results["cropped_borders"] = r6["status"] == "decoded" and UPI_PAYLOAD in r6["payloads"]

    # 7. Multiple QR codes in one image
    q_a = _make_qr_img(UPI_PAYLOAD, box_size=6, border=3)
    q_b = _make_qr_img("https://sbi-kyc.example/login", box_size=6, border=3)
    canvas = Image.new("RGB", (q_a.width + q_b.width + 60, max(q_a.height, q_b.height) + 40), "white")
    canvas.paste(q_a, (20, 20))
    canvas.paste(q_b, (q_a.width + 40, 20))
    r7 = decode_qr_detailed_from_pil(canvas)
    results["multi_qr"] = r7["status"] == "decoded" and len(r7["payloads"]) == 2

    assert all(results.values()), f"Failed conditions: {results}"


def test_qr_status_none_error_and_unreadable():
    blank = Image.new("RGB", (200, 200), "white")
    assert decode_qr_detailed_from_pil(blank)["status"] == "none"

    err = decode_qr_detailed_from_bytes(b"corrupt-bytes")
    assert err["status"] == "error"

    res = analyze("", channel="image", qr_status="detected_unreadable")
    assert res["level"] == "review"
    assert any(i["id"] == "qr_unreadable" for i in res["indicators"])


def test_legitimate_qr_preserved_and_displayed_via_api():
    im = _make_qr_img(UPI_PAYLOAD, box_size=8, border=4, ec=qrcode.constants.ERROR_CORRECT_H)
    w, h = im.size
    ImageDraw.Draw(im).rectangle([(w - 40) // 2, (h - 40) // 2, (w + 40) // 2, (h + 40) // 2], fill="#1d4ed8")
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=40)

    client = TestClient(main.app)
    ocr = client.post("/api/ocr?language=en", files={"file": ("whatsapp_qr.jpg", buf.getvalue(), "image/jpeg")})
    assert ocr.status_code == 200
    odata = ocr.json()
    assert odata["qr_status"] == "decoded"
    assert UPI_PAYLOAD in odata["qr_payloads"]

    an = client.post(
        "/api/analyze",
        json={"text": odata["text"], "qr_payloads": odata["qr_payloads"], "qr_status": odata["qr_status"]},
    )
    assert an.status_code == 200
    body = an.json()
    assert body["qr_analysis"]["payloads"][0]["upi"]["pa"] == "merchant@okicici"
