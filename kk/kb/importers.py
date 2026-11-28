"""Importers for official PDFs and spreadsheets.

Importers never write to data/reference directly. They write to data/staged/,
and `python -m kk kb approve` moves rows into the live tables only after a
named reviewer confirms that each row was checked against the source PDF.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber

from .store import REQUIRED, DataError, KnowledgeBase

_NUM = re.compile(r"^\d[\d,]*(\.\d+)?$")


def _clean(cell) -> str:
    return " ".join(str(cell or "").split())


def _num(cell) -> str | None:
    t = _clean(cell).replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
    if not _NUM.match(t):
        return None
    try:
        return str(Decimal(t.replace(",", "")))
    except InvalidOperation:
        return None


def _find_cols(header: list[str], wanted: dict[str, list[str]]) -> dict[str, int]:
    cols = {}
    low = [h.lower() for h in header]
    for key, needles in wanted.items():
        for i, h in enumerate(low):
            if any(n in h for n in needles):
                cols[key] = i
                break
    return cols


def import_nppa_ceilings(pdf: Path, source_id: str, valid_from: str, valid_to: str,
                         out: Path) -> int:
    """Extract (formulation, dosage form & strength, unit, ceiling price) rows.

    Works with the column layout NPPA uses in its ceiling-price notifications:
    'Name of the Scheduled Formulation | Dosage form and strength | Unit | Ceiling Price'.
    """
    wanted = {
        "formulation": ["name of the scheduled formulation", "medicines", "formulation"],
        "dosage": ["dosage form", "strength"],
        "unit": ["unit"],
        "price": ["ceiling price"],
    }
    rows = []
    with pdfplumber.open(pdf) as doc:
        for pno, page in enumerate(doc.pages, start=1):
            for table in page.extract_tables():
                cols = None
                for rno, raw in enumerate(table, start=1):
                    cells = [_clean(c) for c in raw]
                    if cols is None:
                        c = _find_cols(cells, wanted)
                        if {"formulation", "price"} <= c.keys():
                            cols = c
                        continue
                    price = _num(cells[cols["price"]]) if cols["price"] < len(cells) else None
                    name = cells[cols["formulation"]] if cols["formulation"] < len(cells) else ""
                    if not price or not name:
                        continue
                    rows.append({
                        "row_id": f"NPPA-{pdf.stem[:20]}-{pno}-{rno}",
                        "formulation": name,
                        "dosage_form_strength": cells[cols["dosage"]] if "dosage" in cols else "",
                        "unit": cells[cols["unit"]] if "unit" in cols else "",
                        "ceiling_ex_gst": price,
                        "valid_from": valid_from,
                        "valid_to": valid_to,
                        "source_id": source_id,
                        "source_ref": f"{pdf.name} page {pno} table row {rno}",
                    })
    return _write_staged(out, rows)


def import_hbp(pdf: Path, source_id: str, valid_from: str, valid_to: str, out: Path) -> int:
    """Extract HBP 2022 package rows from a state copy of the package master."""
    wanted = {
        "specialty": ["specialty"],
        "package_code": ["package code", "package\ncode"],
        "procedure_code": ["procedure code", "procedure\ncode"],
        "procedure_name": ["procedure name"],
        "nrp": ["national reference", "nrp"],
        "tier3_rate": ["tier3", "tier 3"],
        "tier2_rate": ["tier2", "tier 2"],
        "tier1_rate": ["tier1", "tier 1"],
        "implant_mapped": ["implant mapped"],
        "implant_cost": ["implant cost"],
    }
    rows = []
    with pdfplumber.open(pdf) as doc:
        for pno, page in enumerate(doc.pages, start=1):
            for table in page.extract_tables():
                cols = None
                for rno, raw in enumerate(table, start=1):
                    cells = [_clean(c) for c in raw]
                    if cols is None:
                        c = _find_cols(cells, wanted)
                        if {"procedure_code", "procedure_name"} <= c.keys():
                            cols = c
                        continue
                    get = lambda k: cells[cols[k]] if k in cols and cols[k] < len(cells) else ""
                    code = get("procedure_code")
                    if not re.match(r"^[A-Z]{2}\d{3}[A-Z]?$", code):
                        continue
                    rows.append({
                        "row_id": f"HBP-{code}",
                        "specialty": get("specialty"),
                        "package_code": get("package_code"),
                        "procedure_code": code,
                        "procedure_name": get("procedure_name"),
                        "nrp": _num(get("nrp")) or "",
                        "tier3_rate": _num(get("tier3_rate")) or "",
                        "tier2_rate": _num(get("tier2_rate")) or "",
                        "tier1_rate": _num(get("tier1_rate")) or "",
                        "implant_mapped": get("implant_mapped"),
                        "implant_cost": get("implant_cost"),
                        "valid_from": valid_from,
                        "valid_to": valid_to,
                        "source_id": source_id,
                        "source_ref": f"{pdf.name} page {pno} table row {rno}",
                    })
    return _write_staged(out, rows)


def import_empanelment_csv(src: Path, source_id: str, status_from: str, out: Path,
                           status: str = "empanelled") -> int:
    """Convert an exported hospital list (CSV) into the empanelment table format."""
    rows = []
    with src.open(encoding="utf-8-sig", newline="") as fh:
        for i, rec in enumerate(csv.DictReader(fh), start=2):
            low = {k.lower().strip(): (v or "").strip() for k, v in rec.items() if k}
            name = low.get("hospital name") or low.get("hospital_name") or low.get("name")
            if not name:
                continue
            rows.append({
                "row_id": f"EMP-{src.stem[:16]}-{i}",
                "hospital_name": name,
                "state": low.get("state", ""),
                "district": low.get("district", ""),
                "address": low.get("address", ""),
                "hfr_id": low.get("hfr id", low.get("hfr_id", "")),
                "gstin": low.get("gstin", ""),
                "scheme": "pmjay",
                "status": status,
                "valid_from": status_from,
                "valid_to": "",
                "source_id": source_id,
                "source_ref": f"{src.name} line {i}",
            })
    return _write_staged(out, rows)


def _write_staged(out: Path, rows: list[dict]) -> int:
    if not rows:
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def approve(staged: Path, table: str, reviewer: str, kb: KnowledgeBase) -> int:
    """Append reviewed staged rows to a live table and log the review."""
    live = kb.dir / "reference" / f"{table}.csv"
    with live.open(encoding="utf-8", newline="") as fh:
        fields = csv.DictReader(fh).fieldnames or []
    with staged.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for c in REQUIRED:
            if not (r.get(c) or "").strip() and c != "valid_to":
                raise DataError(f"staged row {r.get('row_id')} lacks {c}")
        if r["source_id"] not in kb.sources:
            raise DataError(f"staged row {r['row_id']} cites unknown source {r['source_id']}")
    with live.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writerows(rows)
    log = kb.dir / "review_log.csv"
    new = not log.exists()
    with log.open("a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["timestamp", "reviewer", "table", "staged_file", "rows"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), reviewer, table, staged.name, len(rows)])
    KnowledgeBase(kb.dir)   # re-load to validate the result; raises DataError if broken
    return len(rows)
