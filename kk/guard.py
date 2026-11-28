"""Input guard: personal-data masking, injected-instruction removal, refusals, language.

Bill text is untrusted. Masking happens before anything is stored or sent to a model.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------- Verhoeff (Aadhaar check digit)
_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6], [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4], [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2], [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def verhoeff_valid(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if not digits:
        return False
    c = 0
    for i, n in enumerate(reversed(digits)):
        c = _D[c][_P[i % 8][n]]
    return c == 0


_AADHAAR_RE = re.compile(r"(?<!\d)([2-9]\d{3})[\s-]?(\d{4})[\s-]?(\d{4})(?!\d)")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?|0)?([6-9]\d{4})[\s-]?(\d{5})(?!\d)")
_LABELLED_RE = re.compile(
    r"(?i)\b(UHID|IP\s*No\.?|MRN|Patient\s*Name|Name\s*of\s*Patient|Policy\s*No\.?|"
    r"Card\s*No\.?|PMJAY\s*ID|ABHA\s*(?:No\.?|Number|Address)?)\s*[:\-]?\s*([^\n|]{1,40})"
)


def mask_pii(text: str) -> tuple[str, list[str]]:
    """Mask Aadhaar (only when the Verhoeff check passes), phone numbers and labelled IDs.

    Returns the masked text and the kinds of data that were masked.
    """
    kinds: list[str] = []

    def _aad(m: re.Match) -> str:
        num = "".join(m.groups())
        if verhoeff_valid(num):
            kinds.append("aadhaar")
            return "XXXX XXXX " + num[-4:]
        return m.group(0)

    text = _AADHAAR_RE.sub(_aad, text)

    def _ph(m: re.Match) -> str:
        kinds.append("phone")
        return "XXXXXX" + m.group(2)[-4:]

    text = _PHONE_RE.sub(_ph, text)

    def _lab(m: re.Match) -> str:
        kinds.append(m.group(1).lower())
        return f"{m.group(1)}: [masked]"

    text = _LABELLED_RE.sub(_lab, text)
    return text, kinds


# ---------------------------------------------------------------- injected instructions
_INJECTION_RE = re.compile(
    r"(?i)(ignore|disregard|forget)\s+(all\s+|any\s+)?(previous|prior|above|earlier)\s+"
    r"(instructions?|prompts?|rules?)|system\s*prompt|you\s+are\s+now|act\s+as\s+|"
    r"do\s+not\s+flag|mark\s+(this|all)\s+(as\s+)?(ok|green|valid)|assistant\s*:"
)


def is_injection(text: str) -> bool:
    return bool(_INJECTION_RE.search(text or ""))


# ---------------------------------------------------------------- refusals
_MEDICAL = re.compile(
    r"(?i)\b(diagnos\w*|dose|dosage|should\s+i\s+take|which\s+medicine|was\s+(the|this)\s+"
    r"(surgery|operation|stent|test|treatment)\s+(needed|necessary|required)|unnecessary\s+"
    r"(surgery|stent|test)s?|side\s+effects?)\b"
)
_LEGAL = re.compile(
    r"(?i)\b(should\s+i\s+sue|will\s+i\s+win|file\s+(the\s+)?case\s+for\s+me|legal\s+advice|"
    r"represent\s+me|my\s+lawyer)\b"
)


def refusal_kind(text: str) -> str | None:
    """Returns 'medical', 'legal' or None. Price and entitlement questions are never refused."""
    if _MEDICAL.search(text or ""):
        return "medical"
    if _LEGAL.search(text or ""):
        return "legal"
    return None


# ---------------------------------------------------------------- language by script
_SCRIPTS = {
    "hi": (0x0900, 0x097F),   # Devanagari
    "gu": (0x0A80, 0x0AFF),   # Gujarati
    "kn": (0x0C80, 0x0CFF),   # Kannada
    "ta": (0x0B80, 0x0BFF),   # Tamil
    "te": (0x0C00, 0x0C7F),   # Telugu
}


def detect_language(text: str, default: str = "en") -> str:
    counts = {k: 0 for k in _SCRIPTS}
    for ch in text or "":
        o = ord(ch)
        for k, (lo, hi) in _SCRIPTS.items():
            if lo <= o <= hi:
                counts[k] += 1
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else default
