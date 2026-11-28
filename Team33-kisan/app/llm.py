"""Groq client with automatic model discovery (no more 'model not found')."""
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_KEY = os.getenv("GROQ_API_KEY", "").strip()
if not API_KEY:
    print("WARNING: GROQ_API_KEY is empty. Create a .env file next to requirements.txt")

client = AsyncOpenAI(api_key=API_KEY or "missing", base_url="https://api.groq.com/openai/v1")

# Preference order; first one your key can access is used.
CHAT_PREFS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
VISION_PREFS = ["qwen/qwen3.8-27b"]
SKIP = ("whisper", "tts", "guard", "orpheus", "playai", "compound", "embed")

_cache: dict = {}

async def get_models() -> tuple[str, str]:
    """Returns (chat_model, vision_model); honours GROQ_MODEL / GROQ_VISION_MODEL if available."""
    if _cache:
        return _cache["chat"], _cache["vision"]
    ids = [m.id for m in (await client.models.list()).data]
    print("Groq models available to your key:", ids)
    usable = [i for i in ids if not any(s in i.lower() for s in SKIP)]

    def pick(env, prefs, fallback):
        want = os.getenv(env, "").strip()
        for c in ([want] if want else []) + prefs:
            if c in ids:
                return c
        return fallback

    chat = pick("GROQ_MODEL", CHAT_PREFS, usable[0] if usable else "")
    # No fallback to the chat model: a text-only model rejects image requests.
    vision = pick("GROQ_VISION_MODEL", VISION_PREFS, "")
    print(f"Using chat model: {chat} | vision model: {vision or 'NONE'}")
    _cache.update(chat=chat, vision=vision)
    return chat, vision