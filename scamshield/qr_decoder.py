"""Offline QR code decoding, UPI URI parsing, and cross-modal intent checks.

All decoding happens locally using OpenCV QRCodeDetector and Pillow/NumPy.
Never fetches URLs or initiates payments.
"""
from __future__ import annotations

import io
import re
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import cv2
import numpy as np
from PIL import Image, ImageOps

_RECEIVE_INTENT_RE = re.compile(
    r"\b(?:receive|refund|cashback|prize|lottery|reward|claim|credit|get\s+paid|"
    r"buyer|olx|quikr|insurance\s+charge|deposit\s+to\s+get)\b|"
    r"पैसे\s*पाने|कैशबैक|रिफंड|इनाम",
    re.I,
)
_AUTHORITY_OR_KYC_RE = re.compile(
    r"\b(?:kyc|pan\s+update|aadhaar|sbi|hdfc|icici|axis|rbi|cbi|police|customs|"
    r"electricity|disconnection|parcel|courier|verification|fine|penalty)\b|"
    r"केवाईसी|पुलिस|सीबीआई|बिजली",
    re.I,
)
_URL_SCHEME_RE = re.compile(r"^(?:https?://|www\.)", re.I)
_APK_RE = re.compile(r"\.apk(?:$|[?#])", re.I)
_VPA_RE = re.compile(r"^[a-zA-Z0-9._\-]{2,}@[a-zA-Z0-9.\-]{2,}$")


def _try_decode(detector: cv2.QRCodeDetector, img: np.ndarray) -> list[str]:
    """Run multi and single QR decode on an OpenCV image array."""
    found: list[str] = []
    try:
        ok, decoded_info, _points, _ = detector.detectAndDecodeMulti(img)
        if ok and decoded_info is not None:
            for item in decoded_info:
                val = (item or "").strip()
                if val and val not in found:
                    found.append(val)
    except cv2.error:
        pass
    if not found:
        try:
            val, _points, _ = detector.detectAndDecode(img)
            val = (val or "").strip()
            if val:
                found.append(val)
        except cv2.error:
            pass
    return found


def decode_qr_from_pil(image: Image.Image) -> list[str]:
    """Decode QR code payloads from a Pillow Image using progressive fallbacks."""
    rgb = ImageOps.exif_transpose(image).convert("RGB")
    bgr = cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)
    detector = cv2.QRCodeDetector()

    results = _try_decode(detector, bgr)
    if results:
        return results

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    if min(h, w) < 600:
        scale = 2.0
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        results = _try_decode(detector, gray)
        if results:
            return results

    # Otsu threshold and inverted threshold (handles dark-mode / low-contrast QRs)
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    for variant in (otsu, cv2.bitwise_not(otsu)):
        results = _try_decode(detector, variant)
        if results:
            return results

    return []


def decode_qr_from_bytes(image_bytes: bytes) -> list[str]:
    """Decode QR payloads from raw image bytes. Returns [] on failure."""
    if not image_bytes:
        return []
    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            return decode_qr_from_pil(im)
    except Exception:
        return []


def parse_upi_uri(payload: str) -> dict[str, Any] | None:
    """Parse a UPI deep-link URI (e.g. upi://pay?pa=...&pn=...&am=...)."""
    raw = (payload or "").strip()
    if not raw.lower().startswith("upi://"):
        return None
    parsed = urlparse(raw)
    action = (parsed.netloc or parsed.path or "pay").strip("/").lower()
    qs = parse_qs(parsed.query, keep_blank_values=False)

    def first(key: str) -> str:
        vals = qs.get(key)
        return unquote(vals[0]).strip() if vals else ""

    pa = first("pa")
    pn = first("pn")
    am_raw = first("am")
    cu = first("cu") or "INR"
    tn = first("tn")
    mam = first("mam")
    mc = first("mc")
    mode = first("mode")

    amount: float | None = None
    if am_raw:
        try:
            val = float(am_raw)
            if np.isfinite(val) and val >= 0:
                amount = val
        except ValueError:
            amount = None

    return {
        "scheme": "upi",
        "action": action,
        "pa": pa,
        "pn": pn,
        "am": amount,
        "am_raw": am_raw,
        "cu": cu,
        "tn": tn,
        "mam": mam,
        "mc": mc,
        "mode": mode,
        "valid_vpa": bool(_VPA_RE.match(pa)),
    }


def classify_qr_payload(payload: str) -> dict[str, Any]:
    """Classify a decoded QR payload without network access."""
    raw = (payload or "").strip()
    upi = parse_upi_uri(raw)
    if upi is not None:
        return {"type": "upi_payment", "raw": raw, "upi": upi}

    if _URL_SCHEME_RE.match(raw):
        kind = "apk_download" if _APK_RE.search(raw) else "url"
        return {"type": kind, "raw": raw, "url": raw}

    lower = raw.lower()
    if lower.startswith(("tel:", "sms:", "smsto:", "mailto:")):
        return {"type": "contact_action", "raw": raw}

    if _APK_RE.search(raw):
        return {"type": "apk_download", "raw": raw, "url": raw}

    return {"type": "text", "raw": raw}


def analyze_qr_payloads(
    payloads: list[str],
    surrounding_text: str = "",
) -> dict[str, Any]:
    """Analyze decoded QR payloads and check cross-modal intent consistency."""
    items: list[dict[str, Any]] = []
    indicators: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    text = (surrounding_text or "").strip()
    receive_claimed = bool(_RECEIVE_INTENT_RE.search(text))
    authority_claimed = bool(_AUTHORITY_OR_KYC_RE.search(text))

    def add_indicator(
        fid: str,
        title: str,
        explanation: str,
        weight: int,
        evidence: str,
        advice: str,
        category: str,
    ) -> None:
        if fid in seen_ids:
            return
        seen_ids.add(fid)
        indicators.append(
            {
                "id": fid,
                "title": title,
                "explanation": explanation,
                "weight": weight,
                "evidence": evidence[:160],
                "start": 0,
                "end": 0,
                "advice": advice,
                "_category": category,
            }
        )

    for raw in payloads:
        info = classify_qr_payload(raw)
        items.append(info)
        ptype = info["type"]

        if ptype == "upi_payment":
            upi = info["upi"]
            pa = upi["pa"] or "unknown VPA"
            pn = upi["pn"] or "unnamed payee"
            amt = upi["am"]
            amt_str = f"₹{amt:g}" if amt is not None else "unspecified amount"
            evidence = f"UPI QR ({upi['action']}): to {pn} ({pa}), {amt_str}"

            if receive_claimed:
                add_indicator(
                    "qr_receive_mismatch",
                    "QR code is an outgoing payment, not a receipt",
                    "The message mentions receiving money, a refund, or a reward, "
                    "but scanning a UPI payment QR code sends money OUT of your account.",
                    7,
                    evidence,
                    "Do not scan this QR code or enter your UPI PIN. You never scan a QR code to receive money.",
                    "Quishing / UPI QR fraud",
                )
            elif authority_claimed:
                add_indicator(
                    "qr_authority_mismatch",
                    "Official/KYC claim paired with a UPI payment QR",
                    "Legitimate banks, police, and government agencies do not ask you to scan a UPI QR code to resolve KYC or legal issues.",
                    6,
                    evidence,
                    "Do not pay via this QR code. Verify directly in your bank's official app.",
                    "Quishing / UPI QR fraud",
                )
            elif amt is not None and amt > 0:
                add_indicator(
                    "upi_qr_prefilled_amount",
                    "QR code requests a pre-filled UPI payment",
                    f"This QR encodes an outgoing UPI {upi['action']} request for {amt_str} to {pa}.",
                    3,
                    evidence,
                    "Confirm the payee name and amount in your UPI app before approving.",
                    "UPI payment QR",
                )
            else:
                add_indicator(
                    "upi_qr_pay",
                    "QR code encodes an outgoing UPI payment",
                    f"Scanning this QR initiates a UPI {upi['action']} to {pa}.",
                    1,
                    evidence,
                    "Verify the recipient independently before sending money.",
                    "UPI payment QR",
                )

        elif ptype == "apk_download":
            add_indicator(
                "qr_apk_download",
                "QR code links to an Android APK download",
                "QR codes pointing directly to APK files can install spyware or OTP-stealing malware.",
                6,
                raw,
                "Do not scan or download APK files from QR codes. Use only official app stores.",
                "Quishing / Malware",
            )

        elif ptype == "url":
            if receive_claimed or authority_claimed:
                add_indicator(
                    "qr_url_context_mismatch",
                    "QR code redirects to an external website",
                    "The message claims a refund, KYC, or official notice while the QR code sends you to an external web link.",
                    4,
                    raw,
                    "Do not open the QR link. Open your bank or service's official app directly.",
                    "Quishing",
                )
            else:
                add_indicator(
                    "qr_external_url",
                    "QR code contains an external web link",
                    "QR codes hide the destination URL until scanned; verify the domain before opening.",
                    1,
                    raw,
                    "Inspect the domain carefully before opening any link from a QR code.",
                    "Quishing",
                )

    return {
        "qr_count": len(items),
        "payloads": items,
        "indicators": indicators,
    }
