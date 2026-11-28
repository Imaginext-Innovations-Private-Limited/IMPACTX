"""Tests for offline QR code decoding, UPI URI parsing, and cross-modal checks."""
import io

import qrcode

from scamshield.qr_decoder import (
    analyze_qr_payloads,
    classify_qr_payload,
    decode_qr_from_bytes,
    parse_upi_uri,
)


def _make_qr_bytes(payload: str, invert: bool = False) -> bytes:
    qr = qrcode.QRCode(box_size=8, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    fill = "white" if invert else "black"
    back = "black" if invert else "white"
    img = qr.make_image(fill_color=fill, back_color=back).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_decode_upi_qr_and_inverted_qr():
    payload = "upi://pay?pa=scammer@ybl&pn=Cashback%20Desk&am=4999&cu=INR&tn=Refund"
    raw = _make_qr_bytes(payload)
    decoded = decode_qr_from_bytes(raw)
    assert payload in decoded

    inv = _make_qr_bytes(payload, invert=True)
    decoded_inv = decode_qr_from_bytes(inv)
    assert payload in decoded_inv


def test_decode_non_qr_and_malformed_bytes_return_empty():
    assert decode_qr_from_bytes(b"") == []
    assert decode_qr_from_bytes(b"not-an-image") == []


def test_parse_upi_uri_fields():
    parsed = parse_upi_uri("upi://pay?pa=merchant@okicici&pn=Demo%20Shop&am=150.50&cu=INR&tn=Tea")
    assert parsed is not None
    assert parsed["action"] == "pay"
    assert parsed["pa"] == "merchant@okicici"
    assert parsed["pn"] == "Demo Shop"
    assert parsed["am"] == 150.50
    assert parsed["cu"] == "INR"
    assert parsed["tn"] == "Tea"
    assert parsed["valid_vpa"] is True


def test_classify_qr_payload_variants():
    assert classify_qr_payload("upi://pay?pa=a@ybl")["type"] == "upi_payment"
    assert classify_qr_payload("https://sbi-kyc-update.xyz/login")["type"] == "url"
    assert classify_qr_payload("https://example.com/app/update.apk")["type"] == "apk_download"
    assert classify_qr_payload("Hello world")["type"] == "text"


def test_cross_modal_receive_mismatch_detected():
    payload = "upi://pay?pa=fraudster@okaxis&pn=Prize&am=5000&cu=INR"
    res = analyze_qr_payloads(
        [payload],
        surrounding_text="Congratulations! Scan this QR to receive Rs 5000 cashback in your bank.",
    )
    ids = {i["id"] for i in res["indicators"]}
    assert "qr_receive_mismatch" in ids
    assert res["indicators"][0]["weight"] >= 7


def test_cross_modal_authority_mismatch_detected():
    payload = "upi://pay?pa=agent123@paytm&pn=KYC%20Desk&am=1000"
    res = analyze_qr_payloads(
        [payload],
        surrounding_text="Your SBI KYC is suspended. Scan QR immediately to verify.",
    )
    ids = {i["id"] for i in res["indicators"]}
    assert "qr_authority_mismatch" in ids
