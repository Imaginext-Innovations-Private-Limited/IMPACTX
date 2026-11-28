"""TEST BILL 4: a handwritten nursing-home bill for a caesarean (LSCS) delivery.

Fictional, like the other test bills: no real patient or hospital, a printed "TEST BILL" banner
and watermark, never used to measure accuracy. It exists to try the app on the kind of bill
many families actually get: a printed bill-book page from a small nursing home, filled in by
hand in blue ballpoint, then photographed on a phone.

What it is built to show (worked out by hand, see bill4_csection_handwritten.json):
  * Ringer Lactate 500 ml billed at 120 a bottle: NPPA ceiling 57.85 + 5% GST, 6 bottles = 364.46.
  * Diclofenac 50 mg capsules at 5 each: NPPA ceiling 0.78 + 5% GST, 10 capsules = 8.19.
    (Both once the staged NPPA S.O. 1581(E) rows are approved and units confirmed.)
  * Handwritten 5, 0 and 1 read as S, o and I; every repaired number is asked about.
  * Ceftriaxone 6 x 85 written as 610 (should be 510): on a handwritten photo the app asks
    the family to confirm before counting it.
  * 5 room days for a 3-night stay: worth asking.
  * Paid in cash in Karnataka: the scheme panel shows what a card could have paid.

Run:  python tests/fixtures/handwritten/make_handwritten.py
Needs the Kalam font (SIL OFL 1.1) in tests/fixtures/handwritten/fonts/.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent
FONTS = OUT / "fonts"
HAND = [str(FONTS / "Kalam-Regular.ttf"), str(FONTS / "Kalam-Light.ttf")]
PRINT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
PRINT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
PRINT_SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
NAME = "bill4_csection_handwritten"
W, H = 1700, 2300
INK = (28, 44, 128)

# (particulars, qty, rate, amount as WRITTEN). The amount for Ceftriaxone is written wrong on purpose.
LINES = [
    ("LSCS - Surgeon charges", "1", "25,000", "25,000/-"),
    ("Anaesthetist charges", "1", "6,000", "6,000/-"),
    ("O.T. charges", "1", "8,000", "8,000/-"),
    ("Room rent (General ward)", "5", "1,500", "7,500/-"),
    ("Nursing charges", "3", "500", "1,500/-"),
    ("Paediatrician - baby care", "1", "2,000", "2,000/-"),
    ("Inj Ringer Lactate 500ml", "6", "120", "720/-"),
    ("Inj Ceftriaxone 1g", "6", "85", "610/-"),
    ("Cap Diclofenac 50mg", "10", "5", "50/-"),
    ("Lab - CBC, Blood group", "1", "900", "900/-"),
    ("Sutures & dressing", "1", "2,500", "2,500/-"),
]
TOTAL, ADVANCE, BALANCE = "54,780/-", "20,000/-", "34,780/-"


def hand(draw_img: Image.Image, xy, text: str, size: int, rng: random.Random, slope: float = 0.0) -> float:
    """Write `text` the way a person does: each letter a little different in size, height
    and angle, the line drifting, the pen pressure varying. Returns the x where it ended."""
    x, y = xy
    for word in text.split(" "):
        wrot = rng.uniform(-3.5, 2.5)
        for ch in word:
            f = ImageFont.truetype(rng.choice(HAND), int(size * rng.uniform(0.88, 1.10)))
            box = f.getbbox(ch)
            cw, chh = box[2] - box[0] + 8, size * 2
            tile = Image.new("L", (int(cw + 20), int(chh)), 0)
            ImageDraw.Draw(tile).text((10 - box[0], size * 0.35), ch, font=f, fill=int(255 * rng.uniform(0.78, 1.0)))
            tile = tile.rotate(wrot + rng.uniform(-3, 3), resample=Image.BICUBIC)
            yj = y + rng.uniform(-4, 4) + slope * (x - xy[0])
            colour = Image.new("RGB", tile.size, tuple(int(c * rng.uniform(0.85, 1.1)) for c in INK))
            draw_img.paste(colour, (int(x - 10), int(yj - size * 0.35)), tile)
            x += f.getlength(ch) * rng.uniform(0.92, 1.04)
        x += size * rng.uniform(0.28, 0.4)
    return x


def page(seed: int = 11) -> Image.Image:
    rng = random.Random(seed)
    img = Image.new("RGB", (W, H), (248, 246, 238))
    d = ImageDraw.Draw(img)
    pf = lambda s, b=False: ImageFont.truetype(PRINT_B if b else PRINT, s)
    red, navy = (200, 34, 50), (40, 40, 60)

    # printed bill-book form
    d.text((W // 2, 70), "TEST BILL - NOT A REAL PATIENT - NOT VALID FOR ANY CLAIM", font=pf(30, True), fill=red, anchor="mm")
    d.text((W // 2, 150), "SAMPLE MATERNITY NURSING HOME", font=ImageFont.truetype(PRINT_SERIF_B, 58), fill=navy, anchor="mm")
    d.text((W // 2, 215), "45 Test Lane, Hebbal, Bengaluru 560024, Karnataka  ·  Reg. No. TEST/NH/0004", font=pf(28), fill=navy, anchor="mm")
    d.line((90, 250, W - 90, 250), fill=navy, width=4)
    d.text((W // 2, 295), "BILL / CASH MEMO", font=pf(34, True), fill=navy, anchor="mm")
    d.text((110, 350), "Bill No.", font=pf(30), fill=navy)
    d.text((250, 346), "0417", font=pf(34, True), fill=red)
    d.text((1150, 350), "Date:", font=pf(30), fill=navy)
    labels = [("Patient Name:", 420), ("Date of Admission:", 490), ("Date of Discharge:", 560)]
    for lab, y in labels:
        d.text((110, y), lab, font=pf(30), fill=navy)
        d.line((110 + d.textlength(lab, font=pf(30)) + 10, y + 40, W - 110, y + 40), fill=(150, 150, 165), width=2)
    # table
    top, row_h, rows = 640, 88, 12
    cols = [90, 190, 930, 1100, 1330, W - 90]
    heads = ["S.No.", "Particulars", "Qty", "Rate", "Amount (Rs.)"]
    d.rectangle((cols[0], top, cols[-1], top + 70 + rows * row_h), outline=navy, width=3)
    d.line((cols[0], top + 70, cols[-1], top + 70), fill=navy, width=3)
    for c in cols[1:-1]:
        d.line((c, top, c, top + 70 + rows * row_h), fill=navy, width=2)
    for i, hd in enumerate(heads):
        d.text(((cols[i] + cols[i + 1]) // 2, top + 35), hd, font=pf(30, True), fill=navy, anchor="mm")
    for r in range(1, rows):
        y = top + 70 + r * row_h
        d.line((cols[0], y, cols[-1], y), fill=(190, 190, 205), width=1)
    tot_y = top + 70 + rows * row_h
    for i, lab in enumerate(["Total", "Less: Advance", "Balance"]):
        d.text((1000, tot_y + 30 + i * 76), lab, font=pf(30, True), fill=navy)
    d.text((110, H - 190), "Received with thanks", font=pf(28), fill=navy)
    d.text((W - 110, H - 190), "for Sample Maternity Nursing Home", font=pf(28), fill=navy, anchor="ra")
    d.text((W - 110, H - 110), "Authorised Signatory", font=pf(26), fill=navy, anchor="ra")

    # faint printed watermark
    wm = Image.new("L", (W, H), 0)
    ImageDraw.Draw(wm).text((W // 2, H // 2), "TEST BILL", font=pf(220, True), fill=40, anchor="mm")
    wm = wm.rotate(28, resample=Image.BICUBIC)
    img.paste(Image.new("RGB", (W, H), (205, 60, 70)), (0, 0), wm)

    # handwriting
    hand(img, (1250, 336), "19/11/2026", 44, rng)
    hand(img, (360, 404), "Test Patient D", 46, rng, slope=-0.004)
    hand(img, (420, 474), "16/11/2026", 44, rng)
    hand(img, (420, 544), "19/11/2026", 44, rng, slope=0.003)
    for i, (desc, qty, rate, amt) in enumerate(LINES):
        y = top + 70 + i * row_h + 18 + rng.uniform(-4, 4)
        slope = rng.uniform(-0.006, 0.006)
        hand(img, (cols[0] + 30 + rng.uniform(-4, 6), y), f"{i + 1}.", 44, rng)
        hand(img, (cols[1] + 18 + rng.uniform(-6, 10), y), desc, 44, rng, slope)
        hand(img, (cols[2] + 60 + rng.uniform(-10, 10), y), qty, 44, rng)
        hand(img, (cols[3] + 40 + rng.uniform(-10, 10), y), rate, 44, rng)
        f = ImageFont.truetype(HAND[0], 44)
        hand(img, (cols[5] - 30 - f.getlength(amt) + rng.uniform(-14, 6), y), amt, 44, rng)
    for i, val in enumerate([TOTAL, ADVANCE, BALANCE]):
        f = ImageFont.truetype(HAND[0], 46)
        hand(img, (cols[5] - 30 - f.getlength(val) + rng.uniform(-12, 4), tot_y + 18 + i * 76), val, 46, rng)
    # a signature scrawl
    sig = ImageDraw.Draw(img)
    pts, x0, y0 = [], W - 480, H - 250
    for t in np.linspace(0, 1, 60):
        pts.append((x0 + t * 340, y0 + 18 * np.sin(t * 19) * (1 - t * 0.6) + rng.uniform(-2, 2)))
    sig.line(pts, fill=INK, width=4, joint="curve")
    return img


def photo(img: Image.Image, seed: int = 11) -> Image.Image:
    """Phone-photo look: tilt, uneven light, paper grain, slight blur."""
    rng = random.Random(seed)
    a = np.asarray(img).astype(np.float32)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    light = 0.84 + 0.16 * (1 - np.hypot((xx - w * 0.7) / w, (yy - h * 0.15) / h))
    a = a * light[..., None] * np.array([1.0, 0.985, 0.95])
    a += np.random.default_rng(seed).normal(0, 5, a.shape)
    pic = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    pic = pic.rotate(rng.uniform(-1.8, -0.8), resample=Image.BICUBIC, expand=True, fillcolor=(92, 78, 64))
    return pic.filter(ImageFilter.GaussianBlur(0.7))


def _n(s: str) -> str:
    return s.replace(",", "").replace("/-", "")


def main() -> None:
    photo(page()).save(OUT / f"{NAME}.jpg", "JPEG", quality=84)
    lines = [{"description": d, "section": None, "date": None, "batch": None, "expiry": None,
              "qty": q, "rate": f"{_n(r)}.00", "mrp": None, "amount": f"{_n(a)}.00"} for d, q, r, a in LINES]
    data = {
        "notice": "TEST BILL. Fictional handwritten bill for exercising the code. Not a real patient or hospital. "
                  "Never use as evaluation data.",
        "file": f"{NAME}.jpg",
        "answers": {"payer": "cash", "state": "karnataka"},
        "bill": {"header": {"hospital_name": "Sample Maternity Nursing Home", "gstin": None,
                            "admission_date": "2026-11-16", "discharge_date": "2026-11-19",
                            "bill_type": "final", "total": f"{_n(TOTAL)}.00"},
                 "lines": lines},
        "expected": {
            "findings": [
                {"rule_id": "PRC-SCHED", "item": "Inj Ringer Lactate 500ml", "verdict": "red",
                 "allowed": "364.46", "excess": "355.54",
                 "why": "NPPA S.O. 1581(E) ceiling 57.85 per 500 ml bottle + 5% GST = 60.74; billed 120 x 6"},
                {"rule_id": "PRC-SCHED", "item": "Cap Diclofenac 50mg", "verdict": "red",
                 "allowed": "8.19", "excess": "41.81",
                 "why": "NPPA S.O. 1581(E) ceiling 0.78 per capsule + 5% GST = 0.82; billed 5 x 10"},
                {"rule_id": "ARI-QTYRATE", "item": "Inj Ceftriaxone 1g", "excess": "100.00",
                 "why": "6 x 85 = 510, written as 610; on a photo it is asked about before it is counted"},
                {"rule_id": "ROOM-DAYS", "verdict": "amber", "why": "5 room days billed for a 3-night stay"},
            ],
            "recoverable_after_confirming": {
                "shipped_data": "100.00",
                "with_nppa_so1581_rows_approved_and_units_confirmed": "497.35"},
            "lines_read": 11,
            "family_confirms": "every line with a hard-to-read number, including Nursing (amount unreadable: 1,500)",
        },
    }
    (OUT / f"{NAME}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", OUT / f"{NAME}.jpg")


if __name__ == "__main__":
    main()
