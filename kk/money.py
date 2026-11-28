"""Exact money arithmetic.

All amounts are Decimal and rounded to paise only when stored or displayed.
Floats are never used for money.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

PAISE = Decimal("0.01")

_NUM_RE = re.compile(r"^[₹\s]*(?:Rs\.?|INR)?\s*([-+]?[\d,]*\.?\d+)\s*/?-?$", re.IGNORECASE)


def D(value) -> Decimal:
    """Convert int/str/Decimal to Decimal. Floats are rejected on purpose."""
    if isinstance(value, float):
        raise TypeError("Use str or Decimal for money, never float")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def q(value) -> Decimal:
    """Round to paise, half up (the usual billing convention)."""
    return D(value).quantize(PAISE, rounding=ROUND_HALF_UP)


def parse_amount(text: str) -> Decimal | None:
    """Parse a printed amount such as '1,41,145.33', 'Rs. 58,000/-' or '₹ 520'.

    Returns None when the text is not a single number.
    """
    if text is None:
        return None
    t = text.strip().replace("O", "0") if re.fullmatch(r"[\dO,.]+", text.strip() or "x") else text.strip()
    m = _NUM_RE.match(t)
    if not m:
        return None
    raw = m.group(1).replace(",", "")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def indian_grouping(value: Decimal, decimals: int = 2) -> str:
    """Format 141145.33 as '1,41,145.33' (Indian digit grouping)."""
    v = q(value) if decimals == 2 else D(value).quantize(Decimal(1))
    sign = "-" if v < 0 else ""
    v = abs(v)
    s = f"{v:.{decimals}f}"
    if "." in s:
        whole, frac = s.split(".")
    else:
        whole, frac = s, ""
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return sign + whole + (("." + frac) if frac else "")


def rupees(value: Decimal) -> str:
    return "₹" + indian_grouping(value)
