"""Recognise price-controlled items from bill descriptions.

Conservative by design: when a detail (stent type, implant material) is unclear,
the classifier returns every candidate and the rule uses the highest ceiling,
so an unclear line can never produce an inflated overcharge.
"""

from __future__ import annotations

import re

NON_CORONARY = re.compile(r"(?i)\b(dj|double\s*j|ureter\w*|biliary|pancrea\w*|oesophag\w*|esophag\w*|"
                          r"colonic|duodenal|enteral|peripheral|carotid|renal\s+artery|iliac|femoral\s+artery|"
                          r"tracheal|bronch\w*|nasal|airway|vascular\s+graft)\b")
# coronary stent brand names sold in India are recognised as stents; the type still comes from
# the description, and an unknown type falls back to the higher DES ceiling
STENT = re.compile(r"(?i)\bstents?\b|\bbvs\b|\bscaffold\b|\bdes\b|\b(xience|resolute|synergy|orsiro|"
                   r"ultimaster|biomime|yukon|supraflex|firehawk|promus|onyx|metafor|coroflex|endeavor|"
                   r"tetriflex|evermine|everflex)\b")
DES = re.compile(r"(?i)drug[\s\-]*elut|\bdes\b|everolimus|sirolimus|zotarolimus|biolimus|novolimus|"
                 r"paclitaxel|bioresorbable|biodegradable|\bbvs\b|scaffold")
BMS = re.compile(r"(?i)bare[\s\-]*metal|\bbms\b")


def _whole(desc: str, m: re.Match) -> str:
    """The matched words, extended to whole words ("Drug Elut" -> "Drug Eluting")."""
    start, end = m.start(), m.end()
    while start > 0 and desc[start - 1].isalnum():
        start -= 1
    while end < len(desc) and desc[end].isalnum():
        end += 1
    return desc[start:end]


def stent_match(desc: str, kb=None) -> dict | None:
    """Why a line is (or is not) a coronary stent, and which ceiling category applies.

    Returns None for anything that is not a coronary stent (including DJ, biliary and other
    non-coronary stents), else {"kind", "how", "matched", "brand_row"}:
      how = "type_words"  the line itself says drug-eluting / bare metal
            "brand"       a brand from hospital-published stent lists (kb.stent_brand)
            "stent_word"  the word stent / scaffold / DES with no brand or type
    A brand's DES label is used; any other brand type, or no type, falls back to the higher
    DES ceiling ("stent_unknown"), so recognition can never inflate a claim.
    """
    if NON_CORONARY.search(desc):
        return None
    brand = kb.stent_brand(desc) if kb is not None else None
    word = STENT.search(desc)
    if not word and brand is None:
        return None
    m = DES.search(desc)
    if m:
        return {"kind": "stent_des", "how": "type_words", "matched": _whole(desc, m), "brand_row": brand[0].id if brand else None}
    m = BMS.search(desc)
    if m:
        return {"kind": "stent_bms", "how": "type_words", "matched": _whole(desc, m), "brand_row": brand[0].id if brand else None}
    if brand is not None:
        row, alias = brand
        kind = "stent_des" if row.data["type"] == "des" else "stent_unknown"
        return {"kind": kind, "how": "brand", "matched": alias, "brand_row": row.id,
                "brand_label": row.data["hospital_label"], "brand_source": row.data["source_ref"]}
    return {"kind": "stent_unknown", "how": "stent_word", "matched": _whole(desc, word), "brand_row": None}


def stent_kind(desc: str, kb=None) -> str | None:
    """'stent_des', 'stent_bms', 'stent_unknown' or None (not a coronary stent)."""
    m = stent_match(desc, kb)
    return m["kind"] if m else None


def knee_match_text(desc: str) -> str | None:
    m = KNEE_CTX.search(desc)
    return m.group(0) if m else None


KNEE_CTX = re.compile(r"(?i)\b(knee|tkr|tka|total\s+knee|femoral\s+comp\w*|tibial|patell\w*|"
                      r"articulating)\b")
HIP_ETC = re.compile(r"(?i)\b(hip|acetabul\w*|shoulder|elbow|spine|spinal|locking\s+plate|bone\s+screw|"
                     r"interlocking|nail)\b")


def knee_candidates(desc: str) -> tuple[str, list[str], list[str]] | None:
    """Return (system, components, materials) for a knee implant line, or None.

    components/materials are lists of candidates; empty materials means 'unknown'.
    """
    if not KNEE_CTX.search(desc) or HIP_ETC.search(desc):
        return None
    d = desc.lower()
    system = "revision" if "revision" in d else "primary"
    comps: list[str] = []
    if re.search(r"femor", d):
        comps.append("femoral")
    if re.search(r"tibial\s+(tray|base\s*plate|baseplate)?.*(insert|poly)|tray\s*\+\s*insert|all[\s\-]*poly", d):
        comps.append("tibial_insert_combined")
    elif re.search(r"tibi", d):
        comps.append("tibial")
    if re.search(r"\binsert\b|articulat|bearing|\bpoly\w*\b", d) and "tibial_insert_combined" not in comps:
        comps.append("insert")
    if re.search(r"patell", d):
        comps.append("patella")
    if len(comps) != 1:
        # zero components (a lump 'knee implant set') or several on one line cannot be checked line by line
        return system, comps, []
    mats: list[str] = []
    if re.search(r"titan|\bti\b", d):
        mats.append("titanium")
    if re.search(r"oxidi[sz]ed\s+zircon|oxinium|oxzr", d):
        mats.append("oxidized_zirconium")
    if re.search(r"hi[\s\-]*flex|high[\s\-]*flex", d):
        mats.append("hi_flex")
    if re.search(r"cobalt|co[\s\-]*cr\b|cocr", d):
        mats.append("cobalt_chromium_or_other")
    if comps == ["tibial_insert_combined"]:
        mats = ["polyethylene"] if re.search(r"all[\s\-]*poly", d) else ["metal_tray_with_insert"]
    return system, comps, mats
