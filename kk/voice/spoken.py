"""How a verified figure is said aloud.

The written caption keeps the exact display form (₹20,469.34). The spoken form is derived
from the same Decimal by fixed code, never by a model, so speech cannot change a number.
English uses Indian number words (lakh, crore). For Indian languages the integer is given
without separators next to the rupee word, which speech engines read as a native number.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from ..models import Figure

_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def _below_100(n: int) -> str:
    if n < 20:
        return _ONES[n]
    t, o = divmod(n, 10)
    return _TENS[t] + ("-" + _ONES[o] if o else "")


def _below_1000(n: int) -> str:
    h, r = divmod(n, 100)
    parts = []
    if h:
        parts.append(_ONES[h] + " hundred")
    if r:
        parts.append(("and " if h else "") + _below_100(r))
    return " ".join(parts) or "zero"


def english_words(n: int) -> str:
    """Indian-system English words: 111698 -> one lakh eleven thousand six hundred and ninety-eight."""
    if n == 0:
        return "zero"
    out = []
    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, n = divmod(n, 1000)
    if crore:
        out.append(english_words(crore) + " crore")
    if lakh:
        out.append(_below_100(lakh) + " lakh")
    if thousand:
        out.append(_below_100(thousand) + " thousand")
    if n:
        out.append(_below_1000(n))
    return " ".join(out)


RUPEE = {"en": ("rupees", "paise"), "hi": ("रुपये", "पैसे"), "kn": ("ರೂಪಾಯಿ", "ಪೈಸೆ"),
         "gu": ("રૂપિયા", "પૈસા"), "ta": ("ரூபாய்", "பைசா"), "te": ("రూపాయలు", "పైసలు")}
PERCENT_WORD = {"en": "percent", "hi": "प्रतिशत", "kn": "ಶೇಕಡಾ", "gu": "ટકા", "ta": "சதவீதம்", "te": "శాతం"}
AND = {"en": " and ", "hi": " ", "kn": " ", "gu": " ", "ta": " ", "te": " "}


def _split_rupees(v: Decimal) -> tuple[int, int]:
    v = v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    rupees = int(v)
    paise = int((v - rupees) * 100)
    return rupees, paise


def spoken_amount(v: Decimal, lang: str) -> str:
    rs_word, ps_word = RUPEE.get(lang, RUPEE["en"])
    rupees, paise = _split_rupees(v)
    if lang == "en":
        s = f"{english_words(rupees)} {'rupee' if rupees == 1 else rs_word}"
        if paise:
            s += f" and {english_words(paise)} paise"
        return s
    s = f"{rupees} {rs_word}"
    if paise:
        s += f"{AND.get(lang, ' ')}{paise} {ps_word}"
    return s


def _plain_number(v: Decimal, lang: str) -> str:
    v = v.normalize()
    if v == v.to_integral_value():
        n = int(v)
        return english_words(n) if lang == "en" else str(n)
    return f"{v:f}"


def spoken(f: Figure, lang: str) -> str:
    if f.unit == "INR":
        return spoken_amount(f.value, lang)
    if f.unit == "percent":   # templates write the % sign after the slot; speech says the word there
        return _plain_number(f.value, lang)
    return _plain_number(f.value, lang)
