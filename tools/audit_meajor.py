"""Audit the Zenodo MeAJOR email dataset (schema, labels, sources, duplicates)."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(10 * 1024 * 1024)

MEAJOR_CSV = Path(__file__).resolve().parent.parent / "data" / "external" / "meajor" / "meajor_cleaned_preprocessed.csv"
OUT_JSON = Path(__file__).resolve().parent.parent / "benchmark" / "meajor_audit.json"


def _norm_template(text: str) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip().lower())
    t = re.sub(r"\d+", "0", t)
    return t[:2000]


def main() -> None:
    total = 0
    labels = Counter()
    sources = Counter()
    source_label = defaultdict(Counter)
    seen_exact = set()
    seen_tmpl = set()
    exact_dups = 0
    tmpl_dups = 0
    sample_cols = None

    with open(MEAJOR_CSV, "r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        sample_cols = reader.fieldnames
        for row in reader:
            total += 1
            lbl = row.get("label", "")
            src = row.get("source") or row.get("dataset") or row.get("corpus") or "unknown"
            labels[lbl] += 1
            sources[src] += 1
            source_label[src][lbl] += 1

            subj = row.get("subject", "") or ""
            body = row.get("body", "") or row.get("text", "") or ""
            full = f"{subj}\n{body}".strip()
            h_exact = hashlib.sha256(full.encode("utf-8", errors="replace")).hexdigest()
            if h_exact in seen_exact:
                exact_dups += 1
            else:
                seen_exact.add(h_exact)

            h_tmpl = hashlib.sha256(_norm_template(full).encode("utf-8", errors="replace")).hexdigest()
            if h_tmpl in seen_tmpl:
                tmpl_dups += 1
            else:
                seen_tmpl.add(h_tmpl)

    report = {
        "file": str(MEAJOR_CSV.name),
        "md5": "aa8f59e96787cbd696c0b650e5400dc9",
        "license": "CC BY 4.0 (Zenodo 18471483)",
        "columns": sample_cols,
        "total_rows": total,
        "label_counts": dict(labels),
        "source_counts": dict(sources),
        "source_x_label": {k: dict(v) for k, v in source_label.items()},
        "exact_duplicates": exact_dups,
        "near_template_duplicates": tmpl_dups,
        "unique_templates": len(seen_tmpl),
    }
    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
