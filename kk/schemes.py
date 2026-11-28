"""What a government health scheme could have paid on a bill the family paid in cash.

This is awareness, not a claim. Nothing here is added to the amount a family can challenge.

  covered  = the bill lines a scheme package normally includes: inside the stay window
             (3 days before admission to 15 days after discharge), not room upgrades or
             personal items, not lines still waiting for the family to confirm them.
  saving   = smaller of covered and the scheme's cover     (family_year, one_time)
           = covered                                       (no_ceiling: CGHS, ESIC, ECHS, CAPF)
           = smaller of share x covered and the cap        (co_pay: Karnataka APL)

Every cover comes from data/schemes.yaml and cites a source in data/sources.yaml, so the
proof panel can show where each amount comes from.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import yaml

from .figures import FigureStore
from .models import Bill, Role
from .money import q
from .rules.base import billed_total
from .rules.entitlement import NON_MEDICAL, POST_DAYS, PRE_DAYS, UPGRADE

DATA = Path(__file__).resolve().parent.parent / "data" / "schemes.yaml"

# every state and union territory, in the order a family would look for it
STATES: list[tuple[str, str]] = [
    ("andhra_pradesh", "Andhra Pradesh"), ("arunachal_pradesh", "Arunachal Pradesh"), ("assam", "Assam"),
    ("bihar", "Bihar"), ("chhattisgarh", "Chhattisgarh"), ("goa", "Goa"), ("gujarat", "Gujarat"),
    ("haryana", "Haryana"), ("himachal_pradesh", "Himachal Pradesh"), ("jharkhand", "Jharkhand"),
    ("karnataka", "Karnataka"), ("kerala", "Kerala"), ("madhya_pradesh", "Madhya Pradesh"),
    ("maharashtra", "Maharashtra"), ("manipur", "Manipur"), ("meghalaya", "Meghalaya"), ("mizoram", "Mizoram"),
    ("nagaland", "Nagaland"), ("odisha", "Odisha"), ("punjab", "Punjab"), ("rajasthan", "Rajasthan"),
    ("sikkim", "Sikkim"), ("tamil_nadu", "Tamil Nadu"), ("telangana", "Telangana"), ("tripura", "Tripura"),
    ("uttar_pradesh", "Uttar Pradesh"), ("uttarakhand", "Uttarakhand"), ("west_bengal", "West Bengal"),
    ("andaman_nicobar", "Andaman and Nicobar Islands"), ("chandigarh", "Chandigarh"),
    ("dnh_dd", "Dadra and Nagar Haveli and Daman and Diu"), ("delhi", "Delhi"),
    ("jammu_kashmir", "Jammu and Kashmir"), ("ladakh", "Ladakh"), ("lakshadweep", "Lakshadweep"),
    ("puducherry", "Puducherry"),
]
STATE_NAMES = dict(STATES)
ALIASES = {"ka": "karnataka", "gj": "gujarat", "tn": "tamil_nadu", "mh": "maharashtra", "up": "uttar_pradesh",
           "wb": "west_bengal", "jk": "jammu_kashmir", "j&k": "jammu_kashmir", "nct of delhi": "delhi"}
SCHEME_PAYERS = {"pmjay", "state_scheme", "cghs"}


@lru_cache(maxsize=1)
def load(path: str | None = None) -> dict:
    return yaml.safe_load(Path(path or DATA).read_text(encoding="utf-8"))


def norm_state(state: str | None) -> str | None:
    if not state:
        return None
    s = state.strip().lower()
    s = ALIASES.get(s, s).replace(" ", "_").replace("-", "_")
    return s if s in STATE_NAMES else None


def applies(answers: dict) -> bool:
    """Shown when the family did not use a scheme card: cash, private insurance or not said."""
    return (answers or {}).get("payer") not in SCHEME_PAYERS


def covered_amount(bill: Bill, figs: FigureStore) -> tuple[str | None, str]:
    """Figure id of the package-covered amount (None if nothing counts) and a count of left-out lines."""
    from .extraction.validate import CONFIRM_FLAGS
    h = bill.header
    ids: list[str] = []
    left_out = 0
    from .extraction.table import PAYMENT_RE
    for line in bill.lines:
        if PAYMENT_RE.match(line.description.strip()):   # advances and discounts are not charges
            left_out += 1
            continue
        if not line.confirmed and any(f in line.flags for f in CONFIRM_FLAGS):
            left_out += 1
            continue
        if line.item_date and h.admission_date and h.discharge_date and not (
                h.admission_date - timedelta(days=PRE_DAYS) <= line.item_date
                <= h.discharge_date + timedelta(days=POST_DAYS)):
            left_out += 1
            continue
        if UPGRADE.search(line.description) or NON_MEDICAL.search(line.description):
            left_out += 1
            continue
        billed, inputs, formula = billed_total(line, figs)
        if billed is None or billed <= 0:
            left_out += 1
            continue
        ids.append(inputs[0] if len(inputs) == 1 else
                   figs.computed(billed, "INR", Role.BILLED_AMOUNT, formula, inputs))
    count = figs.computed(left_out, "count", Role.COUNT,
                          "lines left out: still to confirm, outside the stay window, upgrades or personal items", [])
    if not ids:
        return None, count
    total = q(sum((figs.value(i) for i in ids), Decimal(0)))
    cov = figs.computed(total, "INR", Role.COVERED,
                        "sum of the lines a scheme package normally includes", ids)
    return cov, count


def _scheme(row: dict, figs: FigureStore, cov: str | None, scope: str) -> dict:
    sid, src = row["id"], row["source"]
    ref = f"data/schemes.yaml {scope} {sid}"
    out = {"id": sid, "name": row["name"], "kind": row["kind"], "who": list(row.get("who", [])),
           "where": row.get("where", "empanelled"), "general": bool(row.get("general")),
           "check_url": row.get("check_url"), "phone": row.get("phone"), "source": src,
           "note": row.get("note"), "cover": None, "share": None, "saving": None, "values": {}}
    for k, v in (row.get("values") or {}).items():
        if k == "age":
            out["values"][k] = figs.from_rule(v, "count", Role.COUNT, sid, src, f"{ref} {k}")
            continue
        role = Role.SCHEME_COVER if k == "announced" else Role.INCOME_LIMIT
        out["values"][k] = figs.from_rule(v, "INR", role, sid, src, f"{ref} {k}")
    if row.get("cover") is not None:
        out["cover"] = figs.from_rule(row["cover"], "INR", Role.SCHEME_COVER, sid, src, f"{ref} cover")
    if row["kind"] == "co_pay":
        out["share"] = figs.from_rule(row["share"], "percent", Role.SHARE, sid, src, f"{ref} share")
    if cov is None:
        return out
    c = figs.value(cov)
    if row["kind"] == "no_ceiling":
        out["saving"] = figs.computed(c, "INR", Role.POTENTIAL_SAVING,
                                      "package-covered amount (this scheme has no yearly money limit)", [cov])
    elif row["kind"] == "co_pay":
        part = q(c * figs.value(out["share"]) / 100)
        out["saving"] = figs.computed(min(part, figs.value(out["cover"])), "INR", Role.POTENTIAL_SAVING,
                                      "smaller of share × package-covered amount and the scheme cap",
                                      [cov, out["share"], out["cover"]])
    else:
        out["saving"] = figs.computed(min(c, figs.value(out["cover"])), "INR", Role.POTENTIAL_SAVING,
                                      "smaller of the package-covered amount and the scheme cover",
                                      [cov, out["cover"]])
    return out


def compute(bill: Bill, figs: FigureStore, state: str | None) -> dict:
    """Language-free result; kk.service renders it. Adds figures to `figs`."""
    data = load()
    st = norm_state(state)
    cov, left_out = covered_amount(bill, figs)
    state_rows = [_scheme(r, figs, cov, st) for r in (data["states"].get(st) or [])] if st else []
    central = [_scheme(r, figs, cov, "central") for r in data["central"]]
    best = None
    for r in state_rows + central:   # state first: on a tie the state scheme is named
        if r["general"] and r["saving"] and (best is None or figs.value(r["saving"]) > figs.value(best["saving"])):
            best = r
    return {"state": st, "state_name": STATE_NAMES.get(st), "covered": cov, "left_out": left_out,
            "state_rows": state_rows, "central": central,
            "best": {"id": best["id"], "name": best["name"], "saving": best["saving"]} if best else None,
            "checked": data.get("checked")}


def fig_ids(res: dict) -> list[str]:
    """Every figure the rendered module may show, for the proof panel."""
    ids = [res["covered"], res["left_out"]]
    for r in res["state_rows"] + res["central"]:
        ids += [r["cover"], r["share"], r["saving"], *r["values"].values()]
    return [i for i in ids if i]
