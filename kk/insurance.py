"""Health-insurance deduction check: is each cut the insurer made one IRDAI's lists allow?

The family types what the settlement letter cut (item, amount, reason given). Each cut is matched
against IRDAI's standard lists (data/reference/irdai_lists.csv, from the Master Circular on
Standardization of Health Insurance Products):

  List I    optional items: not paid unless the policy has an add-on            -> "optional"
  List II   part of room charges         } the insurer does not pay them separately, and a network
  List III  part of procedure charges    } hospital must not bill them to the policyholder in a
  List IV   part of the cost of treatment} cashless claim                         -> "subsumed"
  not in any list                        -> "question": ask for the policy clause (insurers must give
                                            the reason with reference to the policy terms)
  cut in proportion to room rent         -> "question": IRDAI's 2020 norms bar it for ICU charges and
                                            for medicines, consumables, implants, devices and tests

Nothing here becomes a claimed amount: these are questions to the insurer or the hospital, with
the list entry or rule each one rests on. Amounts are figures typed by the family (origin user).
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from .figures import FigureStore
from .kb import KnowledgeBase
from .models import Bill, Evidence, Origin, Role
from .money import q
from .rules.base import billed_total
from .rules.tax import ICU_RE

LIST_KIND = {"I": "optional", "II": "sub_room", "III": "sub_proc", "IV": "sub_treat"}
PROP_RE = re.compile(r"(?i)proportion\w*|pro[\s-]*rata|room\s*rent|room\s*categor\w*|room\s*limit|"
                     r"eligible\s+room|higher\s+room|room\s*capping|\bratio\b")
GOODS_RE = re.compile(r"(?i)\b(medicine\w*|drug\w*|tab\w*|cap\w*|inj\w*|syrup|syp|pharmacy|consumable\w*|"
                      r"implant\w*|stent\w*|device\w*|investigation\w*|test\w*|lab\w*|x-?ray|scan|mri|ct\b|"
                      r"diagnostic\w*|pathology|radiology)\b")
MED_RE = re.compile(r"(?i)\b\d+(\.\d+)?\s*(mg|mcg|ml|gm|g|iu)\b|\b(tab|tablet|tablets|cap|capsule|capsules|"
                    r"inj|injection|syp|syrup|susp)\b")
SINGLE_OK_FOR_MEDICINE = {"lozenge", "spacer", "glucometer", "sterillium"}
GOODS_SECTIONS = {"pharmacy", "consumables", "implant", "diagnostics"}
DROP_SHORT = {"Baby", "Service", "Certificate", "diet"}   # too general once "charges" is dropped


def _norm(text: str) -> list[str]:
    toks = re.sub(r"[^a-z0-9]+", " ", text.lower()).split()
    return [t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t for t in toks]


def _phrases(kb: KnowledgeBase) -> list[tuple[tuple[str, ...], dict]]:
    """Every name an IRDAI list row goes by, longest first; built once per knowledge base."""
    cached = getattr(kb, "_irdai_phrases", None)
    if cached is not None:
        return cached
    rows = [r.data for r in kb.tables["irdai_lists"]]
    out = []
    for r in rows:
        item = r["item"]
        base = re.sub(r"\([^)]*\)", " ", item)
        parts = {base} | set(re.split(r"\s*/\s*|\s*,\s*|\s+-\s+|\s*&\s*", base))
        parts |= {p for p in (r.get("also") or "").split("|") if p}
        # "Laundry charges" is also written just "Laundry"
        parts |= {re.sub(r"(?i)\s+(charges?|cost)$", "", p) for p in list(parts)
                  if re.search(r"(?i)\s+(charges?|cost)$", p)} - DROP_SHORT
        for p in parts:
            toks = tuple(_norm(p))
            if toks and len(" ".join(toks)) >= 3:
                out.append((toks, r))
    out.sort(key=lambda x: (-len(x[0]), -len(" ".join(x[0]))))
    kb._irdai_phrases = out
    return out


def _contains(text: list[str], phrase: tuple[str, ...]) -> bool:
    n = len(phrase)
    return any(tuple(text[i:i + n]) == phrase for i in range(len(text) - n + 1))


def match(kb: KnowledgeBase, text: str) -> dict | None:
    """The IRDAI list row the text names, longest phrase first; None if it names none."""
    toks = _norm(text)
    medicine = bool(MED_RE.search(text))
    for phrase, row in _phrases(kb):
        if medicine and len(phrase) == 1 and phrase[0] not in SINGLE_OK_FOR_MEDICINE:
            continue   # "Omez 20 mg caps" is a medicine, not List II "caps"
        if _contains(toks, phrase):
            return row
    return None


def _amount(v) -> Decimal:
    try:
        d = Decimal(str(v).replace(",", "").replace("₹", "").strip())
    except (InvalidOperation, AttributeError) as e:
        raise ValueError(f"amount is not a number: {v!r}") from e
    if d <= 0:
        raise ValueError("amount must be more than zero")
    return d


def check(bill: Bill, figs: FigureStore, kb: KnowledgeBase, deductions: list[dict], cashless: bool | None,
          wait_fig: str | None = None) -> dict:
    lines = {l.id: l for l in bill.lines}
    rows, optional, hospital, insurer, all_ids = [], [], [], [], []
    for i, d in enumerate(deductions or [], 1):
        line = lines.get(d.get("line_id") or "")
        if d.get("line_id") and line is None:
            raise ValueError(f"deduction {i}: no bill line {d['line_id']!r}")
        item = (d.get("item") or "").strip() or (line.description if line else "")
        if not item:
            raise ValueError(f"deduction {i}: name the item that was cut")
        reason = (d.get("reason") or "").strip()
        amt_id = figs.add(_amount(d.get("amount")), "INR", Role.DEDUCTED, Origin.USER,
                          Evidence(note=f"typed from the insurer's settlement letter: {item[:80]}"))
        all_ids.append(amt_id)
        text = f"{item} {line.description if line else ''}"
        row = {"n": i, "item": item, "reason": reason, "amount": amt_id, "line_id": line.id if line else None,
               "listed": None, "billed": None, "over": False}
        if PROP_RE.search(reason):
            if ICU_RE.search(text):
                row["kind"], row["key"] = "question", "ins_prop_icu"
            elif (line and line.section in GOODS_SECTIONS) or GOODS_RE.search(text):
                row["kind"], row["key"] = "question", "ins_prop_goods"
            else:
                row["kind"], row["key"] = "question", "ins_prop_other"
            row["source"] = "irdai_proportionate_2020"
        else:
            hit = match(kb, item) or (match(kb, line.description) if line else None)
            if hit is None:
                row["kind"], row["key"], row["source"] = "question", "ins_not_listed", "irdai_mc_health_2024"
            else:
                kind = LIST_KIND[hit["list"]]
                row["kind"] = "optional" if kind == "optional" else "subsumed"
                row["key"] = "ins_" + kind
                row["source"] = hit["source_id"]
                row["listed"] = {"list": hit["list"], "serial": hit["serial"], "item": hit["item"],
                                 "row_id": hit["row_id"], "ref": hit["source_ref"]}
        if line is not None:
            billed, _, _ = billed_total(line, figs)
            if billed is not None:
                row["billed"] = line.amount_fig
                if figs.value(amt_id) > billed + Decimal("1"):
                    row["over"] = True
        {"optional": optional, "subsumed": hospital, "question": insurer}[row["kind"]].append(amt_id)
        rows.append(row)

    def total(ids, formula):
        if not ids:
            return None
        if len(ids) == 1:
            return ids[0]
        return figs.computed(q(sum(figs.value(x) for x in ids)), "INR", Role.TOTAL, formula, ids)

    return {"rows": rows, "cashless": cashless,
            "total": total(all_ids, "sum of the cuts typed from the settlement letter"),
            "optional_total": total(optional, "sum of cuts on IRDAI List I (optional) items"),
            "hospital_total": total(hospital, "sum of cuts on items IRDAI subsumes into room, procedure or treatment")
            if cashless else None,
            "insurer_total": total(insurer, "sum of cuts that are not on IRDAI's lists or are proportionate"),
            "wait": wait_fig}


def fig_ids(res: dict) -> list[str]:
    ids = [r["amount"] for r in res["rows"]] + [r["billed"] for r in res["rows"] if r["billed"]]
    ids += [res[k] for k in ("total", "optional_total", "hospital_total", "insurer_total", "wait") if res.get(k)]
    return ids
