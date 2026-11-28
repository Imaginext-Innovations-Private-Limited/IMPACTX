"""Score bill reading (OCR + line extraction) on real bill images you have collected.

Put the images in a folder with labels.csv:   image,item,qty,rate,amount
(one row per bill line, typed by a person from the image; leave unknown cells empty).
Good public sources: itemised bills attached to consumer commission orders (e-Jagriti, NCDRC),
and bill images published by news reports on overcharging (cite the URL in sources.csv).
Run any image of a real person's bill through scripts/anonymise_bill.py first.

    python scripts/eval_ocr_images.py path/to/folder

Reports, per image and overall: lines found, lines matched to a label (by item words),
amounts read exactly, and amounts read wrong (the dangerous case). Writes REPORT.md there.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kk.extraction import read_bill  # noqa: E402
from kk.figures import FigureStore  # noqa: E402


def dec(x):
    try:
        return Decimal(str(x).replace(",", "").replace("₹", "").strip()) if str(x or "").strip() else None
    except InvalidOperation:
        return None


def words(s):
    return set(re.findall(r"[a-z]{3,}", (s or "").lower()))


def main(folder: str) -> dict:
    root = Path(folder)
    labels = defaultdict(list)
    with (root / "labels.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            labels[r["image"]].append(r)
    total = {"labels": 0, "found": 0, "matched": 0, "amount_ok": 0, "amount_wrong": 0}
    rows = []
    for image, want in labels.items():
        figs = FigureStore()
        bill, _ = read_bill([str(root / image)], figs)
        got = [(l, figs.value(l.amount_fig)) for l in bill.lines]
        used = set()
        m = ok = wrong = 0
        for w in want:
            ww = words(w["item"])
            best, score = None, 0
            for i, (l, _amt) in enumerate(got):
                s = len(ww & words(l.description))
                if i not in used and s > score:
                    best, score = i, s
            if best is None or score == 0:
                continue
            used.add(best)
            m += 1
            exp, amt = dec(w["amount"]), got[best][1]
            if exp is not None and amt is not None:
                if abs(exp - amt) < Decimal("0.01"):
                    ok += 1
                else:
                    wrong += 1
        rows.append((image, len(want), len(got), m, ok, wrong))
        for k, v in zip(("labels", "found", "matched", "amount_ok", "amount_wrong"), (len(want), len(got), m, ok, wrong)):
            total[k] += v
    pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "n/a"
    rep = ["# Bill reading on real images", "", "| Image | Labelled lines | Lines read | Matched | Amount exact | Amount wrong |",
           "|---|---|---|---|---|---|", *[f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |" for r in rows], "",
           f"Overall: {total['matched']}/{total['labels']} labelled lines found ({pct(total['matched'], total['labels'])}); "
           f"amounts exact {total['amount_ok']}, wrong {total['amount_wrong']}.",
           "", "A wrong amount that the app did not flag for confirmation is the case to fix first."]
    (root / "REPORT.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep))
    return total


if __name__ == "__main__":
    main(sys.argv[1])
