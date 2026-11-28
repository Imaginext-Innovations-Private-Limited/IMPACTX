"""Generate the three TEST hospital bills used to exercise every rule.

These are fictional test fixtures, not real patients or hospitals, and must never be used
as evaluation data or for any claim. Every page carries a "TEST BILL - NOT A REAL PATIENT"
banner and watermark. Real-world accuracy is measured only with eval/cases (real bills).

Run:  python tests/fixtures/sample_bills/make_bills.py
Writes, for each bill: the document (PDF or JPG), <name>.json (typed-in version, answers to
the app's questions, and the expected results worked out by hand from the official limits).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent
BANNER = "TEST BILL - NOT A REAL PATIENT - NOT VALID FOR ANY CLAIM"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ----------------------------------------------------------------------------- bill data
# Each line: (description, date, batch, expiry, qty, rate, mrp, amount)

BILL1 = {
    "name": "bill1_cardiac_cash",
    "format": "pdf",
    "hospital": "Sample Heart Hospital",
    "address": "12 Test Road, Jayanagar, Bengaluru 560011, Karnataka",
    "gstin": "29TESTB0000T1Z5",
    "title": "FINAL BILL",
    "meta": [("Bill No", "TEST-0001"), ("Patient Name", "Test Patient A"), ("UHID", "TEST-U-0001"),
             ("Date of Admission", "18/11/2026"), ("Date of Discharge", "20/11/2026")],
    "sections": [
        ("IMPLANTS", [
            ("Drug Eluting Stent (Everolimus) 3.0x28", "19/11/2026", "XB2611", "30/06/2028", "1", "58,000.00", "", "58,000.00"),
            ("Coronary Stent Xience Alpine 3.5x18", "19/11/2026", "XA7781", "31/12/2027", "1", "44,000.00", "", "44,000.00"),
        ]),
        ("CATH LAB CONSUMABLES", [
            ("PTCA Guide Wire 0.014", "19/11/2026", "GW5521", "31/03/2028", "2", "3,500.00", "", "7,500.00"),
            ("Balloon Catheter 2.5x15", "19/11/2026", "BC3310", "30/09/2027", "1", "9,800.00", "", "9,800.00"),
        ]),
        ("PHARMACY", [
            ("Inj Enoxaparin 40mg", "19/11/2026", "EN4410", "31/05/2027", "4", "520.00", "455.00", "2,080.00"),
            ("Tab Clopidogrel 75mg", "20/11/2026", "CL9902", "", "10", "8.50", "9.20", "85.00"),
            ("Tab Atorvastatin 40mg", "20/11/2026", "AT1201", "31/01/2028", "10", "22.00", "24.50", "220.00"),
        ]),
        ("INVESTIGATIONS", [
            ("Lipid Profile", "18/11/2026", "", "", "1", "650.00", "", "650.00"),
            ("Lipid Profile", "18/11/2026", "", "", "1", "650.00", "", "650.00"),
            ("ECG", "25/11/2026", "", "", "1", "300.00", "", "300.00"),
        ]),
        ("ROOM CHARGES", [
            ("Room Rent Twin Sharing", "18/11/2026", "", "", "5", "2,500.00", "", "12,500.00"),
        ]),
        ("PROCEDURE", [
            ("PTCA Procedure Charges", "19/11/2026", "", "", "1", "45,000.00", "", "45,000.00"),
        ]),
    ],
    "totals": [("Grand Total", "1,82,785.00"), ("Less: Advance Paid", "50,000.00"), ("Net Payable", "1,32,785.00")],
    "answers": {"payer": "cash", "state": "karnataka"},
    "expected": {
        "recoverable": "20469.34",
        "amber_total": "2650.00",
        "findings": [
            {"rule_id": "PRC-STENT", "match": "Everolimus", "verdict": "red", "excess": "16854.67",
             "why": "1 x 39,186.03 x 1.05 = 41,145.33 allowed; billed 58,000"},
            {"rule_id": "PRC-STENT", "match": "Xience", "verdict": "red", "excess": "2854.67",
             "why": "stent type not printed: higher DES ceiling used (condition shown)"},
            {"rule_id": "ARI-QTYRATE", "match": "Guide Wire", "verdict": "red", "excess": "500.00",
             "why": "2 x 3,500 = 7,000 but billed 7,500"},
            {"rule_id": "PRC-MRP", "match": "Enoxaparin", "verdict": "red", "excess": "260.00",
             "why": "4 x MRP 455 = 1,820 but billed 2,080"},
            {"rule_id": "CONV-DUPLICATE", "match": "Lipid", "verdict": "amber", "excess": "650.00"},
            {"rule_id": "CONV-OUTSIDE-STAY", "match": "ECG", "verdict": "amber"},
            {"rule_id": "CONV-ROOMDAYS", "verdict": "amber", "why": "5 room days for 2 nights"},
            {"rule_id": "ARI-TOTAL", "verdict": "amber", "excess": "2000.00",
             "why": "lines add to 1,80,785 but grand total is 1,82,785"},
            {"rule_id": "FMT-MISSING", "verdict": "amber", "why": "Clopidogrel has no expiry date"},
            {"rule_id": "STATE-KA-DISCLOSURE", "verdict": "info"},
        ],
        "not_expected": ["ENT-COVERED", "ENT-CASH-DENIAL", "RGT-ITEMISED"],
    },
}

BILL2 = {
    "name": "bill2_knee_pmjay",
    "format": "pdf",
    "hospital": "Sample Ortho Hospital",
    "address": "7 Test Lane, Navrangpura, Ahmedabad 380009, Gujarat",
    "gstin": "24TESTB0000T1Z9",
    "title": "FINAL BILL",
    "meta": [("Bill No", "TEST-0002"), ("Patient Name", "Test Patient B"), ("Scheme", "AB PM-JAY"),
             ("Pre-auth No", "TEST-PA-0002"), ("Date of Admission", "10/11/2026"), ("Date of Discharge", "15/11/2026")],
    "sections": [
        ("IMPLANTS", [
            ("Femoral Component Titanium Primary Knee", "11/11/2026", "FK2201", "31/12/2029", "1", "62,000.00", "", "62,000.00"),
            ("Tibial Tray with Insert Metal", "11/11/2026", "TT4410", "31/12/2029", "1", "38,000.00", "", "38,000.00"),
            ("Patella Button", "11/11/2026", "PB1107", "31/12/2029", "1", "6,500.00", "", "6,500.00"),
        ]),
        ("PHARMACY", [
            ("Inj Ceftriaxone 1g", "11/11/2026", "CF2210", "31/10/2027", "6", "65.00", "72.00", "390.00"),
            ("Inj Tramadol 50mg", "12/11/2026", "TR3301", "30/04/2027", "6", "18.00", "21.00", "108.00"),
        ]),
        ("CONSUMABLES", [
            ("Surgical Drape Kit", "11/11/2026", "SD7719", "31/08/2028", "1", "3,200.00", "", "3,200.00"),
        ]),
        ("ROOM CHARGES", [
            ("Deluxe Room Upgrade Charges", "10/11/2026", "", "", "5", "2,000.00", "", "10,000.00"),
        ]),
        ("PHYSIOTHERAPY", [
            ("Physiotherapy Session", "14/11/2026", "", "", "3", "500.00", "", "1,500.00"),
            ("Attendant Diet Charges", "10/11/2026", "", "", "5", "150.00", "", "750.00"),
        ]),
    ],
    "totals": [("Grand Total", "1,22,448.00"), ("Amount Paid by Patient", "1,22,448.00")],
    "answers": {"payer": "pmjay", "state": "gujarat", "hospital_empanelled": True, "patient_paid": True},
    "expected": {
        "recoverable": "111698.00",
        "amber_total": None,
        "findings": [
            {"rule_id": "ENT-COVERED", "match": "Femoral", "verdict": "red", "excess": "62000.00"},
            {"rule_id": "PRC-KNEE", "match": "Femoral", "verdict": "red", "excess": "7858.91",
             "why": "51,562.94 x 1.05 = 54,141.09 allowed; the larger scheme claim counts for this line"},
            {"rule_id": "ENT-COVERED", "match": "Tibial", "verdict": "red", "excess": "38000.00"},
            {"rule_id": "PRC-KNEE", "match": "Tibial", "verdict": "red", "excess": "900.63",
             "why": "tray with insert 35,332.73 x 1.05 = 37,099.37 allowed"},
            {"rule_id": "ENT-COVERED", "match": "Patella", "verdict": "red", "excess": "6500.00"},
            {"rule_id": "PRC-KNEE", "match": "Patella", "verdict": "red", "excess": "784.02",
             "why": "5,443.79 x 1.05 = 5,715.98 allowed"},
            {"rule_id": "ENT-COVERED", "match": "Ceftriaxone", "verdict": "red", "excess": "390.00"},
            {"rule_id": "ENT-COVERED", "match": "Tramadol", "verdict": "red", "excess": "108.00"},
            {"rule_id": "ENT-COVERED", "match": "Drape", "verdict": "red", "excess": "3200.00"},
            {"rule_id": "ENT-COVERED", "match": "Physiotherapy", "verdict": "red", "excess": "1500.00"},
            {"rule_id": "ENT-COVERED", "match": "Deluxe", "verdict": "amber", "why": "room upgrade: ask, do not claim"},
            {"rule_id": "ENT-COVERED", "match": "Attendant", "verdict": "amber", "why": "non-medical charge"},
        ],
        "not_expected": ["ENT-CASH-DENIAL", "PRC-STENT", "CONV-ROOMDAYS", "STATE-KA-DISCLOSURE"],
    },
}

BILL3 = {
    "name": "bill3_interim_photo",
    "format": "jpg",
    "hospital": "Sample City Hospital",
    "address": "3 Test Circle, Malleshwaram, Bengaluru 560003, Karnataka",
    "gstin": "29TESTB0000T2Z3",
    "title": "INTERIM BILL",
    "meta": [("Bill No", "TEST-0003"), ("Patient Name", "Test Patient C"),
             ("Date of Admission", "10/03/2026"), ("Bill Date", "12/03/2026")],
    "sections": [
        ("", [
            ("PTCA Package All Inclusive", "10/03/2026", "", "", "1", "2,10,000.00", "", "2,10,000.00"),
            ("Drug Eluting Stent", "11/03/2026", "", "", "1", "52,000.00", "", "52,000.00"),
        ]),
    ],
    "totals": [("Grand Total", "2,62,000.00")],
    "answers": {"payer": "pmjay", "state": "karnataka", "hospital_empanelled": True, "scheme_booked": False},
    "expected": {
        "recoverable": "262000.00",
        "amber_total": None,
        "findings": [
            {"rule_id": "ENT-CASH-DENIAL", "verdict": "red", "excess": "262000.00",
             "why": "card holder at an empanelled hospital, case not booked under the scheme"},
            {"rule_id": "PRC-STENT", "match": "Stent", "verdict": "grey",
             "why": "March 2026: no verified stent ceiling loaded for that date (2026 ceilings start 1 April 2026)"},
            {"rule_id": "RGT-ITEMISED", "verdict": "amber", "why": "one package line is over 80% of the bill"},
        ],
        "not_expected": ["ENT-COVERED", "STATE-KA-DISCLOSURE"],
    },
}


BILL5 = {
    # Outlier test: extreme, impossible and edge-case values. The app must flag what rules cover,
    # never crash, and never treat a broken number as a fact.
    "name": "bill5_outlier_extremes",
    "format": "pdf",
    "hospital": "Sample Super Speciality Hospital",
    "address": "99 Test Avenue, Whitefield, Bengaluru 560066, Karnataka",
    "gstin": "29TESTB0000T5Z1",
    "title": "FINAL BILL",
    "meta": [("Bill No", "TEST-0005"), ("Patient Name", "Test Patient E"), ("UHID", "TEST-U-0005"),
             ("Date of Admission", "10/11/2026"), ("Date of Discharge", "12/11/2026")],
    "sections": [
        ("IMPLANTS", [
            ("Drug Eluting Stent (Everolimus) 3.0x28", "11/11/2026", "XB9001", "30/06/2028", "1", "9,85,000.00", "", "9,85,000.00"),
            ("Drug Eluting Stent (Sirolimus) 2.75x18", "11/11/2026", "SR9002", "31/12/2027", "12", "40,000.00", "", "4,80,000.00"),
        ]),
        ("CATH LAB CONSUMABLES", [
            ("Balloon Catheter 2.5x15", "11/11/2026", "BC9003", "30/09/2027", "1", "9,800.00", "", "98,000.00"),
            ("Surgical Gloves (pair)", "11/11/2026", "", "", "1", "0.00", "", "0.00"),
            ("Disposable Syringe 5ml", "11/11/2026", "SY9004", "31/03/2029", "3", "0.01", "", "0.03"),
        ]),
        ("PHARMACY", [
            ("Inj Enoxaparin 40mg", "11/11/2026", "EN9005", "31/05/2027", "1", "52,000.00", "455.00", "52,000.00"),
            ("Tab Paracetamol 500mg", "12/11/2026", "PC9006", "31/01/2028", "10000", "2.00", "2.10", "20,000.00"),
            ("Pharmacy Return - Inj Enoxaparin 40mg", "12/11/2026", "EN9005", "31/05/2027", "-5", "455.00", "455.00", "-2,275.00"),
        ]),
        ("INVESTIGATIONS", [
            ("CT Scan Brain", "02/01/2024", "", "", "1", "3,500.00", "", "3,500.00"),
            ("Lipid Profile", "10/11/2026", "", "", "1", "650.00", "", "650.00"),
        ]),
        ("ROOM CHARGES", [
            ("ICU Room Rent", "10/11/2026", "", "", "45", "25,000.00", "", "11,25,000.00"),
        ]),
        ("PROCEDURE", [
            ("PTCA Procedure Charges", "11/11/2026", "", "", "1", "45,000.00", "", "45,000.00"),
        ]),
    ],
    "totals": [("Grand Total", "1,00,00,000.00"), ("Net Payable", "1,00,00,000.00")],
    "answers": {"payer": "cash", "state": "karnataka"},
    "expected": {
        "recoverable": "1083599.67",
        "amber_total": "7193124.97",
        "findings": [
            {"rule_id": "PRC-STENT", "match": "Everolimus", "verdict": "red", "excess": "943854.67",
             "why": "1 x 39,186.03 x 1.05 = 41,145.33 allowed; billed 9,85,000 (about 24 times the cap)"},
            {"rule_id": "PRC-MRP", "match": "^Inj Enoxaparin", "verdict": "red", "excess": "51545.00",
             "why": "1 x MRP 455 = 455 but billed 52,000"},
            {"rule_id": "ARI-QTYRATE", "match": "Balloon", "verdict": "red", "excess": "88200.00",
             "why": "1 x 9,800 = 9,800 but billed 98,000 (a misplaced zero)"},
            {"rule_id": "ARI-TOTAL", "verdict": "amber", "excess": "7193124.97",
             "why": "lines add to 28,06,875.03 but the total says 1,00,00,000"},
            {"rule_id": "CONV-ROOMDAYS", "match": "ICU", "verdict": "amber", "why": "45 room days for 2 nights"},
            {"rule_id": "CONV-OUTSIDE-STAY", "match": "CT Scan", "verdict": "amber", "why": "dated 02/01/2024"},
        ],
        "not_expected": ["ENT-COVERED", "ENT-CASH-DENIAL"],
        "edge_cases_read_as_printed": [
            "zero line (gloves, 0.00)", "3 paise line (syringes, 0.03)", "negative return line (-5 x 455 = -2,275)",
            "1 crore total", "test dated 2024"],
        "known_gaps": [
            "12 stents (each under the cap) and 10,000 paracetamol tablets in a 2-night stay are not flagged: "
            "no official rule limits how many may be billed, and the app does not invent a threshold"],
    },
}

BILL6 = {
    # GST test: a medical admission (no surgery) where the hospital adds CGST and SGST to the whole
    # bill. Every room here is ICU or at most Rs 5000 a day, and treatment is exempt, so no GST is due.
    "name": "bill6_gst_on_treatment",
    "format": "pdf",
    "hospital": "Sample Multispeciality Hospital",
    "address": "7 Test Road, Hubballi 580020, Karnataka",
    "gstin": "29TESTB0000T6Z8",
    "title": "FINAL BILL",
    "meta": [("Bill No", "TEST-0006"), ("Patient Name", "Test Patient F"), ("UHID", "TEST-U-0006"),
             ("Date of Admission", "10/11/2026"), ("Date of Discharge", "14/11/2026")],
    "sections": [
        ("ROOM CHARGES", [
            ("ICU Charges", "10/11/2026", "", "", "1", "9,000.00", "", "9,000.00"),
            ("Twin Sharing Room Rent", "11/11/2026", "", "", "3", "3,500.00", "", "10,500.00"),
        ]),
        ("DOCTOR CHARGES", [
            ("Consultation - Physician", "10/11/2026", "", "", "4", "800.00", "", "3,200.00"),
        ]),
        ("INVESTIGATIONS", [
            ("Platelet Count", "10/11/2026", "", "", "4", "300.00", "", "1,200.00"),
            ("Dengue NS1 Antigen", "10/11/2026", "", "", "1", "1,200.00", "", "1,200.00"),
        ]),
        ("PHARMACY", [
            ("IV Ringer Lactate 500ml", "10/11/2026", "RL6001", "31/08/2028", "8", "60.00", "60.00", "480.00"),
        ]),
        ("TAXES", [
            ("CGST @ 9%", "14/11/2026", "", "", "", "", "", "2,259.00"),
            ("SGST @ 9%", "14/11/2026", "", "", "", "", "", "2,259.00"),
        ]),
    ],
    "totals": [("Grand Total", "30,098.00"), ("Net Payable", "30,098.00")],
    "answers": {"payer": "cash", "state": "karnataka"},
    "expected": {
        "recoverable": "4518.00",
        "amber_total": None,
        "findings": [
            {"rule_id": "TAX-GST", "match": "^CGST", "verdict": "red", "excess": "4518.00",
             "why": "CGST 2,259 + SGST 2,259 = 4,518 on an in-patient bill. Treatment is exempt (CBIC Circular "
                    "32/06/2018 Sl. 5); ICU is exempt whatever it costs and the twin room is 3,500 a day, not above "
                    "5,000 (Notification 04/2022-CT(Rate)), so no GST is due on any line: all 4,518 is excess"},
        ],
        "not_expected": ["ARI-TOTAL", "ENT-COVERED", "PRC-MRP"],
    },
}

BILLS = [BILL1, BILL2, BILL3, BILL5, BILL6]

# ----------------------------------------------------------------------------- helpers

def _num(s: str) -> str | None:
    return s.replace(",", "") if s else None


def structured(bill: dict) -> dict:
    """The same bill as typed into the app's 'Type it in' mode."""
    meta = dict(bill["meta"])
    to_iso = lambda d: "-".join(reversed(d.split("/"))) if d else None
    sec_map = {"IMPLANTS": "implant", "PHARMACY": "pharmacy", "CATH LAB CONSUMABLES": "consumables",
               "CONSUMABLES": "consumables", "INVESTIGATIONS": "diagnostics", "ROOM CHARGES": "room",
               "PROCEDURE": "procedure", "DOCTOR CHARGES": "professional"}
    lines = []
    for sec, rows in bill["sections"]:
        for desc, date, batch, exp, qty, rate, mrp, amount in rows:
            lines.append({"description": desc, "section": sec_map.get(sec), "date": to_iso(date),
                          "batch": batch or None, "expiry": exp or None, "qty": _num(qty), "rate": _num(rate),
                          "mrp": _num(mrp), "amount": _num(amount)})
    header = {"hospital_name": bill["hospital"], "gstin": bill["gstin"],
              "admission_date": to_iso(meta.get("Date of Admission")),
              "discharge_date": to_iso(meta.get("Date of Discharge")),
              "bill_type": "interim" if "INTERIM" in bill["title"] else "final",
              "total": _num(bill["totals"][0][1])}
    if "Scheme" in meta or "Pre-auth No" in meta:
        header["scheme_markers"] = ["PMJAY", "pre-auth"]
    return {"header": header, "lines": lines}


def watermark_png(w: int, h: int) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT_B, int(w / 14))
    d.text((w / 2, h / 2), "TEST BILL", font=f, fill=(200, 30, 50, 38), anchor="mm")
    return img.rotate(30, expand=False)


# ----------------------------------------------------------------------------- PDF (text layer)
COLS = {"desc": 36, "date": 228, "batch": 288, "exp": 342}
RIGHT = {"qty": 430, "rate": 480, "mrp": 522, "amount": 566}


def make_pdf(bill: dict, path: Path) -> None:
    W, H = A4
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle(f"{BANNER} ({bill['name']})")
    wm = watermark_png(1200, 1700)
    c.drawImage(ImageReader(wm), 0, 0, W, H, mask="auto")
    y = H - 34
    c.setFont("Helvetica-Bold", 8)
    c.setFillColorRGB(.8, .1, .2)
    c.drawCentredString(W / 2, y, BANNER)
    c.setFillColorRGB(0, 0, 0)
    y -= 26
    c.setFont("Helvetica-Bold", 16)
    c.drawString(36, y, bill["hospital"])
    y -= 14
    c.setFont("Helvetica", 9)
    c.drawString(36, y, bill["address"])
    y -= 12
    c.drawString(36, y, f"GSTIN: {bill['gstin']}")
    y -= 22
    c.setFont("Helvetica-Bold", 12)
    c.drawString(36, y, bill["title"])
    y -= 18
    c.setFont("Helvetica", 9)
    meta = bill["meta"]
    for i in range(0, len(meta), 2):
        left = meta[i]
        c.drawString(36, y, f"{left[0]}: {left[1]}")
        if i + 1 < len(meta):
            right = meta[i + 1]
            c.drawString(310, y, f"{right[0]}: {right[1]}")
        y -= 13
    y -= 10
    c.line(36, y + 12, 566, y + 12)
    c.setFont("Helvetica-Bold", 9)
    for key, label in (("desc", "Description"), ("date", "Date"), ("batch", "Batch"), ("exp", "Exp")):
        c.drawString(COLS[key], y, label)
    for key, label in (("qty", "Qty"), ("rate", "Rate"), ("mrp", "MRP"), ("amount", "Amount")):
        c.drawRightString(RIGHT[key], y, label)
    y -= 6
    c.line(36, y, 566, y)
    y -= 14
    for sec, rows in bill["sections"]:
        if sec:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(36, y, sec)
            y -= 14
        c.setFont("Helvetica", 8.5)
        for desc, date, batch, exp, qty, rate, mrp, amount in rows:
            c.drawString(COLS["desc"], y, desc)
            c.drawString(COLS["date"], y, date)
            if batch:
                c.drawString(COLS["batch"], y, batch)
            if exp:
                c.drawString(COLS["exp"], y, exp)
            for key, val in (("qty", qty), ("rate", rate), ("mrp", mrp), ("amount", amount)):
                if val:
                    c.drawRightString(RIGHT[key], y, val)
            y -= 14
        y -= 4
    c.line(36, y + 8, 566, y + 8)
    y -= 8
    c.setFont("Helvetica-Bold", 10)
    for label, val in bill["totals"]:
        c.drawString(330, y, label)
        c.drawRightString(RIGHT["amount"], y, val)
        y -= 15
    c.setFont("Helvetica-Bold", 8)
    c.setFillColorRGB(.8, .1, .2)
    c.drawCentredString(W / 2, 30, BANNER)
    c.save()


# ----------------------------------------------------------------------------- photo (OCR path)

def make_photo(bill: dict, path: Path) -> None:
    W, H = 1700, 1500
    page = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(page)
    f = ImageFont.truetype(FONT, 30)
    fb = ImageFont.truetype(FONT_B, 30)
    fh = ImageFont.truetype(FONT_B, 44)
    d.text((W / 2, 40), BANNER, font=ImageFont.truetype(FONT_B, 26), fill=(200, 30, 50), anchor="mt")
    y = 110
    d.text((70, y), bill["hospital"], font=fh, fill="black"); y += 64
    d.text((70, y), bill["address"], font=f, fill="black"); y += 46
    d.text((70, y), f"GSTIN: {bill['gstin']}", font=f, fill="black"); y += 70
    d.text((70, y), bill["title"], font=fb, fill="black"); y += 60
    for k, v in bill["meta"]:
        d.text((70, y), f"{k}: {v}", font=f, fill="black"); y += 46
    y += 30
    cols = {"desc": 70, "date": 760, "qty": 1080, "rate": 1330, "amount": 1630}
    d.text((cols["desc"], y), "Description", font=fb, fill="black")
    d.text((cols["date"], y), "Date", font=fb, fill="black")
    for key, label in (("qty", "Qty"), ("rate", "Rate"), ("amount", "Amount")):
        d.text((cols[key], y), label, font=fb, fill="black", anchor="ra")
    y += 50
    d.line((70, y, 1640, y), fill="black", width=2)
    y += 24
    for _sec, rows in bill["sections"]:
        for desc, date, _b, _e, qty, rate, _m, amount in rows:
            d.text((cols["desc"], y), desc, font=f, fill="black")
            d.text((cols["date"], y), date, font=f, fill="black")
            for key, val in (("qty", qty), ("rate", rate), ("amount", amount)):
                d.text((cols[key], y), val, font=f, fill="black", anchor="ra")
            y += 64
    d.line((70, y, 1640, y), fill="black", width=2)
    y += 24
    for label, val in bill["totals"]:
        d.text((900, y), label, font=fb, fill="black")
        d.text((cols["amount"], y), val, font=fb, fill="black", anchor="ra")
        y += 56
    page.paste(Image.alpha_composite(page.convert("RGBA"), watermark_png(W, H)).convert("RGB"))
    # make it look like a phone photo: slight tilt, warm table background, noise, softness
    rnd = random.Random(3)
    photo = page.rotate(1.3, expand=True, fillcolor=(120, 95, 70), resample=Image.BICUBIC)
    px = photo.load()
    for _ in range(25000):
        x, yy = rnd.randrange(photo.width), rnd.randrange(photo.height)
        r, g, b = px[x, yy]
        n = rnd.randint(-28, 28)
        px[x, yy] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n)))
    photo = photo.filter(ImageFilter.GaussianBlur(0.6))
    photo.save(path, quality=86)


def main() -> None:
    for bill in BILLS:
        doc = OUT / f"{bill['name']}.{bill['format']}"
        if bill["format"] == "pdf":
            make_pdf(bill, doc)
        else:
            make_photo(bill, doc)
        info = {
            "notice": BANNER + ". Fictional test fixture; never use as evaluation data.",
            "file": doc.name,
            "answers": bill["answers"],
            "bill": structured(bill),
            "expected": bill["expected"],
        }
        (OUT / f"{bill['name']}.json").write_text(json.dumps(info, indent=2, ensure_ascii=False))
        print("wrote", doc.name)


if __name__ == "__main__":
    main()
