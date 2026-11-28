"""Optional plain-language explanation by a local LLM (Ollama), guarded by the slot verifier.

The model sees findings as structured data with slot tokens, never raw numbers.
If its text fails verification twice, the fixed template summary is used instead.
Correctness never depends on the model: it only rephrases verified findings.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ..models import AuditResult, Verdict
from .render import msg, summary
from .verifier import fill, verify

LANG_NAMES = {"en": "English", "hi": "Hindi", "kn": "Kannada", "gu": "Gujarati", "ta": "Tamil", "te": "Telugu"}

PROMPT = """You explain a hospital bill check to a patient's family in {language}.
Write at most five short sentences in plain words. Rules you must follow:
- Never write a number, digit, amount or quantity yourself, in any script or in words.
- To mention a number, copy a slot token exactly as given, for example [excess:F31].
- Mention every slot listed under "must_mention".
- Do not add any finding, law or advice that is not in the data. No medical or legal advice.
Data (JSON):
{data}
"""


def _ollama(prompt: str) -> str | None:
    url = os.environ.get("KK_OLLAMA_URL", "http://localhost:11434") + "/api/generate"
    body = json.dumps({"model": os.environ.get("KK_OLLAMA_MODEL", "qwen2.5:7b-instruct"), "prompt": prompt,
                       "stream": False, "options": {"temperature": 0.2}}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode()).get("response")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def explain(result: AuditResult, lang: str = "en", llm=_ollama) -> dict:
    figs = result.figures
    reds = [f for f in result.findings if f.verdict == Verdict.RED]
    offered = {}
    items = []
    for f in result.findings:
        if f.verdict not in (Verdict.RED, Verdict.AMBER, Verdict.GREY):
            continue
        slots = {k: f"[{figs[v].role.value}:{v}]" for k, v in f.slots.items() if v in figs}
        for v in f.slots.values():
            if v in figs:
                offered[v] = figs[v]
        items.append({"rule": f.rule_id, "verdict": f.verdict.value,
                      "meaning": msg(f.message_key, "en"), "slots": slots, "names": f.text_slots})
    must = [f.excess_fig for f in reds if f.excess_fig]
    if result.recoverable_fig:
        offered[result.recoverable_fig] = figs[result.recoverable_fig]
        must = [result.recoverable_fig]
    data = {"findings": items, "total_slot": f"[total:{result.recoverable_fig}]" if result.recoverable_fig else None,
            "must_mention": [f"[{figs[m].role.value}:{m}]" for m in must]}
    prompt = PROMPT.format(language=LANG_NAMES.get(lang, "English"), data=json.dumps(data, ensure_ascii=False))
    errors: list[str] = []
    for _attempt in range(3):   # first try plus two retries
        text = llm(prompt) if llm else None
        if not text:
            break
        v = verify(text, offered, lang, required=must)
        if v.ok:
            return {"source": "llm", "segments": fill(text.strip(), figs)}
        errors = v.errors
        prompt += "\nYour previous answer was rejected because: " + "; ".join(errors[:3]) + ". Try again."
    segs = []
    for line in summary(result, lang):
        segs.extend(line + [{"t": " "}])
    return {"source": "template", "segments": segs, "llm_errors": errors}
