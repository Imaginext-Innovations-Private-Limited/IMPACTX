"""Build a structured Bill from positioned words.

Every number becomes a Figure that points back to the exact OCR word ids and box.
"""

from __future__ import annotations

import re
from decimal import Decimal

from ..dates import find_labelled_date, parse_date
from ..figures import FigureStore
from ..guard import is_injection, mask_pii
from ..models import BBox, Bill, BillHeader, BillLine, Role, Word
from ..money import parse_amount
from .table import PAYMENT_RE, TOTAL_RE, unglue, Columns, Row, classify_tokens, find_columns, group_rows, section_of

GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")
SCHEME_RE = re.compile(r"(?i)\b(PM-?JAY|Ayushman|AB-?ArK|Arogya\s+Karnataka|Vay\s+Vandana|MA-?PMJAY|"
                       r"pre-?auth(?:orisation|orization)?\s*(?:no|number|id)?|TMS\s*(?:id|no)|CGHS)\b")
INTERIM_RE = re.compile(r"(?i)\b(interim|provisional|running)\s+bill\b")
FINAL_RE = re.compile(r"(?i)\b(final|discharge)\s+bill\b")


def _union(words: list[Word]) -> BBox | None:
    if not words:
        return None
    return BBox(page=words[0].bbox.page, x0=min(w.bbox.x0 for w in words), y0=min(w.bbox.y0 for w in words),
                x1=max(w.bbox.x1 for w in words), y1=max(w.bbox.y1 for w in words))


def _num_figure(figs: FigureStore, words: list[Word], role: Role, unit: str) -> str | None:
    text = "".join(w.text for w in words).replace("%", "")
    val = parse_amount(text)
    if val is None:
        return None
    conf = min(w.conf for w in words)
    return figs.from_bill(val, unit, role, [w.id for w in words], _union(words), conf)


def _mask_rows(rows: list[Row]) -> list[Row]:
    out = []
    for r in rows:
        _, kinds = mask_pii(r.text)
        if kinds:
            masked = [r.words[0]] + [w.model_copy(update={"text": "[masked]"}) for w in r.words[1:]]
            out.append(Row(masked))
        else:
            out.append(r)
    return out


def _header(rows: list[Row], figs: FigureStore) -> BillHeader:
    text = "\n".join(r.text for r in rows)
    h = BillHeader()
    m = GSTIN_RE.search(text)
    h.gstin = m.group(0) if m else None
    h.admission_date = find_labelled_date(text, ["date of admission", "admission", "doa", "admitted", "adm"])
    h.discharge_date = find_labelled_date(text, ["date of discharge", "discharge", "dod", "discharged", "dis"])
    if INTERIM_RE.search(text):
        h.bill_type = "interim"
    elif FINAL_RE.search(text):
        h.bill_type = "final"
    h.scheme_markers = sorted({m.group(1) for m in SCHEME_RE.finditer(text)})
    first_page = [r for r in rows if r.page == 1]
    for r in first_page[:6]:
        t = r.text.strip()
        if len(t.split()) >= 2 and not re.search(r"(?i)(bill|invoice|gstin|phone|tel|date|patient)", t):
            if re.search(r"(?i)(hospital|clinic|nursing|medical|health|institute|centre|center)", t):
                h.hospital_name = t
                break
    return h


def build_bill(words: list[Word], pages: int, figs: FigureStore, bill_id: str,
               source_files: list[str] | None = None) -> Bill:
    bill = Bill(id=bill_id, pages=pages, words=words, source_files=source_files or [])
    rows = group_rows(words)
    clean = []
    for r in rows:
        if is_injection(r.text):
            bill.warnings.append("removed_injected_text")
            continue
        clean.append(r)
    # header facts (dates, GSTIN, scheme markers) are read before masking; no personal data is kept
    bill.header = _header(clean, figs)
    rows = _mask_rows(clean)
    cols = find_columns(rows)
    start = (cols.header_row + 1) if cols.header_row is not None else 0
    section: str | None = None
    lines: list[BillLine] = []
    for idx, row in enumerate(rows[start:], start=start):
        text = unglue(row.text.strip())
        if not text:
            continue
        if TOTAL_RE.match(text):
            nums = [w for w in row.words if parse_amount(w.text) is not None]
            if nums and bill.header.total_fig is None and re.match(r"(?i)^(grand|net|total\s+(amount|bill)|amount\s+payable|bill\s+amount)", text):
                bill.header.total_fig = _num_figure(figs, [nums[-1]], Role.TOTAL, "INR")
            continue
        if PAYMENT_RE.match(text):
            continue
        sec = section_of(text)
        if sec:
            section = sec
            continue
        line = _line_from_row(row, cols, figs, f"L{len(lines) + 1}", section)
        if line is None:
            # a wrapped description continues the previous line
            if lines and not SERIAL.match(text) and not any(parse_amount(w.text) is not None for w in row.words) and \
                    lines[-1].bbox and abs(row.words[0].bbox.x0 - lines[-1].bbox.x0) < 40:
                lines[-1].description += " " + text
                lines[-1].word_ids += [w.id for w in row.words]
            continue
        line.description = unglue(line.description)
        lines.append(line)
    bill.lines = lines
    bill.itemised = _is_itemised(lines, figs)
    return bill


SERIAL = re.compile(r"^\s*(\d{1,3}|\d?[SIl]\d?)\s*[.,)]\s+")   # "4. Room rent" starts a new item; a handwritten 5 or 1 may read as S, I or l


def _line_from_row(row: Row, cols: Columns, figs: FigureStore, lid: str, section: str | None) -> BillLine | None:
    if cols.anchors:
        parts = classify_tokens(row, cols)
        nums = parts["numbers"]
        desc = SERIAL.sub("", " ".join(w.text for w in parts["description"]).strip())
        if "amount" not in nums:
            # a numbered row whose amount could not be read: keep it and ask, never drop it
            desc = " ".join(t for t in desc.split() if re.search(r"[A-Za-z]", t))   # drop unreadable scraps
            if desc and SERIAL.match(row.text.strip()) and len(desc) > 3:
                line = BillLine(id=lid, section=section, description=desc,
                                word_ids=[w.id for w in row.words], bbox=_union(row.words))
                line.flags += ["low_ocr_confidence", "amount_unreadable"]
                if "qty" in nums:
                    line.qty_fig = _num_figure(figs, nums["qty"], Role.QUANTITY, "count")
                if "rate" in nums:
                    line.rate_fig = _num_figure(figs, nums["rate"], Role.UNIT_RATE, "INR")
                return line
            return None
        if not desc:
            return None
        line = BillLine(id=lid, section=section, description=desc,
                        word_ids=[w.id for w in row.words], bbox=_union(row.words))
        line.amount_fig = _num_figure(figs, nums["amount"], Role.BILLED_AMOUNT, "INR")
        if "qty" in nums:
            line.qty_fig = _num_figure(figs, nums["qty"], Role.QUANTITY, "count")
        if "rate" in nums:
            line.rate_fig = _num_figure(figs, nums["rate"], Role.UNIT_RATE, "INR")
        if "mrp" in nums:
            line.mrp_fig = _num_figure(figs, nums["mrp"], Role.MRP, "INR")
        if "gst_rate" in nums:
            line.gst_rate_fig = _num_figure(figs, nums["gst_rate"], Role.GST_RATE, "percent")
        if "gst_amount" in nums:
            line.gst_amount_fig = _num_figure(figs, nums["gst_amount"], Role.GST_AMOUNT, "INR")
        if parts["batch"]:
            line.batch = parts["batch"][0]
        if parts["expiry"]:
            line.expiry = parts["expiry"][0]
        if parts["date"]:
            line.item_date = parse_date(parts["date"][0])
        return line
    # no header found: description followed by 1-3 trailing numbers
    ws = row.words
    trailing: list[Word] = []
    for w in reversed(ws):
        if parse_amount(w.text) is not None:
            trailing.insert(0, w)
        else:
            break
    if not trailing or len(trailing) == len(ws):
        return None
    desc = " ".join(w.text for w in ws[: len(ws) - len(trailing)])
    line = BillLine(id=lid, section=section, description=desc, word_ids=[w.id for w in ws], bbox=_union(ws))
    line.amount_fig = _num_figure(figs, [trailing[-1]], Role.BILLED_AMOUNT, "INR")
    if len(trailing) >= 3:
        line.qty_fig = _num_figure(figs, [trailing[-3]], Role.QUANTITY, "count")
        line.rate_fig = _num_figure(figs, [trailing[-2]], Role.UNIT_RATE, "INR")
    elif len(trailing) == 2:
        line.flags.append("ambiguous_columns")
    return line


def _is_itemised(lines: list[BillLine], figs: FigureStore) -> bool:
    """A bill is treated as not itemised when it has no lines, a single line without quantity
    and rate, or one 'package' line carrying most of the amount."""
    if not lines:
        return False
    if len(lines) == 1 and (lines[0].qty_fig is None or lines[0].rate_fig is None):
        return False
    amounts = [figs.value(l.amount_fig) or Decimal(0) for l in lines]
    total = sum(amounts)
    for l, a in zip(lines, amounts):
        if ("package" in l.description.lower() or l.section == "package") and total and a / total > Decimal("0.8"):
            return False
    return True
