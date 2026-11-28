"""Render findings from templates and the figure store.

Output is a list of segments so a UI can make every number tappable:
  {"t": "text"}  or  {"fig": "F12", "t": "₹41,145.33"}
"""

from __future__ import annotations

import html
import re
import string

from ..figures import FigureStore
from ..models import AuditResult, Finding, Figure
from ..money import indian_grouping
from . import messages_en, messages_gu, messages_hi, messages_kn, messages_ta, messages_te

from .messages_more import X as _MORE
from .messages_schemes import S as _SCHEMES

CATALOG = {"en": messages_en.M, "hi": messages_hi.M, "kn": messages_kn.M, "gu": messages_gu.M,
           "ta": messages_ta.M, "te": messages_te.M}
CATALOG = {lang: {**cat, **_SCHEMES[lang], **_MORE[lang]} for lang, cat in CATALOG.items()}
LANGS = tuple(CATALOG)


def msg(key: str, lang: str) -> str:
    cat = CATALOG.get(lang, CATALOG["en"])
    return cat.get(key) or CATALOG["en"].get(key) or key


def fmt_figure(f: Figure) -> str:
    if f.unit == "INR":
        if f.role.value in ("scheme_cover", "income_limit", "benchmark") and f.value == f.value.to_integral_value():
            return "₹" + indian_grouping(f.value).split(".")[0]   # a published limit, not a bill amount
        return "₹" + indian_grouping(f.value)
    if f.unit == "percent":
        v = f.value.normalize()
        return f"{v:f}"
    if f.unit in ("count", "days"):
        v = f.value
        return f"{v.normalize():f}" if v != v.to_integral_value() else str(int(v))
    return str(f.value)


def segments(template: str, slots: dict[str, str], text_slots: dict[str, str], figs: dict[str, Figure]) -> list[dict]:
    out: list[dict] = []
    for literal, field, _spec, _conv in string.Formatter().parse(template):
        if literal:
            out.append({"t": literal})
        if field is None:
            continue
        if field in slots and slots[field] in figs:
            fid = slots[field]
            out.append({"fig": fid, "t": fmt_figure(figs[fid])})
        elif field in text_slots:
            out.append({"t": text_slots[field]})
        else:
            out.append({"t": "…"})
    return out


def plain(segs: list[dict]) -> str:
    return "".join(s["t"] for s in segs)


def to_html(segs: list[dict]) -> str:
    parts = []
    for s in segs:
        if "fig" in s:
            parts.append(f'<a class="fig" href="#{s["fig"]}" data-fig="{s["fig"]}">{html.escape(s["t"])}</a>')
        else:
            parts.append(html.escape(s["t"]))
    return "".join(parts)


def render_finding(f: Finding, result: AuditResult, lang: str) -> dict:
    figs = result.figures
    return {
        "rule_id": f.rule_id,
        "family": f.family,
        "verdict": f.verdict.value,
        "verdict_label": msg(f"verdict_{f.verdict.value}", lang),
        "title": msg(f"title_{f.rule_id}", lang),
        "line_id": f.line_id,
        "channel": f.channel.value,
        "legal_status": f.legal_status,
        "legal_label": msg(f"legal_{f.legal_status}", lang),
        "text": segments(msg(f.message_key, lang), f.slots, f.text_slots, figs),
        "conditions": [msg(c, lang) for c in f.conditions],
        "asks": [msg(a, lang) for a in f.asks],
        "sources": f.source_ids,
        "excess_fig": f.excess_fig,
    }


def remedies(result: AuditResult, lang: str) -> list[list[dict]]:
    """Who decides each part of the challengeable amount: the hospital, or the scheme."""
    figs, out = result.figures, []
    if result.hospital_fig:
        out.append(segments(msg("remedy_hospital", lang), {"amount": result.hospital_fig}, {}, figs))
    if result.scheme_fig:
        out.append(segments(msg("remedy_scheme", lang), {"amount": result.scheme_fig}, {}, figs))
    if result.fallback_fig:
        out.append(segments(msg("remedy_fallback", lang), {"amount": result.fallback_fig}, {}, figs))
    return out


def coverage(result: AuditResult, lang: str) -> list[list[dict]]:
    """What share of the bill a rule could actually check. Shown with every result."""
    c, figs = result.coverage, result.figures
    if not c:
        return []
    out = []
    key = "cov_line" if c.get("share") else "cov_line_noshare"
    out.append(segments(msg(key, lang), {"rule": c["rule"], "lines": c["lines"], "share": c.get("share", "")}, {}, figs))
    if figs[c["basic"]].value:
        out.append(segments(msg("cov_basic", lang), {"basic": c["basic"]}, {}, figs))
    if figs[c["pending"]].value:
        out.append(segments(msg("cov_pending", lang), {"pending": c["pending"]}, {}, figs))
    return out


def line_match(result: AuditResult, line_id: str, lang: str) -> dict:
    x = result.crosswalk.get(line_id)
    if not x:
        return {}
    reasons = [segments(msg(m["reason"], lang), {}, m.get("text", {}), result.figures) for m in x["matches"]]
    if x.get("reason"):
        reasons.append(segments(msg(x["reason"], lang), {}, {}, result.figures))
    return {"status": x["status"], "reasons": reasons, "basic_checks": x["basic_checks"],
            "rules": [{"rule_id": m["rule_id"], "row_id": m["row_id"], "source_id": m["source_id"]} for m in x["matches"]]}


def summary(result: AuditResult, lang: str) -> list[list[dict]]:
    figs = result.figures
    out = []
    if result.recoverable_fig:
        out.append(segments(msg("summary_recoverable", lang), {"recoverable": result.recoverable_fig}, {}, figs))
        out.extend(remedies(result, lang))
    else:
        out.append(segments(msg("summary_none", lang), {}, {}, figs))
    if result.amber_total_fig:
        out.append(segments(msg("summary_amber", lang), {"amber": result.amber_total_fig}, {}, figs))
    if any(f.verdict.value == "grey" for f in result.findings):
        out.append(segments(msg("summary_grey", lang), {}, {}, figs))
    return out


def figure_proof(fid: str, result: AuditResult, kb) -> dict:
    """Everything the proof panel shows for one number."""
    f = result.figures[fid]
    ev = f.evidence
    d = {"id": fid, "display": fmt_figure(f), "role": f.role.value, "origin": f.origin.value,
         "confidence": f.confidence}
    if ev.bill_tokens or ev.bbox:
        d["bill"] = {"tokens": ev.bill_tokens, "bbox": ev.bbox.model_dump() if ev.bbox else None}
    if ev.rule_row:
        d["rule"] = {"row": ev.rule_row, "source_id": ev.source_id, "source_title": kb.source_title(ev.source_id),
                     "source_url": kb.source_url(ev.source_id), "ref": ev.source_ref}
    if ev.formula:
        d["formula"] = {"text": ev.formula, "inputs": [{"id": i, "display": fmt_figure(result.figures[i]),
                                                        "role": result.figures[i].role.value} for i in ev.inputs]}
    if ev.note:
        d["note"] = ev.note
    return d


_SLOT_IN_TEXT = re.compile(r"\[(\w+):(F\d+)\]")


def schemes_panel(res: dict, figs: dict[str, Figure], lang: str) -> dict:
    """Render kk.schemes.compute() output. Every amount is a tappable figure segment."""
    m = lambda key, slots=None, text=None: segments(msg(key, lang), slots or {}, text or {}, figs)

    def row(r: dict) -> dict:
        kind = {"family_year": "sav_row", "one_time": "sav_row_onetime",
                "no_ceiling": "sav_row_noceiling", "co_pay": "sav_row_copay"}[r["kind"]]
        if not r["saving"]:
            kind += "_cover"
        slots = {"cover": r["cover"], "saving": r["saving"], "share": r["share"], **r["values"]}
        slots = {k: v for k, v in slots.items() if v}
        out = {"id": r["id"], "name": r["name"], "general": r["general"],
               "line": m(kind, slots),
               "who": [m("sav_who_" + c, slots) for c in r["who"]],
               "where": m("sav_where_" + r["where"]) if r["where"] != "empanelled" else None,
               "note": m("sav_note_" + r["note"], slots) if r.get("note") else None,
               "check_url": r["check_url"], "phone": r["phone"],
               "source": r["source"], "cover_fig": r["cover"], "saving_fig": r["saving"]}
        return out

    st = res["state_name"]
    return {
        "applies": True,
        "state": res["state"],
        "title": msg("sav_title", lang),
        "intro": m("sav_intro", {"covered": res["covered"]}) if res["covered"] else m("sav_nothing"),
        "best": m("sav_best", {"saving": res["best"]["saving"]}, {"scheme": res["best"]["name"]})
        if res["best"] else None,
        "best_fig": res["best"]["saving"] if res["best"] else None,
        "left_out": m("sav_left_out", {"count": res["left_out"]})
        if res["left_out"] and figs[res["left_out"]].value > 0 else None,
        "head_state": m("sav_head_state", {}, {"state": st}) if st else None,
        "no_state_scheme": m("sav_no_state_scheme", {}, {"state": st}) if st and not res["state_rows"] else None,
        "choose_state": None if st else m("sav_choose_state"),
        "state_rows": [row(r) for r in res["state_rows"]],
        "head_central": m("sav_head_central"),
        "central": [row(r) for r in res["central"]],
        "more": msg("sav_more", lang),
        "labels": {k: msg("sav_" + k, lang) for k in ("pick_state", "check", "call", "source")},
        "conds": m("sav_conds"),
        "not_counted": m("sav_not_counted"),
        "have_card": m("sav_have_card"),
        "checked": m("sav_checked", {}, {"date": res["checked"]}),
    }


# ---------------------------------------------------------------- complaint tracker (kk/tracker.py)
def tracker_panel(res: dict, figs: dict[str, Figure], lang: str, kb) -> dict:
    """Render kk.tracker.plan() output: a step list with segments, plus calendar entries."""
    m = lambda key, slots=None, text=None: segments(msg(key, lang), slots or {}, text or {}, figs)
    iso = lambda d: d.isoformat() if d else None
    steps, cal = [], []
    for s in res["steps"]:
        name = msg("trk_name_" + s["id"], lang)
        lines = []
        if s["sent_on"]:
            lines.append(m("trk_st_sent", {}, {"date": iso(s["sent_on"])}))
        if s["reply_on"]:
            key = "trk_st_resolved" if s["outcome"] == "solved" else "trk_st_reply"
            lines.append(m(key, {}, {"date": iso(s["reply_on"])}))
        if s["wait"] and s["wait"]["due"] and s["status"] in ("waiting", "overdue"):
            lines.append(m("trk_wait_" + s["wait"]["kind"], {"days": s["wait"]["days"]},
                           {"date": iso(s["wait"]["due"])}))
            if s["status"] == "waiting":
                cal.append({"date": s["wait"]["due"], "summary": plain(m("trk_cal_due", {}, {"step": name})),
                            "description": plain(m("trk_do_" + s["id"], {}, {"phone": s["phone"] or ""}))})
        if s["opens"] and s["opens"]["on"] and s["status"] in ("next", "later"):
            lines.append(m("trk_opens_after", {"months": s["opens"]["months"]}, {"date": iso(s["opens"]["on"])}))
        lim = s["limit"]
        if lim and s["status"] not in ("resolved", "not_needed"):
            if lim["from"] == "cause" and lim["last"]:
                lines.append(m("trk_limit_cause", {"years": lim["n"]},
                               {"date": iso(lim["last"]), "from_date": iso(lim["start"])}))
            elif lim["from"] == "prev" and lim["last"]:
                lines.append(m("trk_limit_prev", {"years": lim["n"]}, {"date": iso(lim["last"])}))
            elif lim["from"] == "decision" and lim["last"]:
                lines.append(m("trk_limit_decision", {"days": lim["n"]}, {"date": iso(lim["last"])}))
            if lim["last"] and s["status"] in ("next", "later") and lim["last"] >= res["today"]:
                cal.append({"date": lim["last"], "summary": plain(m("trk_cal_last", {}, {"step": name})),
                            "description": plain(m("trk_do_" + s["id"], {}, {"phone": s["phone"] or ""}))})
        status_key = {"waiting": "trk_st_waiting", "overdue": "trk_st_overdue", "rejected": "trk_st_rejected",
                      "next": "trk_st_next", "later": "trk_st_later", "resolved": None,
                      "not_needed": "trk_st_not_needed", "expired": "trk_st_expired"}[s["status"]]
        basis = []
        for b in s["sources"]:
            basis.append({"title": kb.source_title(b["source"]), "url": kb.source_url(b["source"]),
                          "ref": b["ref"], "suggestion": b["source"] == "kk_suggested_waits"})
        steps.append({"id": s["id"], "name": name, "status": s["status"],
                      "do": m("trk_do_" + s["id"], {}, {"phone": s["phone"] or ""}),
                      "status_text": m(status_key) if status_key else None,
                      "lines": lines, "phone": s["phone"], "url": s["url"], "basis": basis,
                      "sent_on": iso(s["sent_on"]), "reply_on": iso(s["reply_on"]), "outcome": s["outcome"]})
    labels = {k: msg("trk_l_" + k, lang) for k in ("track", "sent", "reply", "outcome", "solved", "not_solved",
                                                   "problem_date", "ics", "clear", "basis")}
    return {"channel": res["channel"], "title": msg("trk_title", lang), "intro": m("trk_intro"),
            "counted": m("trk_counted"), "steps": steps, "next": res["next"], "labels": labels,
            "cause_on": iso(res["cause_on"]), "today": iso(res["today"]), "checked": res["checked"],
            "calendar": sorted(cal, key=lambda e: e["date"])}


# ---------------------------------------------------------------- insurance deductions (kk/insurance.py)
def insurance_panel(res: dict, figs: dict[str, Figure], lang: str, kb) -> dict:
    m = lambda key, slots=None, text=None: segments(msg(key, lang), slots or {}, text or {}, figs)
    rows = []
    for r in res["rows"]:
        text = {"item": r["item"]}
        lines = [m(r["key"], {"amount": r["amount"]}, text)]
        if r["kind"] == "subsumed":
            lines.append(m({True: "ins_hosp_cashless", False: "ins_hosp_reimb"}.get(res["cashless"], "ins_hosp_unknown")))
        if r["over"]:
            lines.append(m("ins_over_billed", {"amount": r["amount"], "billed": r["billed"]}, text))
        listed = None
        if r["listed"]:
            listed = m("ins_matched", {}, {"list": r["listed"]["list"], "serial": str(r["listed"]["serial"]),
                                           "listed": r["listed"]["item"]})
        rows.append({"n": r["n"], "item": r["item"], "kind": r["kind"], "lines": lines, "listed": listed,
                     "line_id": r["line_id"], "amount_fig": r["amount"],
                     "source_title": kb.source_title(r["source"]), "source_url": kb.source_url(r["source"]),
                     "source_ref": (r["listed"] or {}).get("ref") or kb.sources.get(r["source"], {}).get("rule_ref")})
    tot = lambda key, fid: m(key, {"total": fid}) if fid else None
    labels = {k: msg("ins_l_" + k, lang) for k in ("item", "amount", "reason", "line", "add", "check", "remove",
                                                   "cashless", "yes", "no", "dk")}
    return {"title": msg("ins_title", lang), "intro": m("ins_intro"), "rows": rows,
            "total": tot("ins_total", res["total"]),
            "hospital": tot("ins_ask_hospital", res["hospital_total"]),
            "insurer": tot("ins_ask_insurer", res["insurer_total"]),
            "optional": tot("ins_optional_total", res["optional_total"]),
            "next": m("ins_next", {"days": res["wait"]}) if res["insurer_total"] and res["wait"] else None,
            "source": m("ins_source"), "empty": m("ins_empty"), "labels": labels, "cashless": res["cashless"]}
