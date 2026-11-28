"""Image preparation: quality checks, perspective correction, deskew, contrast."""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass
class Quality:
    blur_score: float
    brightness: float
    warnings: list[str] = field(default_factory=list)


def check_quality(gray: np.ndarray) -> Quality:
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    bright = float(gray.mean())
    warn = []
    if blur < 60:
        warn.append("blurry")
    if bright < 70:
        warn.append("too_dark")
    if bright > 235 and float(gray.std()) < 25:
        warn.append("washed_out")
    return Quality(blur, bright, warn)


def _order(pts: np.ndarray) -> np.ndarray:
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]],
                    dtype="float32")


def correct_perspective(gray: np.ndarray) -> np.ndarray:
    """Find the page outline and flatten it. Returns the input if no clear page is found."""
    h, w = gray.shape
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(approx) == 4 and cv2.contourArea(approx) > 0.5 * h * w:
            rect = _order(approx.reshape(4, 2).astype("float32"))
            (tl, tr, br, bl) = rect
            width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
            height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
            dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], "float32")
            m = cv2.getPerspectiveTransform(rect, dst)
            return cv2.warpPerspective(gray, m, (width, height))
    return gray


def deskew(gray: np.ndarray, max_angle: float = 5.0, step: float = 0.25) -> tuple[np.ndarray, float]:
    """Projection-profile deskew: pick the angle where text rows are sharpest."""
    small = cv2.resize(gray, None, fx=0.5, fy=0.5) if max(gray.shape) > 1600 else gray
    bw = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    h, w = bw.shape
    best, best_score = 0.0, -1.0
    for ang in np.arange(-max_angle, max_angle + step, step):
        m = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
        rot = cv2.warpAffine(bw, m, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
        score = float(np.var(rot.sum(axis=1)))
        if score > best_score:
            best, best_score = float(ang), score
    if abs(best) < 0.1:
        return gray, 0.0
    H, W = gray.shape
    m = cv2.getRotationMatrix2D((W / 2, H / 2), best, 1.0)
    return cv2.warpAffine(gray, m, (W, H), flags=cv2.INTER_CUBIC, borderValue=255), best


def enhance(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def prepare(path: str) -> tuple[np.ndarray, Quality, float]:
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"cannot read image {path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    quality = check_quality(gray)
    gray = correct_perspective(gray)
    gray, angle = deskew(gray)
    gray = enhance(gray)
    return gray, quality, angle
