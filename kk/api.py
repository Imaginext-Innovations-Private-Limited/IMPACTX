"""HTTP API and mobile web app.

Run: uvicorn kk.api:app --host 0.0.0.0 --port 8000
Uploaded files are processed in a temporary folder and deleted at once; sessions live in
memory only and expire after 24 hours (or immediately via DELETE).
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .compose import explain
from .grievance import letters
from .guard import detect_language, mask_pii, refusal_kind
from .matching import PackageMatcher
from .report import render_report
from .service import Auditor
from .voice import TTSUnavailable, backend as tts_backend, quality as tts_quality, synthesize

ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}
MAX_BYTES = 25 * 1024 * 1024

app = FastAPI(title="Kharcha Kavach", version="2.0.0")
auditor = Auditor()
matcher = PackageMatcher(auditor.kb)
WEB = Path(__file__).parent / "web"


class Answers(BaseModel):
    answers: dict


class Confirm(BaseModel):
    corrections: dict[str, dict] = {}
    confirmed: list[str] = []


class Ask(BaseModel):
    text: str
    language: str | None = None


def _session(sid: str):
    try:
        return auditor.get(sid)
    except KeyError:
        raise HTTPException(404, "session not found or expired")


@app.post("/api/audit")
async def audit(files: list[UploadFile] = File(...), answers: str = Form("{}"), lang: str = Form("en")):
    tmp = Path(tempfile.mkdtemp(prefix="kk_"))
    try:
        paths = []
        for i, f in enumerate(files):
            suffix = Path(f.filename or "").suffix.lower()
            if suffix not in ALLOWED:
                raise HTTPException(400, f"unsupported file type {suffix}")
            data = await f.read()
            if len(data) > MAX_BYTES:
                raise HTTPException(413, "file too large")
            p = tmp / f"{i:02d}{suffix}"
            p.write_bytes(data)
            paths.append(str(p))
        s = auditor.audit_files(paths, json.loads(answers or "{}"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return auditor.view(s, lang)


@app.post("/api/audit-structured")
def audit_structured(payload: dict, lang: str = "en"):
    s = auditor.audit_structured(payload.get("bill", payload), payload.get("answers", {}))
    return auditor.view(s, lang)


SAMPLES = {"bill1": "sample_bills/bill1_cardiac_cash.json", "bill2": "sample_bills/bill2_knee_pmjay.json",
           "medicines": "medicine_bill/medicines_cash.json", "bill6": "sample_bills/bill6_gst_on_treatment.json"}
FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


@app.post("/api/samples/{name}")
def audit_sample(name: str, lang: str = "en"):
    """One-click test bills for demos; the same constructed bills the tests use."""
    if name not in SAMPLES or not (FIXTURES / SAMPLES[name]).exists():
        raise HTTPException(404, "no such sample")
    d = json.loads((FIXTURES / SAMPLES[name]).read_text(encoding="utf-8"))
    s = auditor.audit_structured(d["bill"], d.get("answers", {}))
    return auditor.view(s, _lang(lang))


@app.get("/api/audit/{sid}")
def get_audit(sid: str, lang: str = "en"):
    return auditor.view(_session(sid), lang)


@app.post("/api/audit/{sid}/answers")
def set_answers(sid: str, body: Answers, lang: str = "en"):
    _session(sid)
    return auditor.view(auditor.set_answers(sid, body.answers), lang)


@app.post("/api/audit/{sid}/confirm")
def confirm(sid: str, body: Confirm, lang: str = "en"):
    _session(sid)
    return auditor.view(auditor.confirm(sid, body.corrections, body.confirmed), lang)


@app.get("/api/audit/{sid}/explain")
def explanation(sid: str, lang: str = "en"):
    return explain(_session(sid).result, lang)


LANGS = ("en", "hi", "kn", "gu", "ta", "te")


def _lang(lang: str) -> str:
    if lang not in LANGS:
        raise HTTPException(400, f"language must be one of {', '.join(LANGS)}")
    return lang


@app.get("/api/audit/{sid}/voice")
def voice_script(sid: str, lang: str = "en", ai: bool = True):
    """Spoken summary: sentences with captions (exact figures) and speech text (figures in words)."""
    out = dict(auditor.voice(_session(sid), _lang(lang), ai))
    out["server_audio"] = tts_backend(lang)
    out["server_quality"] = tts_quality(lang)   # natural | basic | none
    return out


def _speak(cache: dict, key, lines: list[str], lang: str, rate: float):
    if key not in cache:
        try:
            cache[key] = synthesize(lines, lang, rate)
        except TTSUnavailable as e:
            raise HTTPException(503, str(e))
    audio, media = cache[key]
    return Response(audio, media_type=media, headers={"Cache-Control": "no-store"})


@app.get("/api/audit/{sid}/voice.audio")
def voice_audio(sid: str, lang: str = "en", ai: bool = True, rate: float = 1.0):
    s = _session(sid)
    script = auditor.voice(s, _lang(lang), ai)
    return _speak(s.voice, ("audio", lang, ai, rate), script["speech_lines"], lang, rate)


class ChatTurn(BaseModel):
    message: str | None = None
    intent: str | None = None
    lang: str = "en"
    ai: bool = True


@app.get("/api/audit/{sid}/chat")
def chat_hello(sid: str, lang: str = "en"):
    from .chat import hello
    s = _session(sid)
    out = hello(s.result, _lang(lang))
    out["server_quality"] = tts_quality(lang)
    return out


@app.post("/api/audit/{sid}/chat")
def chat_turn(sid: str, body: ChatTurn):
    """One question about this bill. Answers come from its findings; see kk/chat.py."""
    from .chat import reply
    s = _session(sid)
    if body.message and len(body.message) > 500:
        raise HTTPException(400, "question too long")
    out = reply(s.result, body.message, _lang(body.lang), auditor.kb, intent=body.intent, ai=body.ai)
    s.chat.append(out)
    out["n"] = len(s.chat) - 1
    out["server_quality"] = tts_quality(out["lang"])
    return out


class GuardTry(BaseModel):
    text: str
    lang: str = "en"


GUARD_CODES = (("digit outside", "digit"), ("number word", "words"), ("currency", "currency"),
               ("was not offered", "unknown_slot"), ("has role", "wrong_role"))


@app.get("/api/audit/{sid}/guard")
def guard_example(sid: str):
    """A real slot from this bill, so the number guard can be tried live."""
    r = _session(sid).result
    fid = next((f.excess_fig for f in r.findings if f.excess_fig), None) or r.recoverable_fig
    return {"slot": f"[{r.figures[fid].role.value}:{fid}]" if fid else None}


@app.post("/api/audit/{sid}/guard")
def guard_try(sid: str, body: GuardTry):
    """Run any sentence through the same check every AI sentence must pass (kk/compose/verifier.py)."""
    from .compose.verifier import fill, verify
    if len(body.text) > 400:
        raise HTTPException(400, "text too long")
    r = _session(sid).result
    lang = _lang(body.lang)
    v = verify(body.text, r.figures, lang)
    codes = list(dict.fromkeys(c for e in v.errors for k, c in GUARD_CODES if k in e))
    return {"ok": v.ok, "codes": codes, "errors": v.errors,
            "segments": fill(body.text, r.figures) if v.ok else None}


@app.get("/api/audit/{sid}/chat/{n}/audio")
def chat_audio(sid: str, n: int, rate: float = 1.0):
    s = _session(sid)
    if not 0 <= n < len(s.chat):
        raise HTTPException(404, "no such answer")
    a = s.chat[n]
    return _speak(s.voice, ("chat", n, rate), a["speech_lines"], a["lang"], rate)


@app.get("/api/audit/{sid}/schemes")
def scheme_savings(sid: str, state: str = "", lang: str = "en"):
    """What a government scheme could have paid on this bill, for any state (kk/schemes.py).
    Awareness only: never part of the amount the family can challenge."""
    panel, proofs = auditor.schemes(_session(sid), state, _lang(lang))
    return {"schemes": panel, "proofs": proofs}


class TrackerBody(BaseModel):
    channel: str
    events: dict[str, dict] = {}
    cause_on: str | None = None
    lang: str = "en"
    today: str | None = None      # for demos and tests; normally the server's date


@app.post("/api/audit/{sid}/tracker")
def complaint_tracker(sid: str, body: TrackerBody):
    """When a reply is due, the last day to go further, and the next office (kk/tracker.py).
    The browser keeps the dates; this only computes the timeline and a calendar file."""
    try:
        panel, proofs = auditor.tracker(_session(sid), body.channel, body.events, body.cause_on,
                                        _lang(body.lang), body.today)
    except (KeyError, ValueError) as e:
        raise HTTPException(422, str(e).strip("'\""))
    return {"tracker": panel, "proofs": proofs}


@app.post("/api/audit/{sid}/tracker.ics")
def complaint_tracker_ics(sid: str, body: TrackerBody):
    panel = complaint_tracker(sid, body)["tracker"]
    return Response(panel["ics"], media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="kharcha-kavach-{body.channel}.ics"'})


class Deduction(BaseModel):
    item: str = ""
    amount: str
    reason: str = ""
    line_id: str | None = None


class InsuranceBody(BaseModel):
    deductions: list[Deduction]
    cashless: bool | None = None
    lang: str = "en"


@app.post("/api/audit/{sid}/insurance")
def insurance_check(sid: str, body: InsuranceBody):
    """Check each cut on an insurance settlement against IRDAI's standard lists (kk/insurance.py)."""
    if not body.deductions:
        raise HTTPException(422, "add at least one deduction")
    if len(body.deductions) > 100:
        raise HTTPException(422, "too many deductions")
    try:
        panel, proofs = auditor.insurance(_session(sid), [d.model_dump() for d in body.deductions],
                                          body.cashless, _lang(body.lang))
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"insurance": panel, "proofs": proofs}


@app.get("/api/states")
def states():
    from .schemes import STATES
    return [{"id": k, "name": v} for k, v in STATES]


@app.get("/api/audit/{sid}/calls")
def call_scripts(sid: str, lang: str = "en"):
    """What to say on the phone, built from this bill's findings (kk/voice/callscript.py)."""
    from .voice.callscript import build_calls
    out = build_calls(_session(sid).result, _lang(lang))
    for c in out:
        c["server_quality"] = tts_quality(c["lang"])
    return out


@app.get("/api/audit/{sid}/calls/{who}/audio")
def call_audio(sid: str, who: str, lang: str = "en", rate: float = 0.95):
    from .voice.callscript import build_calls
    s = _session(sid)
    lang = _lang(lang)
    call = next((c for c in build_calls(s.result, lang) if c["who"] == who), None)
    if not call:
        raise HTTPException(404, "no such call script")
    return _speak(s.voice, ("call", who, lang, rate), call["speech_lines"], lang, rate)


@app.get("/api/audit/{sid}/proof-card.json")
def proof_card_data(sid: str, lang: str = "en", fid: str | None = None):
    """What the proof card shows, for the browser to draw (browsers shape every Indian script)."""
    from . import proofcard
    try:
        return proofcard.card_data(auditor, _session(sid), _lang(lang), fid)
    except LookupError as e:
        raise HTTPException(404, str(e))


@app.get("/api/audit/{sid}/proof-card.png")
def proof_card(sid: str, lang: str = "en", fid: str | None = None):
    """A shareable image of one disputed line, with the official order as a QR code."""
    from . import proofcard
    try:
        png = proofcard.render(auditor, _session(sid), _lang(lang), fid)
    except LookupError as e:
        raise HTTPException(404, str(e))
    return Response(png, media_type="image/png", headers={"Cache-Control": "no-store"})


@app.get("/api/audit/{sid}/letters")
def get_letters(sid: str, lang: str = "en"):
    return letters(_session(sid).result, lang, auditor.kb.dir)


@app.get("/api/audit/{sid}/report", response_class=HTMLResponse)
def report(sid: str, lang: str = "en"):
    return render_report(auditor, _session(sid), lang)


@app.get("/api/audit/{sid}/page/{page}.png")
def page_png(sid: str, page: int):
    s = _session(sid)
    if not (1 <= page <= len(s.images)):
        raise HTTPException(404, "no such page")
    return Response(auditor.page_png(s, page), media_type="image/png")


@app.get("/api/audit/{sid}/crop/{fid}.png")
def crop(sid: str, fid: str):
    png = auditor.crop_png(_session(sid), fid)
    if png is None:
        raise HTTPException(404, "no image evidence for this figure")
    return Response(png, media_type="image/png")


@app.get("/api/audit/{sid}/line/{lid}.png")
def line_crop(sid: str, lid: str):
    png = auditor.line_crop_png(_session(sid), lid)
    if png is None:
        raise HTTPException(404, "no image for this line")
    return Response(png, media_type="image/png")


@app.delete("/api/audit/{sid}")
def delete(sid: str):
    auditor.delete(sid)
    return {"deleted": sid}


@app.post("/api/ask")
def ask(body: Ask):
    """Treatment description -> candidate packages. Medical or legal advice is refused."""
    text, _kinds = mask_pii(body.text)
    lang = body.language or detect_language(text)
    kind = refusal_kind(text)
    if kind:
        return {"refused": kind, "language": lang,
                "message": {"medical": "Please ask a doctor. This app checks prices and entitlements only.",
                            "legal": "Please contact free legal aid (your District Legal Services Authority). "
                                     "This app checks prices and entitlements only."}[kind]}
    return {"language": lang, "packages": matcher.search(text),
            "note": None if matcher.docs else "No package master is loaded yet; import HBP 2022 first."}


@app.get("/api/limits")
def limits(on: str | None = None):
    """Official limits in force on a date (default today), straight from the verified tables."""
    from datetime import date as _date
    from .money import indian_grouping
    kb = auditor.kb
    d = _date.fromisoformat(on) if on else _date.today()

    def src(row):
        sid = row.data["source_id"]
        return {"row": row.id, "title": kb.source_title(sid), "url": kb.source_url(sid), "ref": row.data["source_ref"]}

    gst = kb.gst_rate("medical_device", d)
    out = {"date": d.isoformat(),
           "gst": {"rate": str(gst.dec("rate_percent").normalize()), "source": src(gst)} if gst else None,
           "stents": [], "knee": []}
    for cat in ("stent_des", "stent_bms"):
        r = kb.stent_ceiling(cat, d)
        if r:
            out["stents"].append({"key": cat, "display": "₹" + indian_grouping(r.dec("ceiling_ex_gst")),
                                  "valid_to": r.valid_to.isoformat() if r.valid_to else None, "source": src(r)})
    for r in kb.knee_rows(d):
        out["knee"].append({"system": r.data["system"], "component": r.data["component"], "material": r.data["material"],
                            "display": "₹" + indian_grouping(r.dec("ceiling_ex_gst")),
                            "valid_to": r.valid_to.isoformat() if r.valid_to else None, "source": src(r)})
    return out


@app.get("/api/health")
def health():
    kb = auditor.kb
    return {"ok": True, "tts": {lg: tts_backend(lg) for lg in LANGS}, "languages": list(LANGS), "rows": {k: len(v) for k, v in kb.tables.items()}, "versions": kb.versions, "readiness": kb.readiness()}


app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    return (WEB / "index.html").read_text(encoding="utf-8")
