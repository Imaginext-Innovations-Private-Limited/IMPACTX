"""Turn positioned words into rows and columns."""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field

from ..models import Word
from ..money import parse_amount

HEADER_KEYS = {
    "description": ["description", "particulars", "item", "service", "details", "name of"],
    "date": ["date"],
    "batch": ["batch", "lot"],
    "expiry": ["exp", "expiry"],
    "qty": ["qty", "quantity", "units", "nos", "no."],
    "rate": ["rate", "unit price", "price", "unit rate", "cost"],
    "mrp": ["mrp"],
    "gst_rate": ["gst%", "gst %", "tax%", "tax %"],
    "gst_amount": ["gst amt", "gst amount", "tax amt", "tax amount"],
    "amount": ["amount", "total", "value", "net amt", "net amount"],
}

SECTION_WORDS = {
    "pharmacy": ["pharmacy", "medicine", "medicines", "drugs", "drug"],
    "consumables": ["consumable", "consumables", "surgical", "disposables"],
    "implant": ["implant", "implants", "stent", "stents", "prosthesis", "cath lab items"],
    "room": ["room", "bed", "ward", "icu", "iccu", "accommodation"],
    "diagnostics": ["investigation", "investigations", "laboratory", "lab", "radiology", "pathology"],
    "procedure": ["procedure", "procedures", "surgery", "operation", "ot charges", "cath lab"],
    "professional": ["doctor", "consultation", "professional", "visit", "surgeon"],
    "package": ["package"],
}

TOTAL_RE = re.compile(r"(?i)^(grand\s+total|net\s+(amount|payable)|total\s+(amount|bill)|bill\s+amount|"
                      r"amount\s+payable|sub[\s\-]*total|total)\b")
# payment and adjustment rows are not charges: never turn them into bill lines
PAYMENT_RE = re.compile(r"(?i)^(less\W*)?(advance|deposit|amount\s+(paid|received)|paid\s+by|received|"
                        r"balance|refund|discount|round(ed)?\s*off|payment)\b")
# phone-photo OCR often runs words together ("Less:AdvancePaid", "DrugElutingStent"); split a long
# word where the case changes, so word-boundary patterns (payments, stents, brands) still match.
_GLUED = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=[a-z]{3})(?=\d)")


def unglue(text: str) -> str:
    """'DrugElutingStent(Everolimus)3.0x28' -> 'Drug Eluting Stent(Everolimus)3.0x28'.
    Words shorter than eight letters (brand names such as BioMime) are left alone."""
    return " ".join(_GLUED.sub(" ", w) if len(w) >= 8 else w for w in text.split(" "))


DATE_RE = re.compile(r"^\d{1,2}[/.\-](\d{1,2}|[A-Za-z]{3})[/.\-]\d{2,4}$")
BATCH_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9\-/]{4,}$")


@dataclass
class Row:
    words: list[Word]

    @property
    def y(self) -> float:
        return statistics.mean((w.bbox.y0 + w.bbox.y1) / 2 for w in self.words)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def page(self) -> int:
        return self.words[0].bbox.page


@dataclass
class Columns:
    anchors: dict[str, float] = field(default_factory=dict)   # column name -> x centre
    header_row: int | None = None


def group_rows(words: list[Word]) -> list[Row]:
    rows: list[Row] = []
    for page in sorted({w.bbox.page for w in words}):
        pw = sorted((w for w in words if w.bbox.page == page), key=lambda w: (w.bbox.y0 + w.bbox.y1) / 2)
        if not pw:
            continue
        hs = [w.bbox.y1 - w.bbox.y0 for w in pw]
        tol = 0.6 * statistics.median(hs)
        current: list[Word] = []
        cy = None
        for w in pw:
            yc = (w.bbox.y0 + w.bbox.y1) / 2
            if cy is None or abs(yc - cy) <= tol:
                current.append(w)
                cy = statistics.mean((x.bbox.y0 + x.bbox.y1) / 2 for x in current)
            else:
                rows.append(Row(sorted(current, key=lambda x: x.bbox.x0)))
                current, cy = [w], yc
        if current:
            rows.append(Row(sorted(current, key=lambda x: x.bbox.x0)))
    return rows


def _match_header(text: str) -> str | None:
    t = text.lower().strip(" :.")
    for key in ("mrp", "gst_rate", "gst_amount", "batch", "expiry", "qty", "rate", "amount", "date",
                "description"):
        for needle in HEADER_KEYS[key]:
            if t == needle or t.startswith(needle):
                return key
    return None


def find_columns(rows: list[Row]) -> Columns:
    """Find the header row: the first row naming at least three column types including an amount."""
    for i, row in enumerate(rows):
        found: dict[str, list[float]] = {}
        ws = row.words
        j = 0
        while j < len(ws):
            # try two-word header phrases first ("Unit Price", "Net Amount", "GST Amt")
            two = f"{ws[j].text} {ws[j + 1].text}" if j + 1 < len(ws) else None
            key = _match_header(two) if two else None
            if key and _match_header(ws[j].text) != key:
                xc = (ws[j].bbox.x0 + ws[j + 1].bbox.x1) / 2
                found.setdefault(key, []).append(xc)
                j += 2
                continue
            key = _match_header(ws[j].text)
            if key:
                found.setdefault(key, []).append((ws[j].bbox.x0 + ws[j].bbox.x1) / 2)
            j += 1
        if "amount" in found and len(found) >= 3:
            anchors = {k: v[0] for k, v in found.items()}
            # when "total" and "amount" both appear, the right-most amount-like column is the amount
            anchors["amount"] = max(found["amount"])
            return Columns(anchors=anchors, header_row=i)
    return Columns()


def section_of(text: str) -> str | None:
    t = text.lower().strip(" :-")
    if not t or any(parse_amount(w) is not None for w in t.split()):
        return None
    for sec, words in SECTION_WORDS.items():
        if any(t == w or t.startswith(w + " ") or t.endswith(" " + w) or t == w + "s" for w in words):
            return sec
    raw = text.strip(" :-")
    # an unknown heading printed in capitals (e.g. PHYSIOTHERAPY) starts a new section
    if raw.isupper() and len(raw.split()) <= 4 and re.search(r"[A-Z]{3}", raw):
        return "other"
    return None


def classify_tokens(row: Row, cols: Columns) -> dict:
    """Assign each word in a data row to a column."""
    out: dict = {"description": [], "numbers": {}, "batch": None, "expiry": None, "date": None}
    num_cols = {k: x for k, x in cols.anchors.items()
                if k in ("qty", "rate", "mrp", "gst_rate", "gst_amount", "amount")}
    first_num_x = min(num_cols.values()) if num_cols else float("inf")
    for w in row.words:
        xc = (w.bbox.x0 + w.bbox.x1) / 2
        t = w.text.strip()
        amount = parse_amount(t.rstrip("%"))
        if DATE_RE.match(t):
            key = "expiry" if ("expiry" in cols.anchors and
                               abs(xc - cols.anchors["expiry"]) < abs(xc - cols.anchors.get("date", 1e9))) else "date"
            out[key] = (t, w)
            continue
        if amount is not None and num_cols and xc > first_num_x - 0.5 * _col_gap(num_cols):
            nearest = min(num_cols, key=lambda k: abs(num_cols[k] - xc))
            out["numbers"].setdefault(nearest, []).append(w)
            continue
        if "batch" in cols.anchors and BATCH_RE.match(t) and abs(xc - cols.anchors["batch"]) < 80:
            out["batch"] = (t, w)
            continue
        out["description"].append(w)
    return out


def _col_gap(num_cols: dict[str, float]) -> float:
    xs = sorted(num_cols.values())
    if len(xs) < 2:
        return 80.0
    return min(b - a for a, b in zip(xs, xs[1:]))
