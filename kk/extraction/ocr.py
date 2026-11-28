"""Text with positions from PDFs and images.

Sources, in order of trust: the PDF text layer, then an OCR ensemble
(RapidOCR as primary, Tesseract as a second reader for digits).
"""

from __future__ import annotations

import csv
import io
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

from ..models import BBox, Word

_DIGITS = re.compile(r"\d")


def _split_line(text: str, x0: float, y0: float, x1: float, y1: float, conf: float,
                page: int, start: int) -> list[Word]:
    """RapidOCR returns phrases; split them into words with proportional x positions."""
    parts = text.split()
    if not parts:
        return []
    total = sum(len(p) for p in parts) + (len(parts) - 1)
    out, cursor = [], 0
    for i, p in enumerate(parts):
        a = x0 + (x1 - x0) * cursor / total
        b = x0 + (x1 - x0) * (cursor + len(p)) / total
        out.append(Word(id=f"p{page}w{start + i}", text=p, bbox=BBox(page=page, x0=a, y0=y0, x1=b, y1=y1),
                        conf=conf))
        cursor += len(p) + 1
    return out


def rapidocr_words(img: np.ndarray, page: int, start: int = 0) -> list[Word] | None:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return None
    engine = _rapid_singleton(RapidOCR)
    result, _ = engine(img)
    words: list[Word] = []
    for box, text, score in result or []:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        new = _split_line(text, min(xs), min(ys), max(xs), max(ys), float(score), page, start + len(words))
        words.extend(new)
    return words


_RAPID = None


def _rapid_singleton(cls):
    global _RAPID
    if _RAPID is None:
        _RAPID = cls()
    return _RAPID


def tesseract_words(img: np.ndarray, page: int, start: int = 0) -> list[Word] | None:
    if not shutil.which("tesseract"):
        return None
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
        cv2.imwrite(fh.name, img)
        tmp = fh.name
    try:
        res = subprocess.run(["tesseract", tmp, "stdout", "--psm", "6", "tsv"],
                             capture_output=True, text=True, timeout=120)
    finally:
        Path(tmp).unlink(missing_ok=True)
    words: list[Word] = []
    reader = csv.DictReader(io.StringIO(res.stdout), delimiter="\t", quoting=csv.QUOTE_NONE)
    for r in reader:
        t = (r.get("text") or "").strip()
        if not t or r.get("conf") in (None, "", "-1"):
            continue
        x, y, w, h = (float(r[k]) for k in ("left", "top", "width", "height"))
        words.append(Word(id=f"p{page}w{start + len(words)}", text=t,
                          bbox=BBox(page=page, x0=x, y0=y, x1=x + w, y1=y + h),
                          conf=max(0.0, min(1.0, float(r["conf"]) / 100))))
    return words


def _iou(a: BBox, b: BBox) -> float:
    ix = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    iy = max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))
    inter = ix * iy
    union = (a.x1 - a.x0) * (a.y1 - a.y0) + (b.x1 - b.x0) * (b.y1 - b.y0) - inter
    return inter / union if union > 0 else 0.0


def _digits(t: str) -> str:
    return re.sub(r"[^\d.]", "", t)


def cross_check_digits(primary: list[Word], second: list[Word]) -> list[Word]:
    """Combine two OCR engines for numbers.

    - both engines read the same digits: confidence raised (independent agreement)
    - they disagree: confidence lowered, so the user is asked to confirm
    - only the second engine saw a number (lone digits are often missed by detectors):
      the word is added with moderate confidence
    """
    out = []
    for w in primary:
        if _DIGITS.search(w.text):
            match = max(second, key=lambda s: _iou(w.bbox, s.bbox), default=None)
            if match is None or _iou(w.bbox, match.bbox) < 0.2:
                w = w.model_copy(update={"conf": min(w.conf, 0.8)})
            elif _digits(match.text) != _digits(w.text):
                w = w.model_copy(update={"conf": min(w.conf, 0.5)})
            else:
                w = w.model_copy(update={"conf": max(w.conf, 0.95)})
        out.append(w)
    next_id = len(out)
    for s in second:
        if not _DIGITS.search(s.text) or s.conf < 0.6:
            continue
        if any(_iou(s.bbox, w.bbox) > 0.05 for w in primary):
            continue
        page = s.bbox.page
        out.append(s.model_copy(update={"id": f"p{page}w{start_of(out)}", "conf": min(s.conf, 0.8)}))
        next_id += 1
    return out


def start_of(words: list[Word]) -> int:
    """Next free word number on the page ids used so far."""
    nums = [int(w.id.split("w")[-1]) for w in words]
    return (max(nums) + 1) if nums else 0


# Handwritten digits are often read as look-alike letters: 5 as S, 0 as o, 1 as I or l.
_LOOK = str.maketrans({"S": "5", "s": "5", "O": "0", "o": "0", "I": "1", "l": "1", "|": "1"})
_NUMISH = re.compile(r"^[\dSsOoIl|,.\-/]+$")
_DOSE = re.compile(r"^([\dSsOoIl|.]+)(ml|mg|g|gm|mcg|iu)$", re.IGNORECASE)
_SLASH_DASH = re.compile(r"^\d{1,3}(,\d{2,3})*,\d{3}[1/]$")     # "6,0001": a handwritten "/-" read as "1"
# "25,0001-", "9001-": the "/" of a handwritten "/-" read as "1", the dash kept (RapidOCR 1.4)
_SLASH_DASH_KEPT = re.compile(r"^(\d{1,3}(?:,\d{2,3})*(?:,\d{3})|\d{2,})[1/]-$")
_DOT_THOUSANDS = re.compile(r"^\d{1,3}\.\d{3}$")                  # "8.000" for "8,000"


def fix_lookalikes(words: list[Word]) -> list[Word]:
    """Repair digits a reader took for letters in amounts and doses ("2S,000/-", "so0ml", "Ig").

    Only tokens that already hold a digit and nothing but digit look-alikes are changed (or a
    dose such as "Somg"). Every repaired amount is marked low confidence, so the family is asked
    to confirm it before any rule uses it: a repair can lower doubt, never remove it."""
    for w in words:
        t = w.text
        new = t
        if _NUMISH.match(t) and any(c.isdigit() for c in t) and any(c in "SsOoIl|" for c in t):
            new = t.translate(_LOOK)
        elif _DOSE.match(t) and any(c in "SsOoIl|" for c in _DOSE.match(t).group(1)):
            m = _DOSE.match(t)
            new = m.group(1).translate(_LOOK) + m.group(2)
        if _SLASH_DASH.match(new):
            new = new[:-1] + "/-"
        elif _SLASH_DASH_KEPT.match(new) and not new.endswith("/-"):
            new = _SLASH_DASH_KEPT.match(new).group(1) + "/-"
        elif _DOT_THOUSANDS.match(new):
            new = new.replace(".", ",")
        if new != t:
            w.text = new
            if not _DOSE.match(new):
                w.conf = min(w.conf, 0.6)
    return words


def ocr_image(img: np.ndarray, page: int, start: int = 0) -> list[Word]:
    primary = rapidocr_words(img, page, start)
    second = tesseract_words(img, page, start)
    if primary is None and second is None:
        raise RuntimeError("No OCR engine available: install rapidocr_onnxruntime or tesseract")
    if primary is None:
        return fix_lookalikes(second or [])
    if second:
        return fix_lookalikes(cross_check_digits(primary, second))
    return fix_lookalikes(primary)


def pdf_words(path: str) -> tuple[list[Word], int, list[np.ndarray]]:
    """Words from a PDF. Pages without a usable text layer are rasterised and OCR'd."""
    import pdfplumber

    words: list[Word] = []
    images: list[np.ndarray] = []
    with pdfplumber.open(path) as doc:
        for pno, page in enumerate(doc.pages, start=1):
            pil = page.to_image(resolution=200).original.convert("L")
            img = np.array(pil)
            images.append(img)
            scale = 200 / 72
            layer = page.extract_words(keep_blank_chars=False, use_text_flow=False)
            if len(layer) >= 10:
                for w in layer:
                    words.append(Word(id=f"p{pno}w{len(words)}", text=w["text"],
                                      bbox=BBox(page=pno, x0=w["x0"] * scale, y0=w["top"] * scale,
                                                x1=w["x1"] * scale, y1=w["bottom"] * scale),
                                      conf=1.0))
            else:
                words.extend(ocr_image(img, pno, len(words)))
        return words, len(doc.pages), images