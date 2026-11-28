"""Make a stained, phone-photo-like copy of a TEST bill page, to try the photo-safety flow.

The output is a test fixture, not a real bill: the page keeps its "TEST BILL" banner.

  python scripts/stain_photo.py page.png out.jpg --box 1467,560,1575,590 [--box ...] [--seed 7]

--box  x0,y0,x1,y1 in pixels of the input image: a coffee stain is centred on each box and
       darkest over it, so the number underneath is hard to read (as on a real spilled bill).
The whole page also gets a light second stain, a slight tilt, uneven light, paper grain and
JPEG compression, the way a phone photo looks.
"""

from __future__ import annotations

import argparse
import random

import numpy as np
from PIL import Image, ImageFilter


def _stain(h: int, w: int, cx: float, cy: float, r: float, strength: float, rng: random.Random) -> np.ndarray:
    """Alpha map of one coffee stain: an irregular blob, darker at the rim, with blotches inside."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ang = np.arctan2(yy - cy, xx - cx)
    wobble = sum(rng.uniform(0.04, 0.10) * np.sin(k * ang + rng.uniform(0, 6.28)) for k in (3, 5, 8))
    d = np.hypot(xx - cx, yy - cy) / (r * (1 + wobble))
    body = np.clip(1 - d, 0, 1) ** 0.6 * 0.55
    rim = np.exp(-((d - 0.95) ** 2) / 0.004) * 0.9
    blot = np.zeros_like(d)
    for _ in range(6):
        bx, by = cx + rng.uniform(-0.5, 0.5) * r, cy + rng.uniform(-0.4, 0.4) * r
        br = r * rng.uniform(0.15, 0.35)
        blot += np.clip(1 - np.hypot(xx - bx, yy - by) / br, 0, 1) * rng.uniform(0.3, 0.6)
    a = np.clip((body + rim + blot) * (d < 1.05), 0, 1) * strength
    return a


STRENGTH = 0.92


def stain(src: str, out: str, boxes: list[tuple[int, int, int, int]], seed: int = 7) -> None:
    rng = random.Random(seed)
    img = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
    h, w = img.shape[:2]
    coffee = np.array([120, 72, 30], dtype=np.float32)
    alpha = np.zeros((h, w), np.float32)
    for x0, y0, x1, y1 in boxes:   # heavy stains over the numbers to hide
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        alpha = np.maximum(alpha, _stain(h, w, cx, cy, max(x1 - x0, 90) * 0.9, STRENGTH, rng))
    # a light ring elsewhere, as from the bottom of a cup
    alpha = np.maximum(alpha, _stain(h, w, w * 0.25, h * 0.62, w * 0.09, 0.35, rng))
    a = alpha[..., None]
    img = img * (1 - a) + coffee * a * 0.9 + img * a * 0.1 * (coffee / 255)
    # uneven light and paper grain
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    light = 0.86 + 0.14 * (1 - np.hypot((xx - w * 0.3) / w, (yy - h * 0.2) / h))
    img = img * light[..., None] * np.array([1.0, 0.98, 0.93])
    img += np.random.default_rng(seed).normal(0, 6, img.shape)
    pic = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    pic = pic.rotate(rng.uniform(-1.5, 1.5), resample=Image.BICUBIC, expand=True, fillcolor=(70, 62, 55))
    pic = pic.filter(ImageFilter.GaussianBlur(0.6))
    pic.save(out, "JPEG", quality=82)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--box", action="append", default=[], help="x0,y0,x1,y1 to cover with a stain")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    boxes = [tuple(int(v) for v in b.split(",")) for b in a.box]
    stain(a.src, a.out, boxes, a.seed)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
