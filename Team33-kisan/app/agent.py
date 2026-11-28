"""Tool-calling farm advisor agent + leaf disease diagnosis."""
import base64, io, json
from PIL import Image
from .llm import client, get_models
from .tools import TOOL_FUNCS, TOOL_SCHEMAS

LANGS = {"en": "English", "hi": "Hindi", "kn": "Kannada", "te": "Telugu", "ta": "Tamil",
         "mr": "Marathi", "bn": "Bengali", "gu": "Gujarati", "pa": "Punjabi", "ml": "Malayalam"}

def system_prompt(lang: str, location: str) -> str:
    return f"""You are 'Kisan Mitra', a friendly, practical farm advisor for Indian smallholder farmers.
- ALWAYS reply in {LANGS.get(lang, 'English')} (script of that language), simple village-friendly words.
- Farmer's location: {location or 'unknown - ask once if you need it'}. When calling tools, pass this location string exactly as given (including any @lat,lon part).
- Do NOT guess live data. Call tools: get_weather (irrigation/sowing/spray timing), get_soil_health (crop & fertilizer choice), get_market_prices (when/where to sell). Pass crop names to tools in English.
- Your answer will be spoken aloud: max ~6 short sentences, no markdown, no bullet symbols, no emojis.
- Structure: 1) what the data shows 2) clear recommendation (crop / irrigate or wait / sell now or hold) 3) one safety tip.
- Use quantities in local units (acre, quintal, Rs). If market data is DEMO, say prices are approximate.
- For pesticides, recommend only label-approved products, integrated pest management first, and suggest consulting the local Krishi Vigyan Kendra for serious cases."""

_sessions: dict[str, list] = {}

async def run_agent(session_id: str, user_text: str, lang: str = "en", location: str = "") -> dict:
    hist = _sessions.setdefault(session_id, [])
    hist.append({"role": "user", "content": user_text})
    hist[:] = hist[-20:]
    msgs = [{"role": "system", "content": system_prompt(lang, location)}] + hist
    used = []
    CHAT_MODEL, _ = await get_models()
    for _ in range(5):
        resp = await client.chat.completions.create(
            model=CHAT_MODEL, messages=msgs, tools=TOOL_SCHEMAS, tool_choice="auto", temperature=0.3)
        m = resp.choices[0].message
        if not m.tool_calls:
            hist.append({"role": "assistant", "content": m.content or ""})
            return {"reply": m.content or "", "tools_used": used}
        msgs.append({"role": "assistant", "content": m.content or "",
                     "tool_calls": [{"id": t.id, "type": "function",
                                    "function": {"name": t.function.name, "arguments": t.function.arguments or "{}"}}
                                   for t in m.tool_calls]})
        for tc in m.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
                fn = TOOL_FUNCS[tc.function.name]
                result = await fn(**args)
            except Exception as e:
                args, result = {}, {"error": str(e)}
            used.append({"tool": tc.function.name, "args": args})
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)[:6000]})
    return {"reply": "Sorry, I could not complete that. Please try again.", "tools_used": used}

def _prep_image(raw: bytes) -> str:
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    img.thumbnail((768, 768))
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

async def diagnose_leaf(raw: bytes, lang: str = "en", crop_hint: str = "") -> str:
    prompt = (f"You are a plant pathologist. Look at this leaf photo{' of ' + crop_hint if crop_hint else ''}. "
              f"Reply in {LANGS.get(lang, 'English')}, plain text, max 6 short sentences: likely crop, most likely disease/pest/"
              "nutrient problem with confidence (low/medium/high), 2 low-cost organic or cultural remedies, when to see a "
              "Krishi Vigyan Kendra expert. If the image is not a plant leaf, say so.")
    _, VISION_MODEL = await get_models()
    resp = await client.chat.completions.create(
        model=VISION_MODEL, temperature=0.2,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": _prep_image(raw)}}]}])
    return resp.choices[0].message.content or ""
