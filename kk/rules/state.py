"""State-specific rules. Rules on hold are shown as information only."""

from __future__ import annotations

from datetime import date

from ..kb import Rule
from ..models import Finding, Verdict
from .base import RC, make


def karnataka_disclosure(rc: RC, rule: Rule) -> list[Finding]:
    st = rc.ctx.state.value if rc.ctx.state.known else None
    d = rc.service_date
    if st not in ("karnataka", "ka") or d is None or d < date(2026, 11, 1):
        return []
    return [make(rule, Verdict.INFO, "state_ka", None)]
