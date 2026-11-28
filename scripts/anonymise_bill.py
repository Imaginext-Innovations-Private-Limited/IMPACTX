"""Black out personal details on a real bill before it is stored for evaluation.

Usage:
    python scripts/anonymise_bill.py BILL.pdf|BILL.jpg [...] --case-id KK-0001 --consent-id C-0001 \
        --out eval/cases/KK-0001

What it does
  1. Reads every page with the same OCR as the app.
  2. Blacks out (solid boxes, not blur):
       - everything after a personal label on the same line: name, patient, UHID, IP/MR/reg no,
         mobile/phone, address, age/sex, Aadhaar, ABHA, policy/card/member id, relation (S/O, W/O, D/O),
         doctor name and signature lines are kept (they are not the patient's);
       - any word that looks like an Aadhaar number (Verhoeff check), a phone number, or an email.
  3. Writes page-N.png (redacted), redaction_log.json (how many boxes and why, never the text)
     and a label.json skeleton with origin "consented_bill" for two people to fill in.

The original file is not modified and is never copied into the output folder.
A person must check every page before it is kept: OCR can miss text, so the script also writes
review.png with the boxes outlined. Delete the case if anything personal is still visible.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kk.extraction.ocr import ocr_image, pdf_words  # noqa: E402
from kk.extraction.preprocess import prepare  # noqa: E402
from kk.guard import mask_pii  # noqa: E402

LABELS = re.compile(
    r"(?i)^(patient|pt\.?|name|mr\.?|mrs\.?|ms\.?|uhid|mrn|mr\s*no|ip\s*no|ipd\s*no|reg\w*\s*no|admission\s*no|"
    r"mobile|phone|ph\.?|contact|address|addr|age|sex|gender|dob|aadhaa?r|abha|policy|member|card|beneficiary|"
    r"pmjay\s*id|s/o|w/o|d/o|c/o|father|husband|guardian|email|e-mail)\b")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def _lines(words):
    rows: list[list] = []
    for w in sorted(words, key=lambda w: (w.bbox.page, (w.bbox.y0 + w.bbox.y1) / 2, w.bbox.x0)):
        cy = (w.bbox.y0 + w.bbox.y1) / 2
        h = max(1.0, w.bbox.y1 - w.bbox.y0)
        if rows and rows[-1][0].bbox.page == w.bbox.page and \
                abs(cy - (rows[-1][0].bbox.y0 + rows[-1][0].bbox.y1) / 2) < 0.6 * h:
            rows[-1].append(w)
        else:
            rows.append([w])
    return [sorted(r, key=lambda w: w.bbox.x0) for r in rows]


def boxes_to_hide(words) -> list[tuple]:
    hide = []
    for row in _lines(words):
        text = " ".join(w.text for w in row)
        h = sorted(max(1.0, w.bbox.y1 - w.bbox.y0) for w in row)[len(row) // 2]
        i = 0
        while i < len(row):
            # a personal field is "Label:" (label words ending in a colon within three words)
            end = next((j for j in range(i, min(i + 3, len(row))) if row[j].text.endswith(":") or ":" in row[j].text), None)
            if end is not None and LABELS.match(" ".join(x.text for x in row[i:end + 1])):
                tail = row[end].text.split(":", 1)[1]
                if tail.strip():                      # "UHID:TEST-U-0001" in one OCR word
                    hide.append((row[end], "labelled_field"))
                prev = row[end]
                k = end + 1
                while k < len(row):
                    x = row[k]
                    if x.text.endswith(":") or x.bbox.x0 - prev.bbox.x1 > 2.5 * h:
                        break                         # next field, or a column gap
                    if k + 1 < len(row) and row[k + 1].text.endswith(":") and not LABELS.match(x.text):
                        break                         # "Date of Admission:" starts here
                    hide.append((x, "labelled_field"))
                    prev = x
                    k += 1
                i = k
            else:
                i += 1
        for w in row:
            _, kinds = mask_pii(w.text)
            if kinds or EMAIL.search(w.text):
                hide.append((w, kinds[0] if kinds else "email"))
        _, line_kinds = mask_pii(text)   # numbers split across OCR words
        if "aadhaar" in line_kinds or "phone" in line_kinds:
            for w in row:
                if sum(c.isdigit() for c in w.text) >= 4:
                    hide.append((w, "number_in_" + line_kinds[0]))
    seen, out = set(), []
    for w, why in hide:
        if w.id not in seen:
            seen.add(w.id)
            out.append((w, why))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--case-id", required=True)
    ap.add_argument("--consent-id", required=True, help="id of the signed consent form kept offline")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    pages, words = [], []
    for f in a.files:
        if f.lower().endswith(".pdf"):
            ws, _, imgs = pdf_words(f)
            off = len(pages)
            for w in ws:
                w.bbox.page += off
            words += ws
            pages += imgs
        else:
            img = prepare(f)[0]
            pages.append(img)
            words += ocr_image(img, len(pages), len(words))

    hide = boxes_to_hide(words)
    log = {"case_id": a.case_id, "pages": len(pages), "boxes": len(hide), "by_reason": {}}
    for _, why in hide:
        log["by_reason"][why] = log["by_reason"].get(why, 0) + 1
    files = []
    for pno, img in enumerate(pages, start=1):
        red = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img.copy()
        review = red.copy()
        for w, _ in hide:
            if w.bbox.page != pno:
                continue
            p = 4
            pt1 = (int(w.bbox.x0) - p, int(w.bbox.y0) - p)
            pt2 = (int(w.bbox.x1) + p, int(w.bbox.y1) + p)
            cv2.rectangle(red, pt1, pt2, (0, 0, 0), -1)
            cv2.rectangle(review, pt1, pt2, (0, 0, 255), 3)
        name = f"page-{pno}.png"
        cv2.imwrite(str(out / name), red)
        cv2.imwrite(str(out / f"review-{pno}.png"), np.hstack([review, red]))
        files.append(name)
    (out / "redaction_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    label = out / "label.json"
    if not label.exists():
        label.write_text(json.dumps({
            "origin": "consented_bill", "consent_id": a.consent_id, "files": files,
            "answers": {"payer": "", "state": "", "hospital_empanelled": None, "scheme_booked": None,
                        "patient_paid": None},
            "lines": [], "expected": [],
            "labelled_by": ["", ""], "agreement_notes": "",
        }, indent=2), encoding="utf-8")
    print(json.dumps(log, indent=2))
    print(f"Check every review-N.png in {out} by eye before keeping this case; then delete the review images.")


if __name__ == "__main__":
    main()
