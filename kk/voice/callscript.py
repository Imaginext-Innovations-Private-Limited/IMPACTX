"""What to say on the phone: a short script built from this bill's own findings.

One script for the hospital billing desk (price caps, MRP, arithmetic) and one for the PM-JAY
helpline 14555 (items the package covers). Every amount is a figure slot, so the script shows and
speaks only verified numbers. Bill item names stay in the text, so the family can read them out,
but are not read inside another language's speech.
"""

from __future__ import annotations

from ..compose.render import msg, segments
from ..models import AuditResult, Channel, Verdict
from .script import _speech_lines, _speechify

TOP = 3
HOSPITAL = {Channel.NPPA, Channel.CONSUMER, Channel.HOSPITAL_DESK}
PHONES = {"scheme": "14555"}


def _line(f, lang, figs):
    item = f.text_slots.get("item") or msg(f"title_{f.rule_id}", lang)
    if f.rule_id.startswith("ENT-"):
        key = "call_scheme_item"
    elif f.rule_id == "PRC-MRP":
        key = "call_mrp"
    elif f.rule_id.startswith("ARI-") and "expected" in f.slots:
        key = "call_arith"
    elif "allowed" in f.slots:
        key = "call_price"
    else:
        return []
    segs = segments(msg(key, lang), f.slots, {"item": item}, figs)
    for s in segs:
        if s.get("t") == item and "fig" not in s:
            s["item"] = True
    return segs


def build_calls(result: AuditResult, lang: str = "en") -> list[dict]:
    figs = result.figures
    reds = [f for f in result.findings if f.verdict == Verdict.RED and f.excess_fig in figs]
    reds.sort(key=lambda f: figs[f.excess_fig].value, reverse=True)
    groups = [
        ("hospital", [f for f in reds if f.channel in HOSPITAL], result.hospital_fig, "hospital"),
        ("scheme", [f for f in reds if f.channel == Channel.SCHEME], result.scheme_fig, "scheme"),
    ]
    out = []
    for who, fs, total, kind in groups:
        if not fs:
            continue
        sents = [segments(msg(f"call_intro_{kind}", lang), {}, {}, figs)]
        for f in fs[:TOP]:
            body = _line(f, lang, figs)
            if body:
                sents.append(body)
        if total and total in figs:
            sents.append(segments(msg(f"call_total_{kind}", lang), {"total": total}, {}, figs))
        sents.append(segments(msg(f"call_ask_{kind}", lang), {}, {}, figs))
        sents.append(segments(msg("call_tip", lang), {}, {}, figs))
        sents = [_speechify(s, result, lang) for s in sents]
        out.append({"who": who, "phone": PHONES.get(who), "lang": lang, "sentences": sents,
                    "text": " ".join("".join(x["t"] for x in s) for s in sents),
                    "speech_lines": [l for l in _speech_lines(sents, lang) if l]})
    return out
