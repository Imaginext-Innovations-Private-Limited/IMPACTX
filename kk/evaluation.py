"""Evaluation on real cases only.

Each case is a folder in eval/cases/<case_id>/ with the bill files and a label.json:

{
  "origin": "consented_bill" | "decided_case",
  "citation": "for decided cases: commission, case number, date, URL",
  "consent_id": "for consented bills: id of the signed consent form (stored offline)",
  "files": ["page1.jpg", "page2.jpg"],          # omit for decided cases entered as structured bills
  "structured_bill": {...},                      # same format as /api/audit-structured, for decided cases
  "answers": {"payer": "cash", "state": "karnataka", ...},
  "lines": [ {"match": "stent", "qty": "1", "rate": "58000", "amount": "58000"} ],
  "expected": [ {"rule_id": "PRC-STENT", "match": "stent", "verdict": "red", "excess": "16854.67"} ]
}

Labels are written by two people independently; disagreements are resolved before use.
No case may be generated or simulated.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from .compose import render_finding
from .compose.verifier import SLOT
from .models import Verdict
from .service import Auditor


@dataclass
class Scores:
    field_tp: int = 0
    field_fp: int = 0
    field_fn: int = 0
    red_tp: int = 0
    red_fp: int = 0
    red_fn: int = 0
    excess_exact: int = 0
    excess_total: int = 0
    unsupported_numbers: int = 0
    cases: int = 0
    notes: list[str] = field(default_factory=list)

    def report(self) -> dict:
        def ratio(a, b):
            return round(a / b, 4) if b else None
        p = ratio(self.field_tp, self.field_tp + self.field_fp)
        r = ratio(self.field_tp, self.field_tp + self.field_fn)
        f1 = round(2 * p * r / (p + r), 4) if p and r else None
        return {
            "cases": self.cases,
            "field_extraction": {"precision": p, "recall": r, "f1": f1},
            "red_verdicts": {"precision": ratio(self.red_tp, self.red_tp + self.red_fp),
                             "recall": ratio(self.red_tp, self.red_tp + self.red_fn),
                             "tp": self.red_tp, "fp": self.red_fp, "fn": self.red_fn},
            "excess_exact_match": ratio(self.excess_exact, self.excess_total),
            "unsupported_numbers_in_output": self.unsupported_numbers,
            "notes": self.notes,
        }


def _line_for(session, pattern: str):
    rx = re.compile(pattern, re.IGNORECASE)
    return next((l for l in session.bill.lines if rx.search(l.description)), None)


def _num(figs, fid):
    return figs.value(fid) if fid else None


def evaluate(cases_dir: str, auditor: Auditor | None = None) -> dict:
    auditor = auditor or Auditor()
    sc = Scores()
    for case in sorted(Path(cases_dir).glob("*/label.json")):
        label = json.loads(case.read_text(encoding="utf-8"))
        if label.get("origin") not in ("consented_bill", "decided_case"):
            sc.notes.append(f"{case.parent.name}: skipped, origin must be consented_bill or decided_case")
            continue
        sc.cases += 1
        if label.get("files"):
            s = auditor.audit_files([str(case.parent / f) for f in label["files"]], label.get("answers", {}))
        else:
            s = auditor.audit_structured(label["structured_bill"], label.get("answers", {}))
        figs = s.figs
        # field extraction
        for exp in label.get("lines", []):
            line = _line_for(s, exp["match"])
            for key, attr in (("qty", "qty_fig"), ("rate", "rate_fig"), ("amount", "amount_fig")):
                if key not in exp:
                    continue
                got = _num(figs, getattr(line, attr)) if line else None
                if got is not None and got == Decimal(exp[key]):
                    sc.field_tp += 1
                else:
                    sc.field_fn += 1
                    if got is not None:
                        sc.field_fp += 1
        # red verdicts and amounts
        reds = [f for f in s.result.findings if f.verdict == Verdict.RED]
        matched = set()
        for exp in label.get("expected", []):
            if exp.get("verdict") != "red":
                continue
            line = _line_for(s, exp["match"]) if exp.get("match") else None
            hit = next((f for f in reds if f.rule_id == exp["rule_id"] and
                        (line is None or f.line_id == line.id) and id(f) not in matched), None)
            if hit:
                sc.red_tp += 1
                matched.add(id(hit))
                if "excess" in exp:
                    sc.excess_total += 1
                    if hit.excess_fig and figs.value(hit.excess_fig) == Decimal(exp["excess"]):
                        sc.excess_exact += 1
            else:
                sc.red_fn += 1
        sc.red_fp += sum(1 for f in reds if id(f) not in matched)
        # every number in every rendered message must come from the figure store
        for f in s.result.findings:
            for lang in ("en", "hi", "kn", "gu", "ta", "te"):
                rf = render_finding(f, s.result, lang)
                text_only = "".join(seg["t"] for seg in rf["text"] if "fig" not in seg)
                # text slots carry item names and dates read from the bill; strip dates before counting
                text_only = re.sub(r"\d{4}-\d{2}-\d{2}", "", text_only)
                for ts in f.text_slots.values():
                    text_only = text_only.replace(ts, "")
                sc.unsupported_numbers += len(re.findall(r"\d", SLOT.sub("", text_only)))
        auditor.delete(s.id)
    return sc.report()
