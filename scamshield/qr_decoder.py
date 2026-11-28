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
import zxingcpp
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


def _try_opencv(detector: cv2.QRCodeDetector, img: np.ndarray) -> tuple[list[str], bool]:
    """Run OpenCV multi and single QR decode; also report whether a QR box was detected."""
    found: list[str] = []
    detected_box = False
    try:
        ok, decoded_info, points, _ = detector.detectAndDecodeMulti(img)
        if points is not None and len(points) > 0:
            detected_box = True
        if ok and decoded_info is not None:
            for item in decoded_info:
                val = (item or "").strip()
                if val and val not in found:
                    found.append(val)
    except cv2.error:
        pass
    if not found:
        try:
            val, points, _ = detector.detectAndDecode(img)
            if points is not None and len(points) > 0:
                detected_box = True
            val = (val or "").strip()
            if val:
                found.append(val)
        except cv2.error:
            pass
    return found, detected_box


def _try_zxing(img: np.ndarray) -> tuple[list[str], bool]:
    """Run zxing-cpp QR decoding; also report if an unreadable QR candidate was seen."""
    found: list[str] = []
    detected_box = False
    try:
        barcodes = zxingcpp.read_barcodes(
            img,
            formats=zxingcpp.BarcodeFormat.QRCode,
            try_rotate=True,
            try_invert=True,
            try_downscale=True,
        )
        for b in barcodes:
            val = (b.text or "").strip()
            if val and b.valid:
                if val not in found:
                    found.append(val)
            else:
                detected_box = True
    except Exception:
        pass
    return found, detected_box


def _add_quiet_zone(img: np.ndarray, pad: int = 32) -> np.ndarray:
    val = (255, 255, 255) if img.ndim == 3 else 255
    return cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=val)


def _rotate_bound(img: np.ndarray, angle: float) -> np.ndarray:
    h, w = img.shape[:2]
    center = (w / 2.0, h / 2.0)
    mat = cv2.getRotationMatrix2D(center, angle, 1.0)
    cos = abs(mat[0, 0])
    sin = abs(mat[0, 1])
    nw = int((h * sin) + (w * cos))
    nh = int((h * cos) + (w * sin))
    mat[0, 2] += (nw / 2.0) - center[0]
    mat[1, 2] += (nh / 2.0) - center[1]
    val = (255, 255, 255) if img.ndim == 3 else 255
    return cv2.warpAffine(img, mat, (nw, nh), borderValue=val)


def decode_qr_detailed_from_pil(image: Image.Image) -> dict[str, Any]:
    """Multi-stage offline QR decoding using zxing-cpp + OpenCV with preprocessing."""
    rgb = np.array(ImageOps.exif_transpose(image).convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    detector = cv2.QRCodeDetector()
    all_found: list[str] = []
    used_decoders: set[str] = set()
    detected_box = False

    def run_stage(arr: np.ndarray, is_rgb: bool = False) -> bool:
        nonlocal detected_box
        zx_vals, zx_box = _try_zxing(arr)
        cv_arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if (is_rgb and arr.ndim == 3) else arr
        cv_vals, cv_box = _try_opencv(detector, cv_arr)
        if zx_box or cv_box:
            detected_box = True
        for v in zx_vals:
            used_decoders.add("zxing-cpp")
            if v not in all_found:
                all_found.append(v)
        for v in cv_vals:
            used_decoders.add("opencv")
            if v not in all_found:
                all_found.append(v)
        return bool(all_found)

    # 1. Original image before preprocessing
    if run_stage(rgb, is_rgb=True):
        return {"status": "decoded", "payloads": all_found, "decoder_used": "+".join(sorted(used_decoders)), "error": None}

    # 2. White border padding (restores cropped quiet zones)
    if run_stage(_add_quiet_zone(rgb, 36), is_rgb=True):
        return {"status": "decoded", "payloads": all_found, "decoder_used": "+".join(sorted(used_decoders)), "error": None}

    # 3. Grayscale + CLAHE contrast enhancement + quiet zone
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    if run_stage(_add_quiet_zone(clahe, 32)):
        return {"status": "decoded", "payloads": all_found, "decoder_used": "+".join(sorted(used_decoders)), "error": None}

    # 4. Multiple scaling resolutions (upscale small QRs, downscale huge images)
    h, w = gray.shape[:2]
    scales = []
    if min(h, w) < 600:
        scales.append(2.0)
    if min(h, w) < 300:
        scales.append(3.0)
    if max(h, w) > 1600:
        scales.append(0.5)
    for sc in scales:
        resized = cv2.resize(clahe, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC if sc > 1 else cv2.INTER_AREA)
        if run_stage(_add_quiet_zone(resized, 32)):
            return {"status": "decoded", "payloads": all_found, "decoder_used": "+".join(sorted(used_decoders)), "error": None}

    # 5. Adaptive thresholding, Otsu, and inverted binary (dark-mode / low-contrast)
    work = _add_quiet_zone(
        cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC) if min(h, w) < 600 else gray,
        32,
    )
    adaptive = cv2.adaptiveThreshold(work, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 7)
    _, otsu = cv2.threshold(work, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    for variant in (adaptive, otsu, cv2.bitwise_not(otsu)):
        if run_stage(variant):
            return {"status": "decoded", "payloads": all_found, "decoder_used": "+".join(sorted(used_decoders)), "error": None}

    # 6. Skew/rotation correction for angled phone captures
    for angle in (-15.0, 15.0, -30.0, 30.0, 45.0):
        rotated = _rotate_bound(_add_quiet_zone(clahe, 24), angle)
        if run_stage(rotated):
            return {"status": "decoded", "payloads": all_found, "decoder_used": "+".join(sorted(used_decoders)), "error": None}

    status = "detected_unreadable" if detected_box else "none"
    return {"status": status, "payloads": [], "decoder_used": None, "error": None}


def decode_qr_detailed_from_bytes(image_bytes: bytes) -> dict[str, Any]:
    """Decode QR payloads from raw bytes and return explicit status metadata."""
    if not image_bytes:
        return {"status": "error", "payloads": [], "decoder_used": None, "error": "Empty image bytes."}
    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            return decode_qr_detailed_from_pil(im)
    except Exception as exc:
        return {"status": "error", "payloads": [], "decoder_used": None, "error": type(exc).__name__}


def decode_qr_from_pil(image: Image.Image) -> list[str]:
    """Decode QR code payloads from a Pillow Image."""
    return decode_qr_detailed_from_pil(image)["payloads"]


def decode_qr_from_bytes(image_bytes: bytes) -> list[str]:
    """Decode QR payloads from raw image bytes. Returns [] on failure."""
    return decode_qr_detailed_from_bytes(image_bytes)["payloads"]


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
    from .url_classifier import normalize_url, registered_domain

    raw = (payload or "").strip()
    upi = parse_upi_uri(raw)
    if upi is not None:
        action = upi.get("action") or "pay"
        return {
            "type": "upi_payment",
            "qr_type": f"UPI {action.title()} QR",
            "raw": raw,
            "upi": upi,
            "unverified_name_note": "QR-provided payee name is not independently verified.",
            "cross_modal_mismatch": False,
            "mismatch_reason": None,
        }

    if _URL_SCHEME_RE.match(raw):
        kind = "apk_download" if _APK_RE.search(raw) else "url"
        norm = normalize_url(raw)
        parsed = urlparse(norm)
        host = (parsed.hostname or "").lower()
        return {
            "type": kind,
            "qr_type": "APK Download QR" if kind == "apk_download" else "URL QR",
            "raw": raw,
            "url": raw,
            "destination": raw,
            "protocol": (parsed.scheme or "http").lower(),
            "registered_domain": registered_domain(host) if host else "",
            "cross_modal_mismatch": False,
            "mismatch_reason": None,
        }

    lower = raw.lower()
    if lower.startswith(("tel:", "sms:", "smsto:", "mailto:")):
        scheme = lower.split(":", 1)[0]
        return {
            "type": "contact_action",
            "qr_type": f"Contact Action QR ({scheme})",
            "raw": raw,
            "category": scheme,
            "extracted": raw[:200],
        }

    if _APK_RE.search(raw):
        return {
            "type": "apk_download",
            "qr_type": "APK Download QR",
            "raw": raw,
            "url": raw,
            "destination": raw,
            "protocol": "",
            "registered_domain": "",
            "cross_modal_mismatch": False,
            "mismatch_reason": None,
        }

    return {
        "type": "text",
        "qr_type": "Plain Text QR",
        "raw": raw,
        "category": "plain_text",
        "extracted": raw[:200],
    }


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
                info["cross_modal_mismatch"] = True
                info["mismatch_reason"] = "Message mentions receiving money/refund, but QR encodes an outgoing UPI payment."
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
                info["cross_modal_mismatch"] = True
                info["mismatch_reason"] = "Official/KYC claim paired with a UPI payment QR."
                add_indicator(
                    "qr_authority_mismatch",
                    "Official/KYC claim paired with a UPI payment QR",
                    "Legitimate banks, police, and government agencies do not ask you to scan a UPI QR code to resolve KYC or legal issues.",
                    6,
                    evidence,
                    "Do not pay via this QR code. Verify directly in your bank's official app.",
                    "Quishing / UPI QR fraud",
                )
            # Ordinary UPI payment QRs without contradictory or coercive context are NOT
            # treated as fraud indicators; extracted payee/amount/action details remain
            # visible in qr_analysis["payloads"] with unverified_name_note.

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
                info["cross_modal_mismatch"] = True
                info["mismatch_reason"] = "Message claims refund, KYC, or official notice while QR opens an external URL."
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
