"""Loader for inspectable JSON clinical rule tables."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

RULES_DIR: Path = Path(__file__).resolve().parents[2] / "rules"


@lru_cache(maxsize=8)
def load_rule_table(filename: str) -> dict[str, Any]:
    """Load and cache a JSON rule table from ``packages/clinical-engine/rules/``."""
    rule_path = RULES_DIR / filename
    if not rule_path.is_file():
        raise FileNotFoundError(f"Clinical rule table not found: {rule_path}")
    with rule_path.open("r", encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


def load_imnci_rules() -> dict[str, Any]:
    """Return the WHO IMNCI pediatric triage rule table."""
    return load_rule_table("imnci_pediatric.json")


def load_maternal_anc_rules() -> dict[str, Any]:
    """Return the NHM ASHA maternal ANC/PNC triage & checklist rule table."""
    return load_rule_table("maternal_anc.json")


def load_uip_vaccine_rules() -> dict[str, Any]:
    """Return the India UIP pediatric immunization schedule rule table."""
    return load_rule_table("uip_vaccines.json")
