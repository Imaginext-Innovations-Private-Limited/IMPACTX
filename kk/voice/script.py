"""The spoken summary of a checked bill.

Two sources, same guarantees:
  - "llm": the local model writes the summary with slot tokens; the slot verifier must pass
    (no digits, number words or currency outside slots). Only then are slots filled.
  - "template": fixed sentences in each language, filled from the figure store.
In both cases every number is said with spoken() from the stored Decimal and shown with
fmt_figure() in the caption, so the voice and the screen can never disagree.
"""

from __future__ import annotations

import re

from ..compose.explain import explain
from ..compose.render import coverage, fmt_figure, msg, remedies, segments
from ..models import AuditResult, Verdict
from .spoken import PERCENT_WORD, spoken

TOP_RED = 3
_END = re.compile(r"(?<=[.!?।])\s+")
_HAS_DIGIT = re.compile(r"[^\s()]*\d[^\s()]*")   # sizes and codes in item names: 3.0x28, 40mg, 0.014
_STOP = {"hi": "।"}


def _say_text(t: str) -> str:
    """Speech for plain text. Templates and verified model text hold no digits, so a digit here can
    only come from a bill item name (a size or code). It is dropped from speech, kept in the caption,
    so every number the voice says is a verified figure."""
    t = re.sub(r"\(\s*\)", "", _HAS_DIGIT.sub("", t))
    return re.sub(r"\s+([:,.;])", r"\1", re.sub(r"\s{2,}", " ", t))


def _speech_lines(sents: list[list[dict]], lang: str) -> list[str]:
    out = []
    for s in sents:
        line = re.sub(r"\s{2,}", " ", "".join(x["say"] for x in s)).strip()
        line = re.sub(r"\s+([:,.;।])", r"\1", line)
        line = re.sub(r"^[\s:,.;।]+", "", line)
        if line and line[-1] not in ".!?।:":
            line += _STOP.get(lang, ".")
        out.append(line)        # one line per sentence, so captions and speech stay aligned
    return out


def _speechify(segs: list[dict], result: AuditResult, lang: str) -> list[dict]:
    out = []
    for s in segs:
        if "fig" in s and s["fig"] in result.figures:
            f = result.figures[s["fig"]]
            out.append({"fig": s["fig"], "t": fmt_figure(f), "say": spoken(f, lang)})
        else:
            say = "" if (s.get("item") and lang != "en") else _say_text(s["t"])
            if out and out[-1].get("fig") and result.figures[out[-1]["fig"]].unit == "percent" and say.startswith("%"):
                say = " " + PERCENT_WORD.get(lang, "percent") + say[1:]
            out.append({"t": s["t"], "say": say})
    return out


def _sentences(segs: list[dict]) -> list[list[dict]]:
    """Split a flat segment list into sentences at sentence-ending punctuation in text segments."""
    out, cur = [], []
    for s in segs:
        if "fig" in s:
            cur.append(s)
            continue
        parts = _END.split(s["t"])
        for i, p in enumerate(parts):
            if p:
                cur.append({"t": p})
            if i < len(parts) - 1 and cur:
                out.append(cur)
                cur = []
    if cur and any(("fig" in s) or s["t"].strip() for s in cur):
        out.append(cur)
    return out


def template_script(result: AuditResult, lang: str) -> list[list[dict]]:
    figs = result.figures
    lines: list[list[dict]] = [segments(msg("voice_intro", lang), {}, {}, figs)]
    if result.recoverable_fig:
        lines.append(segments(msg("summary_recoverable", lang), {"recoverable": result.recoverable_fig}, {}, figs))
        lines.extend(remedies(result, lang))
    else:
        lines.append(segments(msg("summary_none", lang), {}, {}, figs))
    reds = [f for f in result.findings if f.verdict == Verdict.RED and f.excess_fig in figs]
    reds.sort(key=lambda f: figs[f.excess_fig].value, reverse=True)
    if reds:
        lines.append(segments(msg("voice_problems", lang), {}, {}, figs))
        for f in reds[:TOP_RED]:
            title = msg(f"title_{f.rule_id}", lang)
            item = f.text_slots.get("item")
            key, texts = ("voice_item", {"item": item, "title": title}) if item else ("voice_item_noitem", {"title": title})
            segs = segments(msg(key, lang), {"excess": f.excess_fig}, texts, figs)
            for seg in segs:   # the bill's English item name: shown in the caption, not read inside another language
                if item and seg.get("t") == item and "fig" not in seg:
                    seg["item"] = True
            lines.append(segs)
        if len(reds) > TOP_RED:
            lines.append(segments(msg("voice_more_red", lang), {}, {}, figs))
    if result.amber_total_fig:
        lines.append(segments(msg("summary_amber", lang), {"amber": result.amber_total_fig}, {}, figs))
        lines.append(segments(msg("voice_amber_hint", lang), {}, {}, figs))
    if any(f.verdict == Verdict.GREY for f in result.findings):
        lines.append(segments(msg("summary_grey", lang), {}, {}, figs))
    lines.extend(coverage(result, lang)[:2])   # say plainly how much of the bill a rule could check
    if reds or result.amber_total_fig:
        lines.append(segments(msg("voice_next", lang), {}, {}, figs))
    lines.append(segments(msg("voice_proof", lang), {}, {}, figs))
    return lines


def build(result: AuditResult, lang: str = "en", ai: bool = True, llm=None) -> dict:
    """Return {"lang", "source", "sentences": [[{t, say, fig?}]], "text", "speech_lines", "speech"}."""
    source, sents = "template", None
    if ai:
        ex = explain(result, lang, llm=llm) if llm is not None else explain(result, lang)
        if ex["source"] == "llm":
            source, sents = "llm", _sentences(ex["segments"])
    if sents is None:
        sents = template_script(result, lang)
    sents = [_speechify(s, result, lang) for s in sents]
    return {
        "lang": lang,
        "source": source,
        "sentences": sents,
        "text": " ".join("".join(x["t"] for x in s).strip() for s in sents),
        "speech_lines": (lines := _speech_lines(sents, lang)),
        "speech": " ".join(lines),
    }
