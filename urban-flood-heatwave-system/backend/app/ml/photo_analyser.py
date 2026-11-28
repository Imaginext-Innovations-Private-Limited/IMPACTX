"""
Photo Analyser using Google Gemini Vision API.
Classifies citizen-uploaded images as flood / heatwave / normal.
"""

import base64
import httpx
from pathlib import Path
from app.core.config import settings


ANALYSIS_PROMPT = """
You are an urban disaster assessment AI. Analyse this photo reported by a citizen.

Determine:
1. Is there visible flooding? (yes/no)
2. Are there signs of extreme heat (haze, dry cracked ground, heat shimmer)? (yes/no)
3. What is the primary category? Choose ONE: flooded_road, flooded_building, waterlogged_area,
   heat_haze, dry_cracked_ground, blocked_drain, normal, other
4. Severity: low / medium / high
5. Brief description (1–2 sentences max).

Respond ONLY as valid JSON:
{
  "has_flood": true/false,
  "has_heat_indicator": true/false,
  "category": "<category>",
  "severity": "low|medium|high",
  "confidence": 0.0–1.0,
  "description": "<text>"
}
"""


async def analyse_citizen_photo(photo_path: str) -> dict:
    """
    Sends a citizen photo to Gemini Vision and returns structured analysis.
    Falls back to a placeholder response if API key is not set.
    """
    if not settings.GEMINI_API_KEY:
        return _placeholder_analysis(photo_path)

    image_data = Path(photo_path).read_bytes()
    encoded = base64.b64encode(image_data).decode("utf-8")

    payload = {
        "contents": [{
            "parts": [
                {"text": ANALYSIS_PROMPT},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": encoded,
                    }
                }
            ]
        }]
    }

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        raw = response.json()

    text = raw["candidates"][0]["content"]["parts"][0]["text"]
    # Strip markdown code fences if present
    text = text.strip().removeprefix("```json").removesuffix("```").strip()

    import json
    return json.loads(text)


def _placeholder_analysis(photo_path: str) -> dict:
    """Fallback when no Gemini API key is configured."""
    return {
        "has_flood": False,
        "has_heat_indicator": False,
        "category": "normal",
        "severity": "low",
        "confidence": 0.5,
        "description": "AI analysis unavailable – Gemini API key not configured.",
    }
