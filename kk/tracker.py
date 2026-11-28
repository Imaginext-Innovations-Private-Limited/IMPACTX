"""Complaint tracker: after a letter is sent, when a reply is due and where to go next.

Every wait and time limit comes from data/escalation.yaml, and each one names its source:
an official text (CBIC/IRDAI/NHA/Act) or, where no official reply time exists, our own
declared suggestion (source kk_suggested_waits), which the family sees labelled as a suggestion.
Day counts and years are figures in the session's figure store, so each one is tappable to
its source; dates are worked out here from the dates the family enters.

The tracker never files anything. The family sends each letter and records the date.
Its state lives in the browser; the server only computes the timeline from what is sent.
"""

from __future__ import annotations

import calendar
import hashlib
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import yaml

from .figures import FigureStore
from .models import Role

OUTCOMES = ("solved", "not_solved")


@lru_cache(maxsize=4)
def _load(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load(data_dir: Path) -> dict:
    return _load(str(Path(data_dir) / "escalation.yaml"))


def channels(data_dir: Path) -> list[str]:
    return list(load(data_dir)["ladders"])


def add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def add_years(d: date, years: int) -> date:
    return add_months(d, 12 * years)


def _day(v) -> date | None:
    if not v:
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError as e:
        raise ValueError(f"not a date: {v!r} (use YYYY-MM-DD)") from e


def _fig(figs: FigureStore, cache: dict, sid: str, part: str, value: int, unit: str, role: Role,
         source: str, ref: str) -> str:
    """One figure per (step, part) per session, so repeated timelines reuse it."""
    key = f"{sid}:{part}"
    if key not in cache:
        cache[key] = figs.from_rule(value, unit, role, f"ESC-{sid}-{part}", source, ref)
    return cache[key]


def plan(cfg: dict, channel: str, events: dict, figs: FigureStore, cache: dict,
         cause_on: date | None = None, today: date | None = None) -> dict:
    """The timeline for one complaint channel.

    events: step id -> {"sent_on": "YYYY-MM-DD", "reply_on": "YYYY-MM-DD", "outcome": "solved"|"not_solved"}
    cause_on: the day the problem arose (for the consumer-law time limit); usually the discharge date.
    """
    if channel not in cfg["ladders"]:
        raise KeyError(f"no escalation ladder for channel {channel!r}")
    today = today or date.today()
    events = events or {}
    unknown = set(events) - set(cfg["ladders"][channel])
    if unknown:
        raise KeyError(f"steps not on the {channel} ladder: {sorted(unknown)}")
    steps, prev, resolved = [], None, False
    parsed = {}
    for sid in cfg["ladders"][channel]:
        ev = events.get(sid) or {}
        outcome = ev.get("outcome") or None
        if outcome is not None and outcome not in OUTCOMES:
            raise ValueError(f"outcome must be one of {OUTCOMES}")
        parsed[sid] = {"sent_on": _day(ev.get("sent_on")), "reply_on": _day(ev.get("reply_on")), "outcome": outcome}
        if parsed[sid]["reply_on"] and parsed[sid]["sent_on"] and parsed[sid]["reply_on"] < parsed[sid]["sent_on"]:
            raise ValueError(f"{sid}: reply date is before the date the letter was sent")

    for i, sid in enumerate(cfg["ladders"][channel]):
        st = cfg["steps"][sid]
        ev = parsed[sid]
        rec = {"id": sid, "phone": st.get("phone"), "url": st.get("url"), **ev,
               "wait": None, "opens": None, "limit": None, "sources": []}
        if st.get("info_source"):
            rec["sources"].append({"source": st["info_source"], "ref": None})

        w = st.get("wait")
        if w:
            fid = _fig(figs, cache, sid, "wait", w["days"], "days", Role.WAIT_DAYS, w["source"], w["ref"])
            due = ev["sent_on"] + timedelta(days=w["days"]) if ev["sent_on"] else None
            rec["wait"] = {"kind": w["kind"], "days": fid, "due": due}
            rec["sources"].append({"source": w["source"], "ref": w["ref"]})

        o = st.get("opens")
        if o:
            fid = _fig(figs, cache, sid, "opens", o["months"], "months", Role.TIME_LIMIT, o["source"], o["ref"])
            before = parsed.get(o["after"]) or {}
            on = None
            if before.get("reply_on") and before.get("outcome") != "solved":
                on = before["reply_on"]
            elif before.get("sent_on"):
                on = add_months(before["sent_on"], o["months"])
            rec["opens"] = {"months": fid, "on": on}
            rec["sources"].append({"source": o["source"], "ref": o["ref"]})

        lim = st.get("limit")
        if lim:
            unit, n = ("years", lim["years"]) if "years" in lim else ("days", lim["days"])
            fid = _fig(figs, cache, sid, "limit", n, unit, Role.TIME_LIMIT, lim["source"], lim["ref"])
            start = None
            if lim["from"] == "cause":
                start = cause_on
            elif lim["from"] == "decision" and prev is not None:
                start = parsed[prev]["reply_on"]
            elif lim["from"] == "prev":
                p = parsed.get(lim["prev"]) or {}
                if p.get("reply_on"):
                    start = p["reply_on"]
                elif p.get("sent_on"):
                    opens_m = (st.get("opens") or {}).get("months", 1)
                    start = add_months(p["sent_on"], opens_m)
            last = None
            if start is not None:
                last = add_years(start, n) if unit == "years" else start + timedelta(days=n)
            rec["limit"] = {"from": lim["from"], "unit": unit, "n": fid, "start": start, "last": last}
            rec["sources"].append({"source": lim["source"], "ref": lim["ref"]})

        # ---- status
        prev_status = steps[-1]["status"] if steps else None
        if resolved:
            status = "not_needed"
        elif ev["outcome"] == "solved":
            status, resolved = "resolved", True
        elif ev["reply_on"]:
            status = "rejected"
        elif ev["sent_on"]:
            due = rec["wait"]["due"] if rec["wait"] else None
            status = "overdue" if due is not None and today > due else "waiting"
        else:
            unlocked = i == 0 or prev_status in ("overdue", "rejected")
            if rec["opens"]:
                # the Ombudsman opens on its own date: the insurer's rejection, or one month after the letter
                on = rec["opens"]["on"]
                unlocked = on is not None and today >= on
            status = "next" if unlocked else "later"
            if rec["limit"] and rec["limit"]["last"] and today > rec["limit"]["last"]:
                status = "expired"
        rec["status"] = status
        steps.append(rec)
        prev = sid

    nxt = next((s["id"] for s in steps if s["status"] == "next"), None)
    return {"channel": channel, "today": today, "cause_on": cause_on, "steps": steps, "next": nxt,
            "checked": cfg.get("checked")}


# ---------------------------------------------------------------- calendar file
def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """RFC 5545: lines longer than 75 octets are folded; never split a UTF-8 character."""
    out, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > (75 if not out else 74):
            out.append(cur.decode("utf-8"))
            cur = b""
        cur += b
    out.append(cur.decode("utf-8"))
    return "\r\n ".join(out)


def ics(events: list[dict], name: str) -> str:
    """events: [{"date": date, "summary": str, "description": str}] -> an iCalendar file."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Kharcha Kavach//Complaint tracker//EN",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", f"X-WR-CALNAME:{_esc(name)}"]
    for e in events:
        d = e["date"]
        uid = hashlib.sha1(f"{d.isoformat()}|{e['summary']}".encode()).hexdigest()[:20]
        lines += ["BEGIN:VEVENT", f"UID:{uid}@kharcha-kavach", f"DTSTAMP:{stamp}",
                  f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
                  f"DTEND;VALUE=DATE:{(d + timedelta(days=1)).strftime('%Y%m%d')}",
                  f"SUMMARY:{_esc(e['summary'])}", f"DESCRIPTION:{_esc(e.get('description', ''))}",
                  "TRANSP:TRANSPARENT",
                  "BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:-P1D", f"DESCRIPTION:{_esc(e['summary'])}", "END:VALARM",
                  "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(x) for x in lines) + "\r\n"


def fig_ids(res: dict) -> list[str]:
    out = []
    for s in res["steps"]:
        for part in ("wait", "opens", "limit"):
            if s[part]:
                out.append(s[part].get("days") or s[part].get("months") or s[part].get("n"))
    return [f for f in out if f]
