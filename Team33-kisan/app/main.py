import os, uuid
from xml.sax.saxutils import escape
import httpx
from fastapi import FastAPI, File, Form, UploadFile, Request
import logging, traceback
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .agent import run_agent, diagnose_leaf, LANGS

app = FastAPI(title="Voice-First Farm Advisor")
@app.exception_handler(Exception)
async def on_error(request: Request, exc: Exception):
    traceback.print_exc()
    hint = ""
    m = str(exc).lower()
    if "401" in m or "auth" in m or "api key" in m or "incorrect" in m:
        hint = " Check your API key and that LLM_PROVIDER matches it in .env."
    elif "404" in m or "model" in m:
        hint = " The model name may be wrong for your account; change it in .env."
    return JSONResponse({"reply": f"Server error ({type(exc).__name__}): {str(exc)[:300]}.{hint}", "tools_used": []}, status_code=500)

app.mount("/static", StaticFiles(directory="static"), name="static")

class ChatIn(BaseModel):
    message: str
    session_id: str = ""
    language: str = "en"
    location: str = ""

@app.get("/")
async def home():
    return FileResponse("static/index.html")

@app.get("/api/models")
async def models():
    from .llm import get_models
    chat, vision = await get_models()
    return {"chat_model": chat, "vision_model": vision}

@app.post("/api/chat")
async def chat(body: ChatIn):
    return await run_agent(body.session_id or str(uuid.uuid4()), body.message, body.language, body.location)

@app.post("/api/diagnose")
async def diagnose(image: UploadFile = File(...), language: str = Form("en"), crop: str = Form("")):
    return {"reply": await diagnose_leaf(await image.read(), language, crop)}

# ---------- WhatsApp (Twilio) ----------
# Users can type "lang kn" to switch language and "loc Mandya" to set location.
_wa_prefs: dict[str, dict] = {}

def _twiml(text: str) -> Response:
    return Response(f"<?xml version='1.0' encoding='UTF-8'?><Response><Message>{escape(text[:1500])}</Message></Response>",
                    media_type="application/xml")

@app.post("/whatsapp")
async def whatsapp(request: Request):
    f = await request.form()
    sender, body = f.get("From", ""), (f.get("Body") or "").strip()
    prefs = _wa_prefs.setdefault(sender, {"lang": "en", "loc": ""})
    low = body.lower()
    if low.startswith("lang "):
        code = low.split()[1]
        if code in LANGS:
            prefs["lang"] = code
            return _twiml(f"Language set to {LANGS[code]}.")
        return _twiml("Supported: " + ", ".join(f"{k}={v}" for k, v in LANGS.items()))
    if low.startswith("loc "):
        prefs["loc"] = body[4:].strip()
        return _twiml(f"Location set to {prefs['loc']}.")
    if int(f.get("NumMedia", 0) or 0) > 0 and (f.get("MediaContentType0") or "").startswith("image/"):
        auth = (os.getenv("TWILIO_ACCOUNT_SID", ""), os.getenv("TWILIO_AUTH_TOKEN", ""))
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as c:
            raw = (await c.get(f["MediaUrl0"], auth=auth)).content
        return _twiml(await diagnose_leaf(raw, prefs["lang"], body))
    if not body:
        return _twiml("Send a question, or a leaf photo. Use 'lang kn' / 'loc Mandya' to set language/location.")
    out = await run_agent(sender, body, prefs["lang"], prefs["loc"])
    return _twiml(out["reply"])
