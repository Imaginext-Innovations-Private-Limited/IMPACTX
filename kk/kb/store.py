"""Knowledge base: official reference tables and the rule registry.

Loading is strict. A row without a known source, a source reference or a valid
date range is refused, so no unsourced number can enter the system.
"""

from __future__ import annotations

import csv
import hashlib
import os
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

import yaml

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

REQUIRED = ("row_id", "valid_from", "valid_to", "source_id", "source_ref")


class DataError(ValueError):
    pass


def _parse_date(s: str, where: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError as e:
        raise DataError(f"{where}: bad date {s!r}") from e


@dataclass
class Row:
    table: str
    data: dict
    valid_from: date
    valid_to: date | None

    @property
    def id(self) -> str:
        return self.data["row_id"]

    def dec(self, key: str) -> Decimal:
        return Decimal(self.data[key])

    def valid_on(self, d: date) -> bool:
        return self.valid_from <= d and (self.valid_to is None or d <= self.valid_to)


@dataclass
class Rule:
    id: str
    family: str
    check: str
    status: str
    verdict: str
    channel: str
    sources: list[str]
    message: str
    needs: list[str] = field(default_factory=list)


class KnowledgeBase:
    def __init__(self, data_dir: str | os.PathLike | None = None) -> None:
        self.dir = Path(data_dir or os.environ.get("KK_DATA_DIR") or DEFAULT_DATA_DIR)
        self.sources: dict = yaml.safe_load((self.dir / "sources.yaml").read_text(encoding="utf-8"))
        self.tables: dict[str, list[Row]] = {}
        self.versions: dict[str, str] = {}
        ref = self.dir / "reference"
        for name, numeric in [
            ("stent_ceilings", ["ceiling_ex_gst"]),
            ("knee_implant_ceilings", ["ceiling_ex_gst"]),
            ("gst_rates", ["rate_percent"]),
            ("nppa_scheduled_ceilings", ["ceiling_ex_gst"]),
            ("hbp_packages", ["nrp", "tier3_rate", "tier2_rate", "tier1_rate"]),
            ("empanelled_hospitals", []),
            ("cghs_rates", ["rate"]),
            ("stent_brands", []),
            ("gst_health", ["value"]),
            ("irdai_lists", []),
        ]:
            self.tables[name] = self._load_table(ref / f"{name}.csv", name, numeric)
        self.aliases = self._load_aliases(ref / "aliases.csv")
        rules_raw = yaml.safe_load((self.dir / "rules.yaml").read_text(encoding="utf-8"))["rules"]
        self.rules = [Rule(**{**{"needs": []}, **r}) for r in rules_raw]
        for r in self.rules:
            for s in r.sources:
                if s not in self.sources:
                    raise DataError(f"rule {r.id} cites unknown source {s}")
        self.versions["rules.yaml"] = _sha((self.dir / "rules.yaml").read_bytes())

    # ------------------------------------------------------------ loading
    def _load_table(self, path: Path, name: str, numeric: Iterable[str]) -> list[Row]:
        raw = path.read_bytes()
        self.versions[path.name] = _sha(raw)
        rows: list[Row] = []
        seen: set[str] = set()
        with path.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
            if missing:
                raise DataError(f"{path.name}: missing columns {missing}")
            for i, rec in enumerate(reader, start=2):
                where = f"{path.name} line {i}"
                rid = (rec.get("row_id") or "").strip()
                if not rid:
                    raise DataError(f"{where}: empty row_id")
                if rid in seen:
                    raise DataError(f"{where}: duplicate row_id {rid}")
                seen.add(rid)
                if rec["source_id"] not in self.sources:
                    raise DataError(f"{where}: unknown source_id {rec['source_id']!r}")
                if not (rec.get("source_ref") or "").strip():
                    raise DataError(f"{where}: source_ref is required")
                vf = _parse_date(rec["valid_from"], where)
                if vf is None:
                    raise DataError(f"{where}: valid_from is required")
                vt = _parse_date(rec["valid_to"], where)
                if vt is not None and vt < vf:
                    raise DataError(f"{where}: valid_to before valid_from")
                for col in numeric:
                    val = (rec.get(col) or "").strip()
                    if val:
                        try:
                            Decimal(val)
                        except InvalidOperation as e:
                            raise DataError(f"{where}: {col} is not a number: {val!r}") from e
                rows.append(Row(name, rec, vf, vt))
        return rows

    def _load_aliases(self, path: Path) -> list[dict]:
        self.versions[path.name] = _sha(path.read_bytes())
        with path.open(encoding="utf-8", newline="") as fh:
            return [r for r in csv.DictReader(fh)]

    # ------------------------------------------------------------ queries
    def valid(self, table: str, on: date, **match) -> list[Row]:
        out = []
        for r in self.tables[table]:
            if not r.valid_on(on):
                continue
            if all(r.data.get(k) == v for k, v in match.items()):
                out.append(r)
        return out

    def gst_rate(self, category: str, on: date) -> Row | None:
        rows = self.valid("gst_rates", on, category=category)
        return rows[0] if rows else None

    def gst_health(self, item: str, on: date) -> Row | None:
        rows = self.valid("gst_health", on, item=item)
        return rows[0] if rows else None

    def stent_ceiling(self, category: str, on: date) -> Row | None:
        rows = self.valid("stent_ceilings", on, category=category)
        return rows[0] if rows else None

    def stent_brand(self, desc: str) -> tuple[Row, str] | None:
        """Longest stent brand alias found in a line description, from hospital-published lists."""
        import re as _re
        d = " " + _re.sub(r"[^a-z0-9]+", " ", desc.lower()) + " "
        best = None
        for r in self.tables.get("stent_brands", []):
            for a in r.data["aliases"].split("|"):
                a = a.strip()
                if a and f" {a} " in d and (best is None or len(a) > len(best[1])):
                    best = (r, a)
        return best

    def source_field(self, sid: str, key: str):
        return self.sources.get(sid, {}).get(key)

    def knee_rows(self, on: date) -> list[Row]:
        return self.valid("knee_implant_ceilings", on)

    def scheduled_rows(self, on: date) -> list[Row]:
        return self.valid("nppa_scheduled_ceilings", on)

    def hospital_status(self, name_or_id: str, on: date) -> Row | None:
        key = _norm(name_or_id)
        for r in self.tables["empanelled_hospitals"]:
            if not r.valid_on(on):
                continue
            if key in (_norm(r.data.get("hospital_name", "")), _norm(r.data.get("hfr_id", "")),
                       _norm(r.data.get("gstin", ""))):
                return r
        return None

    # Tables each rule needs before it can give a verdict, and tables it can use if loaded.
    RULE_TABLES = {
        "PRC-STENT": (["stent_ceilings", "gst_rates"], ["stent_brands"]),
        "PRC-KNEE": (["knee_implant_ceilings", "gst_rates"], []),
        "PRC-SCHED": (["nppa_scheduled_ceilings", "gst_rates"], []),
        "ENT-COVERED": ([], ["empanelled_hospitals"]),
        "ENT-CASH-DENIAL": ([], ["empanelled_hospitals"]),
        "TAX-GST": (["gst_health"], []),
    }

    def readiness(self) -> dict:
        """Which rules can run with the data loaded now, and which staged files await review."""
        rules = []
        for r in self.rules:
            need, can_use = self.RULE_TABLES.get(r.id, ([], []))
            missing = [t for t in need if not self.has_data(t)]
            rules.append({"rule": r.id, "legal_status": r.status, "ready": not missing and r.status != "on_hold",
                          "needs": {t: len(self.tables.get(t, [])) for t in need},
                          "missing": missing,
                          "optional": {t: len(self.tables.get(t, [])) for t in can_use}})
        staged = sorted(p.name for p in (self.dir / "staged").glob("*.csv")) if (self.dir / "staged").exists() else []
        return {"rules": rules, "ready": sum(x["ready"] for x in rules), "total": len(rules),
                "staged_awaiting_review": staged}

    def has_data(self, table: str) -> bool:
        return bool(self.tables.get(table))

    def rule(self, rule_id: str) -> Rule:
        for r in self.rules:
            if r.id == rule_id:
                return r
        raise KeyError(rule_id)

    def basis(self, source_ids) -> list[dict]:
        """Official wording a finding rests on: sources that carry a rule_quote."""
        out = []
        for sid in source_ids or []:
            src = self.sources.get(sid, {})
            if src.get("rule_quote"):
                out.append({"source_id": sid, "title": src.get("title", sid), "ref": src.get("rule_ref"),
                            "quote": " ".join(str(src["rule_quote"]).split()), "url": self.source_url(sid)})
        return out

    def source_title(self, sid: str) -> str:
        return self.sources.get(sid, {}).get("title", sid)

    def source_url(self, sid: str) -> str | None:
        urls = self.sources.get(sid, {}).get("urls") or []
        return urls[0] if urls else None


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def _norm(s: str) -> str:
    return " ".join((s or "").lower().replace(".", " ").replace(",", " ").split())
