"""The figure store: every number the system knows, with its role and evidence.

Nothing reaches the user unless it is a Figure in this store.
"""

from __future__ import annotations

from decimal import Decimal

from .models import BBox, Evidence, Figure, Origin, Role
from .money import D, q


class FigureStore:
    def __init__(self) -> None:
        self._figs: dict[str, Figure] = {}
        self._n = 0

    def _next_id(self) -> str:
        self._n += 1
        return f"F{self._n}"

    def add(self, value, unit: str, role: Role, origin: Origin, evidence: Evidence,
            confidence: float = 1.0, money: bool | None = None) -> str:
        v = D(value)
        if money or (money is None and unit == "INR"):
            v = q(v)
        fid = self._next_id()
        self._figs[fid] = Figure(id=fid, value=v, unit=unit, role=role, origin=origin,
                                 evidence=evidence, confidence=confidence)
        return fid

    def from_bill(self, value, unit: str, role: Role, token_ids: list[str],
                  bbox: BBox | None, confidence: float) -> str:
        return self.add(value, unit, role, Origin.BILL,
                        Evidence(bill_tokens=token_ids, bbox=bbox), confidence)

    def from_rule(self, value, unit: str, role: Role, row_id: str, source_id: str,
                  source_ref: str) -> str:
        return self.add(value, unit, role, Origin.RULE_DATA,
                        Evidence(rule_row=row_id, source_id=source_id, source_ref=source_ref))

    def computed(self, value, unit: str, role: Role, formula: str, inputs: list[str]) -> str:
        for i in inputs:
            if i not in self._figs:
                raise KeyError(f"computed figure uses unknown input {i}")
        return self.add(value, unit, role, Origin.COMPUTED, Evidence(formula=formula, inputs=inputs))

    def confirm(self, fid: str, new_value) -> str:
        """User correction: creates a new user-confirmed figure that replaces the old one."""
        old = self._figs[fid]
        nid = self.add(new_value, old.unit, old.role, Origin.USER,
                       Evidence(bill_tokens=old.evidence.bill_tokens, bbox=old.evidence.bbox,
                                note=f"corrected from {old.id}"))
        return nid

    def get(self, fid: str) -> Figure:
        return self._figs[fid]

    def value(self, fid: str | None) -> Decimal | None:
        if fid is None:
            return None
        return self._figs[fid].value

    def __contains__(self, fid: str) -> bool:
        return fid in self._figs

    def all(self) -> dict[str, Figure]:
        return dict(self._figs)
