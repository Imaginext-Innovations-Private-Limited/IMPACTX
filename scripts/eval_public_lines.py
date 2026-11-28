"""Stress-test line matching and the arithmetic rule on real hospital bill lines.

Source: Hugging Face dataset shaluyadav/newdatafiles (vlmbilldata_corrected.jsonl): 776 bill pages
with each page's billItems labelled (serviceName, qty, rate, amount, batch, expiry). The bills
appear to be Indian hospital bills (DD/MM/YYYY dates, TPA, bed and package lines), but the dataset
has no card and no licence, and its images are not in the repository. So:
  - this script downloads it on your machine and keeps nothing in the repo;
  - it is used only to test our code, and results are reported in aggregate;
  - eval/public_lines/sample_rows.csv holds a few rows read through the dataset viewer, for a
    smoke test only (a web tool transcribed them; check against the dataset before citing).

Run:   python scripts/eval_public_lines.py                 # downloads the full file
       python scripts/eval_public_lines.py --sample        # the 19 sample rows in the repo
Writes eval/public_lines/REPORT.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kk.kb import KnowledgeBase  # noqa: E402
from kk.rules.arithmetic import STANDARD_GST  # noqa: E402
from kk.rules.classify import knee_candidates, stent_match  # noqa: E402

URL = "https://huggingface.co/datasets/shaluyadav/newdatafiles/resolve/main/vlmbilldata_corrected.jsonl"
TOL = Decimal("1.00")


def dec(x):
    try:
        return Decimal(str(x).replace(",", "").strip()) if str(x).strip() not in ("", "None", "null") else None
    except InvalidOperation:
        return None


def rows_full():
    raw = urllib.request.urlopen(URL, timeout=120).read().decode("utf-8")
    for line in raw.splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        resp = rec.get("response")
        items = (json.loads(resp) if isinstance(resp, str) else resp or {}).get("billItems", [])
        for it in items:
            yield {"image_path": rec.get("image_path", ""), **{k: it.get(k, "") for k in
                   ("serviceCategory", "serviceName", "serviceQty", "serviceRate", "serviceAmount")}}


def rows_sample():
    with (ROOT / "eval/public_lines/sample_rows.csv").open(encoding="utf-8") as fh:
        yield from csv.DictReader(fh)


def classify_arith(q, r, a):
    if None in (q, r, a) or q == 0 or r == 0:
        return "incomplete"
    exp = q * r
    if abs(a - exp) <= TOL:
        return "matches"
    if abs(a - r) <= TOL and q != 1:
        return "rate_column_is_line_total"
    if a < exp:
        return "less_than_qty_x_rate (discount or rate is total)"
    for g in STANDARD_GST:
        if abs(a - exp * (1 + g / 100)) <= max(TOL, a * Decimal("0.002")):
            return "more_by_a_standard_GST_rate (now amber)"
    return "more_than_qty_x_rate (red in our rules)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true")
    a = ap.parse_args()
    kb = KnowledgeBase()
    rows = list(rows_sample() if a.sample else rows_full())
    pages = {r["image_path"] for r in rows}
    arith = Counter()
    red_examples, matched = [], []
    for r in rows:
        name = r["serviceName"] or ""
        s = stent_match(name, kb)
        k = knee_candidates(name)
        if s or k:
            matched.append((name, "stent:" + s["kind"] if s else "knee:" + ",".join(k[1])))
        kind = classify_arith(dec(r["serviceQty"]), dec(r["serviceRate"]), dec(r["serviceAmount"]))
        arith[kind] += 1
        if kind.startswith("more_than") and len(red_examples) < 25:
            red_examples.append(f"{name} | qty {r['serviceQty']} × {r['serviceRate']} vs {r['serviceAmount']}")
    n = len(rows)
    complete = n - arith["incomplete"]
    lines = [
        "# Real bill lines: matching and arithmetic",
        "",
        f"Source: Hugging Face `shaluyadav/newdatafiles` ({'19-row sample read through the dataset viewer' if a.sample else 'full file'}). "
        "No licence is stated; used only to test this code, reported in aggregate.",
        "",
        f"Pages: {len(pages)}. Bill lines: {n}.",
        "",
        "## Recognised as a price-capped item",
        "",
        f"{len(matched)} of {n} lines. Check each by hand: a wrong match here would be a wrong claim.",
        "",
        *[f"- {nm} → {how}" for nm, how in matched[:40]],
        "",
        "## How quantity × rate relates to the amount (lines with all three)",
        "",
        f"{complete} lines have quantity, rate and amount.",
        "",
        "| Pattern | Lines |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in arith.most_common() if k != "incomplete"],
        "",
        "Only the last pattern produces a red finding. Every such line must be read on the real bill",
        "before the rule is trusted on this kind of bill:",
        "",
        *[f"- {x}" for x in red_examples],
    ]
    out = ROOT / "eval/public_lines/REPORT.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out.read_text())


if __name__ == "__main__":
    main()
