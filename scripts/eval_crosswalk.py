"""Measure the bill-text -> rule crosswalk on text that hospitals actually publish.

Inputs (eval/crosswalk/): stent brand strings copied verbatim from hospital stent price lists
(published under the NPPA display requirement), with each hospital's own DES/BMS label where it
gives one, and knee component labels from a hospital implant price list.

Reports, with and without the brand table (data/reference/stent_brands.csv):
  recognised   the line is recognised as a coronary stent / knee component at all
  right_cap    the ceiling used is the right one or the higher one (never the lower one)
  inflates     the ceiling used is LOWER than the true one, which would inflate a claim (must be 0)
The brand table was compiled from these same lists, so "with table" shows that real spellings are
handled; "without table" is the honest estimate for brands the table has never seen.
Run: python scripts/eval_crosswalk.py  (writes eval/crosswalk/REPORT.md)
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kk.kb import KnowledgeBase  # noqa: E402
from kk.rules.classify import knee_candidates, stent_match  # noqa: E402

RANK = {"stent_bms": 0, "stent_des": 1, "stent_unknown": 1}   # unknown is checked against DES


def stent_eval(kb) -> dict:
    rows = list(csv.DictReader((ROOT / "eval/crosswalk/hospital_stent_strings.csv").open(encoding="utf-8")))
    out = {"n": len(rows), "labelled": sum(1 for r in rows if r["hospital_type_label"])}
    misses = []
    rec = right = infl = 0
    for r in rows:
        m = stent_match(r["text_as_published"], kb)
        if m is None:
            misses.append(r["text_as_published"])
            continue
        rec += 1
        lab = r["hospital_type_label"]
        if lab:
            true = "stent_des" if lab == "DES" else "stent_bms"
            if RANK[m["kind"]] >= RANK[true]:
                right += 1
            else:
                infl += 1
    out.update(recognised=rec, right_cap=right, inflates=infl, misses=misses)
    return out


def knee_eval() -> dict:
    rows = list(csv.DictReader((ROOT / "eval/crosswalk/hospital_knee_strings.csv").open(encoding="utf-8")))
    ok, bad = 0, []
    for r in rows:
        c = knee_candidates(r["text_as_published"])
        if c and c[1] == [r["expected_component"]]:
            ok += 1
        else:
            bad.append((r["text_as_published"], c[1] if c else None))
    return {"n": len(rows), "component_ok": ok, "wrong": bad}


def main() -> dict:
    kb = KnowledgeBase()
    with_table = stent_eval(kb)
    without = stent_eval(None)
    knee = knee_eval()
    pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "n/a"
    lines = [
        "# Crosswalk evaluation on hospital-published text",
        "",
        f"Stent strings: {with_table['n']} rows from 7 hospital price-list pages "
        f"({with_table['labelled']} carry the hospital's own DES/BMS label). Knee strings: {knee['n']} rows.",
        "",
        "| Measure | With brand table | Without brand table |",
        "|---|---|---|",
        f"| Recognised as a coronary stent | {with_table['recognised']}/{with_table['n']} ({pct(with_table['recognised'], with_table['n'])}) "
        f"| {without['recognised']}/{without['n']} ({pct(without['recognised'], without['n'])}) |",
        f"| Right or higher ceiling, of labelled rows | {with_table['right_cap']}/{with_table['labelled']} "
        f"| {without['right_cap']}/{without['labelled']} recognised rows |",
        f"| Lower ceiling than the true one (would inflate a claim) | {with_table['inflates']} | {without['inflates']} |",
        "",
        f"Knee component recognised correctly: {knee['component_ok']}/{knee['n']}.",
        "",
        "Not recognised with the brand table: " + (", ".join(with_table["misses"]) or "none") + ".",
        "",
        "Not recognised without it (what an unseen brand looks like): " + (", ".join(without["misses"]) or "none") + ".",
        "",
        "An unrecognised line is never claimed against: it is shown as 'no official price limit loaded'",
        "and gets only arithmetic, duplicate and date checks. Recognition gaps cost coverage, not accuracy.",
        "The brand table was compiled from these same lists, so the 'with' column shows that real spellings",
        "(\"SYNERGY-XD, MEGATRON\", \"Xience Alpine / Xpedition\", \"INTEGRITY RESOLUTE (DES)\") are handled; it is",
        "not a measure of generalisation. Real consented bills are the next test (see pilot/).",
    ]
    (ROOT / "eval/crosswalk/REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"with": with_table, "without": without, "knee": knee}


if __name__ == "__main__":
    r = main()
    print((ROOT / "eval/crosswalk/REPORT.md").read_text())
