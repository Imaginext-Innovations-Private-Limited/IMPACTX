"""Slot verifier for any free text written by a language model.

The model may only refer to numbers through role-typed slots such as [excess:F31].
Any digit (in any script), magnitude word or bare currency sign outside a slot is
rejected, as is a slot whose figure does not exist, has a different role, or was not
offered to the model.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from ..models import Figure
from .render import fmt_figure

SLOT = re.compile(r"\[([a-z_]+):(F\d+)\]")

# magnitude and quantity words per language ('one' is left out: it is also an article)
NUMBER_WORDS = {
    "en": r"\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|"
          r"sixty|seventy|eighty|ninety|hundred|thousand|lakh|lakhs|lac|crore|crores|million|billion|"
          r"half|double|twice)\b",
    "hi": r"(?<![\u0900-\u097F])(दो|तीन|चार|पाँच|पांच|छह|सात|आठ|नौ|दस|बीस|पचास|सौ|हज़ार|हजार|लाख|करोड़)(?![\u0900-\u097F])",
    "kn": r"(?<![\u0C80-\u0CFF])(ಎರಡು|ಮೂರು|ನಾಲ್ಕು|ಐದು|ಆರು|ಏಳು|ಎಂಟು|ಒಂಬತ್ತು|ಹತ್ತು|ಇಪ್ಪತ್ತು|ಐವತ್ತು|ನೂರು|ಸಾವಿರ|ಲಕ್ಷ|ಕೋಟಿ)(?![\u0C80-\u0CFF])",
    "ta": r"(?<![\u0B80-\u0BFF])(இரண்டு|மூன்று|நான்கு|ஐந்து|ஆறு|ஏழு|எட்டு|ஒன்பது|பத்து|இருபது|ஐம்பது|நூறு|ஆயிரம்|லட்சம்|கோடி)(?![\u0B80-\u0BFF])",
    "te": r"(?<![\u0C00-\u0C7F])(రెండు|మూడు|నాలుగు|ఐదు|ఆరు|ఏడు|ఎనిమిది|తొమ్మిది|పది|ఇరవై|యాభై|వంద|వెయ్యి|వేలు|లక్ష|లక్షలు|కోటి)(?![\u0C00-\u0C7F])",
    "gu": r"(?<![\u0A80-\u0AFF])(બે|ત્રણ|ચાર|પાંચ|છ|સાત|આઠ|નવ|દસ|વીસ|પચાસ|સો|હજાર|લાખ|કરોડ)(?![\u0A80-\u0AFF])",
}
CURRENCY = re.compile(r"₹|\bRs\.?\b|\bINR\b|रुपये|रुपए|ರೂಪಾಯಿ|રૂપિયા|ரூபாய்|రూపాయ", re.IGNORECASE)


@dataclass
class VerifyResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    used: list[str] = field(default_factory=list)


def verify(text: str, offered: dict[str, Figure], lang: str = "en",
           required: list[str] | None = None) -> VerifyResult:
    errors: list[str] = []
    used: list[str] = []
    for m in SLOT.finditer(text):
        role, fid = m.group(1), m.group(2)
        if fid not in offered:
            errors.append(f"slot {fid} was not offered")
            continue
        if offered[fid].role.value != role:
            errors.append(f"slot {fid} has role {offered[fid].role.value}, text used it as {role}")
        used.append(fid)
    bare = SLOT.sub(" ", text)
    for ch in bare:
        if unicodedata.category(ch) == "Nd":
            errors.append(f"digit outside a slot: {ch!r}")
            break
    pat = NUMBER_WORDS.get(lang)
    if pat and re.search(pat, bare, re.IGNORECASE):
        errors.append("number word outside a slot")
    if lang != "en" and re.search(NUMBER_WORDS["en"], bare, re.IGNORECASE):
        errors.append("number word outside a slot")
    if CURRENCY.search(bare):
        errors.append("currency sign or word outside a slot")
    for fid in required or []:
        if fid not in used:
            errors.append(f"required figure {fid} not mentioned")
    return VerifyResult(ok=not errors, errors=errors, used=used)


def fill(text: str, figs: dict[str, Figure]) -> list[dict]:
    """Turn verified text with slots into display segments."""
    out, pos = [], 0
    for m in SLOT.finditer(text):
        if m.start() > pos:
            out.append({"t": text[pos:m.start()]})
        fid = m.group(2)
        out.append({"fig": fid, "t": fmt_figure(figs[fid])})
        pos = m.end()
    if pos < len(text):
        out.append({"t": text[pos:]})
    return out
