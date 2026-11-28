"""Explainer chat: answers a family's questions about their checked bill, in six languages.

Every answer is built from this bill's findings, figures and fixed sentences, so it cannot state
an amount or a rule that the check did not produce:
  - amounts are figures from the store (shown exactly, spoken in words, tappable for proof);
  - phone numbers and offices come from data/channels.yaml (official sources);
  - wording comes from the reviewed templates in each language.
A local language model, when running, may only reword an answer. It sees the answer with slot
tokens instead of numbers and must pass the same verifier; otherwise the template answer stands.
Medical and legal questions are refused with a pointer to the right person.
"""

from __future__ import annotations

import re

from .compose.explain import _ollama
from .compose.render import coverage, fmt_figure, msg, remedies, render_finding, segments, summary
from .compose.verifier import fill, verify
from .grievance import channels as load_channels
from .guard import detect_language, mask_pii, refusal_kind
from .models import AuditResult, Verdict
from .rules.classify import knee_candidates, stent_match
from .voice.script import _speech_lines, _speechify

LANGS = ("en", "hi", "kn", "gu", "ta", "te")
INTENTS = ("summary", "overcharge", "next", "remedy", "coverage", "gst", "trust", "amber", "grey")

# Words that point to an intent, per language. Matching is on whole words or word starts.
KEYWORDS = {
    "next": ["what should i do", "what do i do", "next", "complain", "complaint", "letter", "call", "helpline", "who do i",
             "क्या करूँ", "क्या करें", "क्या करना", "शिकायत", "अगला", "पत्र", "हेल्पलाइन",
             "ಏನು ಮಾಡ", "ದೂರು", "ಮುಂದೆ", "ಪತ್ರ", "શું કરવ", "ફરિયાદ", "આગળ", "પત્ર",
             "என்ன செய்ய", "புகார்", "அடுத்த", "கடிதம்", "ఏమి చేయా", "ఫిర్యాదు", "తదుపరి", "లేఖ"],
    "remedy": ["refund", "money back", "get back", "grievance", "reimburs", "return my", "रिफंड", "पैसे वापस", "वापस मिल",
               "ಮರುಪಾವತಿ", "ವಾಪಸ್", "પાછા", "રિફંડ", "திருப்பி", "பணம் திரும்ப", "రీఫండ్", "తిరిగి", "డబ్బు"],
    "coverage": ["not check", "every line", "coverage", "which lines", "couldn't check", "could not check", "missed", "basic",
                 "जाँच नहीं", "जांच नहीं", "कौन सी लाइन", "ಪರಿಶೀಲಿಸಲು ಆಗಲಿಲ್ಲ", "ಪರಿಶೀಲಿಸಿಲ್ಲ", "તપાસી શકાયું નહીં", "તપાસ્યું નથી",
                 "சரிபார்க்க முடியவில்லை", "சரிபார்க்கவில்லை", "తనిఖీ చేయలేక", "తనిఖీ చేయలేదు"],
    "gst": ["gst", "tax", "जीएसटी", "टैक्स", "ತೆರಿಗೆ", "વેરો", "வரி ", "పన్ను"],
    "trust": ["how do you know", "how do i know", "proof", "source", "sure", "trust", "correct", "right?", " ai",
              "कैसे पता", "प्रमाण", "स्रोत", "सही है", "ಹೇಗೆ ಗೊತ್ತು", "ಪುರಾವೆ", "ಮೂಲ", "ಸರಿ", "કેવી રીતે ખબર", "પુરાવો", "સ્ત્રોત", "સાચું",
              "எப்படித் தெரியும்", "ஆதாரம்", "சரி என்று", "ఎలా తెలుస్తుంది", "రుజువు", "మూలం", "సరైనది"],
    "overcharge": ["overcharg", "not allowed", "too much", "extra", "excess", "wrong charge", "above the", "ज़्यादा", "ज्यादा",
                   "अधिक", "अनुमति नहीं", "ಹೆಚ್ಚು", "ಅನುಮತಿ ಇಲ್ಲ", "વધુ", "મંજૂરી નથી", "அதிக", "கூடுதல்", "அனுமதி இல்லை",
                   "ఎక్కువ", "అదనపు", "అనుమతి లేదు"],
    "amber": ["worth asking", "ask about", "question", "पूछने", "ಕೇಳಲು", "પૂછવા", "கேட்க வேண்டிய", "అడగదగిన"],
    "grey": ["cannot verify", "can't verify", "unclear", "not sure", "जाँच संभव नहीं", "ಪರಿಶೀಲನೆ ಸಾಧ್ಯವಿಲ್ಲ", "તપાસ શક્ય નથી",
             "சரிபார்க்க முடியாது", "తనిఖీ చేయలేము"],
    "summary": ["summary", "overall", "result", "what did you find", "what's wrong", "what is wrong", "explain", "tell me",
                "सार", "नतीजा", "क्या मिला", "समझा", "ಸಾರಾಂಶ", "ಫಲಿತಾಂಶ", "ಏನು ಕಂಡು", "ವಿವರಿಸ", "સાર", "પરિણામ", "શું મળ્યું", "સમજાવ",
                "சுருக்கம்", "முடிவு", "என்ன கண்டறி", "விளக்க", "సారాంశం", "ఫలితం", "ఏమి కనుగొన", "వివరించ"],
}
# Item words in each language, mapped to a test on the bill line.
ITEM_WORDS = {
    "stent": ["stent", "स्टेंट", "ಸ್ಟೆಂಟ್", "સ્ટેન્ટ", "ஸ்டென்ட்", "స్టెంట్"],
    "knee": ["knee", "implant", "घुटन", "इम्प्लांट", "ಮಂಡಿ", "ಇಂಪ್ಲಾಂಟ್", "ઘૂંટણ", "ઇમ્પ્લાન્ટ", "முழங்கால்", "இம்பிளாண்ட்", "మోకాలి", "ఇంప్లాంట్"],
    "pharmacy": ["medicine", "drug", "injection", "tablet", "दवा", "इंजेक्शन", "ಔಷಧ", "ಇಂಜೆಕ್ಷನ್", "દવા", "ઇન્જેક્શન", "மருந்து", "ஊசி",
                 "మందు", "ఇంజెక్షన్"],
    "room": ["room", "bed", "कमरा", "कमरे", "ಕೊಠಡಿ", "રૂમ", "அறை", "గది"],
}


def _has(text: str, words: list[str]) -> bool:
    t = " " + text.lower() + " "
    return any(w.lower() in t for w in words)


def detect_intent(text: str) -> str | None:
    for intent in ("next", "remedy", "coverage", "gst", "trust", "overcharge", "amber", "grey", "summary"):
        if _has(text, KEYWORDS[intent]):
            return intent
    return None


def find_lines(text: str, result: AuditResult, kb) -> list[str]:
    """Bill lines the question is about: by item words in any language, or by words of the printed name."""
    t = text.lower()
    hits = []
    for line in result.bill.lines:
        d = line.description
        if _has(t, ITEM_WORDS["stent"]) and stent_match(d, kb):
            hits.append(line.id)
        elif _has(t, ITEM_WORDS["knee"]) and knee_candidates(d):
            hits.append(line.id)
        elif _has(t, ITEM_WORDS["pharmacy"]) and line.section == "pharmacy":
            hits.append(line.id)
        elif _has(t, ITEM_WORDS["room"]) and line.section == "room":
            hits.append(line.id)
        else:
            words = [w for w in re.findall(r"[a-z]{4,}", d.lower())]
            if words and sum(w in t for w in words) >= max(1, min(2, len(words) // 2)):
                hits.append(line.id)
    return hits


def _para(key: str, lang: str, figs, slots=None, texts=None) -> list[dict]:
    return segments(msg(key, lang), slots or {}, texts or {}, figs)


def _answer_for(intent: str, result: AuditResult, lang: str, kb, line_ids: list[str] | None = None) -> list[list[dict]]:
    figs = result.figures
    reds = [f for f in result.findings if f.verdict == Verdict.RED]
    out: list[list[dict]] = []
    if intent == "line":
        for lid in line_ids or []:
            fs = [f for f in result.findings if f.line_id == lid and f.verdict != Verdict.GREEN]
            for f in sorted(fs, key=lambda f: ["red", "grey", "amber", "info", "green"].index(f.verdict.value)):
                r = render_finding(f, result, lang)
                out.append([{"t": r["title"] + ": "}] + r["text"])
            x = result.crosswalk.get(lid, {})
            for m in x.get("matches", []):
                out.append(segments(msg(m["reason"], lang), {}, m.get("text", {}), figs))
            if x.get("reason"):
                out.append(_para(x["reason"], lang, figs))
        return out or [_para("chat_line_none", lang, figs)]
    if intent == "summary":
        out = summary(result, lang) + coverage(result, lang)[:1]
    elif intent == "overcharge":
        if not reds:
            return [_para("chat_none_red", lang, figs)]
        for f in sorted(reds, key=lambda f: figs[f.excess_fig].value if f.excess_fig else 0, reverse=True)[:5]:
            r = render_finding(f, result, lang)
            out.append([{"t": r["title"] + ": "}] + r["text"])
    elif intent == "next":
        chans = load_channels(kb.dir)
        used = {f.channel.value for f in result.findings if f.verdict in (Verdict.RED, Verdict.AMBER)} - {"none"}
        used.add("hospital_desk")
        out.append(_para("chat_next_intro", lang, figs))
        for ch in ("hospital_desk", "scheme_grievance", "nppa", "consumer"):
            if ch in used or ch == "consumer":
                out.append(_para(f"chat_ch_{ch}", lang, figs, texts={"phone": str(chans.get(ch, {}).get("phone", ""))}))
    elif intent == "remedy":
        out = remedies(result, lang) + [_para("chat_remedy_explain", lang, figs)]
        if not result.recoverable_fig:
            out.insert(0, _para("chat_none_red", lang, figs))
    elif intent == "coverage":
        out = coverage(result, lang) + [_para("chat_cov_explain", lang, figs)]
        basic = [l.description for l in result.bill.lines if result.crosswalk.get(l.id, {}).get("status") == "basic"]
        if basic:
            out.append(_para("chat_cov_list", lang, figs, texts={"names": ", ".join(basic[:8])}))
    elif intent == "gst":
        out.append(_para("chat_gst", lang, figs))
        capped = next((f for f in reds + [f for f in result.findings if f.verdict == Verdict.GREEN]
                       if {"ceiling", "gst", "allowed"} <= set(f.slots)), None)
        if capped:
            out.append(_para("chat_gst_example", lang, figs,
                             {k: capped.slots[k] for k in ("ceiling", "gst", "allowed")},
                             {"item": capped.text_slots.get("item", "")}))
    elif intent == "trust":
        out.append(_para("chat_trust", lang, figs))
        srcs = []
        for f in reds:
            for s in f.source_ids:
                title = kb.source_title(s)
                if title not in srcs:
                    srcs.append(title)
        if srcs:
            out.append(_para("chat_trust_sources", lang, figs, texts={"sources": "; ".join(srcs[:4])}))
    elif intent == "amber":
        ambers = [f for f in result.findings if f.verdict == Verdict.AMBER]
        for f in ambers[:6]:
            r = render_finding(f, result, lang)
            out.append([{"t": r["title"] + ": "}] + r["text"])
        out = out or [_para("chat_amber_none", lang, figs)]
    elif intent == "grey":
        greys = [f for f in result.findings if f.verdict == Verdict.GREY]
        for f in greys[:6]:
            r = render_finding(f, result, lang)
            out.append([{"t": r["title"] + ": "}] + r["text"] + [{"t": " " + a} for a in r["asks"][:1]])
        out = out or [_para("chat_grey_none", lang, figs)]
    return out


def suggestions(result: AuditResult, lang: str) -> list[dict]:
    out = [{"id": i, "label": msg(f"chat_q_{i}", lang)} for i in ("summary", "overcharge", "next", "remedy", "coverage", "gst", "trust")]
    reds = [f for f in result.findings if f.verdict == Verdict.RED and f.line_id]
    seen = set()
    for f in sorted(reds, key=lambda f: result.figures[f.excess_fig].value, reverse=True):
        if f.line_id in seen:
            continue
        seen.add(f.line_id)
        line = next(l for l in result.bill.lines if l.id == f.line_id)
        out.append({"id": f"line:{f.line_id}", "label": msg("chat_q_line", lang).format(item=line.description)})
        if len(seen) == 3:
            break
    return out


def _slot_text(paras: list[list[dict]], figs) -> tuple[str, dict, list[str]]:
    """The answer as text with [role:F12] slots, the figures offered, and those that must stay."""
    offered, text = {}, []
    for p in paras:
        t = ""
        for s in p:
            if "fig" in s:
                f = figs[s["fig"]]
                offered[s["fig"]] = f
                t += f"[{f.role.value}:{s['fig']}]"
            else:
                t += s["t"]
        text.append(t)
    must = [fid for fid, f in offered.items() if f.role.value in ("excess", "total")][:3]
    return "\n".join(text), offered, must


PROMPT = """You help a patient's family understand their hospital bill check, in {language}.
Rewrite the ANSWER below so it replies to the QUESTION in short, plain sentences a person with
little schooling can follow. Rules you must follow:
- Use only facts in the ANSWER. Add nothing: no new findings, laws, advice or reassurance.
- Never write a number, digit or amount yourself, in any script or in words.
- To mention an amount, copy its slot token exactly, for example [excess:F31]. Keep every slot listed under MUST.
- No medical or legal advice. At most six sentences.
QUESTION: {question}
ANSWER:
{answer}
MUST: {must}
"""


def reply(result: AuditResult, message: str | None, lang: str, kb, intent: str | None = None,
          ai: bool = True, llm=_ollama) -> dict:
    """Answer one chat turn. `intent` comes from a suggestion chip; otherwise it is read from the message."""
    figs = result.figures
    text, _ = mask_pii(message or "")
    if text.strip() and lang == "en":
        guess = detect_language(text, "en")
        lang = guess if guess in LANGS else lang
    line_ids: list[str] = []
    if intent and intent.startswith("line:"):
        line_ids, intent = [intent.split(":", 1)[1]], "line"
    elif not intent:
        kind = refusal_kind(text)
        if kind:
            paras = [_para(f"chat_refuse_{kind}", lang, figs)]
            return _pack(result, lang, "refused", paras, "rules", text)
        line_ids = find_lines(text, result, kb)
        detected = detect_intent(text)
        if line_ids and detected in (None, "overcharge", "summary", "trust"):
            intent = "line"
        else:
            intent = detected
    if intent not in INTENTS + ("line",):
        return _pack(result, lang, "help", [_para("chat_help", lang, figs)], "rules", text)
    paras = _answer_for(intent, result, lang, kb, line_ids)
    source = "rules"
    if ai and llm and text.strip() and intent not in ("next",):   # offices and phone numbers are never reworded
        answer, offered, must = _slot_text(paras, figs)
        prompt = PROMPT.format(language={"en": "English", "hi": "Hindi", "kn": "Kannada", "gu": "Gujarati",
                                         "ta": "Tamil", "te": "Telugu"}[lang], question=text, answer=answer,
                               must=", ".join(f"[{figs[m].role.value}:{m}]" for m in must) or "none")
        for _ in range(2):
            out = llm(prompt)
            if not out:
                break
            if verify(out, offered, lang, required=must).ok:
                paras = [fill(p.strip(), figs) for p in out.strip().split("\n") if p.strip()]
                source = "llm"
                break
    return _pack(result, lang, intent, paras, source, text)


def _pack(result: AuditResult, lang: str, intent: str, paras: list[list[dict]], source: str, question: str) -> dict:
    sents = [_speechify(p, result, lang) for p in paras]
    return {"lang": lang, "intent": intent, "source": source, "question": question,
            "answer": [[{k: v for k, v in s.items() if k != "say"} for s in p] for p in sents],
            "speech_lines": _speech_lines(sents, lang),
            "suggestions": suggestions(result, lang)}


def hello(result: AuditResult, lang: str) -> dict:
    return _pack(result, lang, "hello", [segments(msg("chat_hello", lang), {}, {}, result.figures)], "rules", "")
