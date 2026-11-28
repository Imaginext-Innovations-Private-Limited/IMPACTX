"""Date parsing for Indian bill formats (day first)."""

from __future__ import annotations

import re
from datetime import date, datetime

_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
            "%d-%b-%Y", "%d-%b-%y", "%d/%b/%Y", "%d %b %Y", "%d %B %Y", "%Y-%m-%d"]

DATE_TOKEN = r"(\d{1,2}[/.\-](?:\d{1,2}|[A-Za-z]{3})[/.\-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})"


def parse_date(text: str | None) -> date | None:
    if not text:
        return None
    t = text.strip().rstrip(",.")
    for f in _FORMATS:
        try:
            return datetime.strptime(t, f).date()
        except ValueError:
            continue
    return None


def find_labelled_date(text: str, labels: list[str]) -> date | None:
    pat = re.compile(r"(?i)(" + "|".join(labels) + r")\s*(?:date|on)?\s*[:\-]?\s*" + DATE_TOKEN)
    m = pat.search(text)
    return parse_date(m.group(2)) if m else None
