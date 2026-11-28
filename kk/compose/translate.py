"""Machine translation for languages beyond the four hand-written ones.

Slots are frozen before translation and must come back unchanged. Any translator can be
plugged in (for example Bhashini's pipeline API or a self-hosted IndicTrans2) by passing
a function str -> str. Findings in en/hi/kn/gu never use machine translation.
"""

from __future__ import annotations

import re
from typing import Callable

from .verifier import SLOT


class SlotsChanged(ValueError):
    pass


def freeze(text: str) -> tuple[str, list[str]]:
    slots: list[str] = []

    def _sub(m: re.Match) -> str:
        slots.append(m.group(0))
        return f"⟦{chr(0x41 + len(slots) - 1)}⟧"   # ⟦A⟧ ⟦B⟧ ... letters, never digits

    return SLOT.sub(_sub, text), slots


def thaw(text: str, slots: list[str]) -> str:
    found = re.findall(r"⟦([A-Z])⟧", text)
    expected = [chr(0x41 + i) for i in range(len(slots))]
    if sorted(found) != expected:
        raise SlotsChanged(f"translator changed slot markers: {found} vs {expected}")
    for i, s in enumerate(slots):
        text = text.replace(f"⟦{chr(0x41 + i)}⟧", s)
    return text


def translate(text: str, translator: Callable[[str], str]) -> str:
    frozen, slots = freeze(text)
    return thaw(translator(frozen), slots)
