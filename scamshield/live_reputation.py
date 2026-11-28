"""Optional live URL reputation lookup (Google Safe Browsing v4).

Never visits, fetches, or executes suspicious URLs.
Clearly distinguishes: threat_match, no_match, provider_error, unavailable.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

LOGGER = logging.getLogger(__name__)
GSB_ENDPOINT = "https://safebrowsing.googleapis.com/v4/threatMatches:find"


def configured() -> bool:
    return bool(
        (os.environ.get("GOOGLE_SAFE_BROWSING_API_KEY") or os.environ.get("SAFE_BROWSING_API_KEY") or "").strip()
    )


def check_urls_live(urls: list[str], timeout_seconds: float = 4.0) -> dict[str, Any]:
    """Check up to 10 URLs against Google Safe Browsing v4 when configured.

    Never claims an unlisted URL is safe.
    """
    clean_urls = [u.strip() for u in urls if isinstance(u, str) and u.strip().lower().startswith(("http://", "https://"))][:10]
    if not clean_urls:
        return {"status": "not_applicable", "matches": [], "note": "No HTTP(S) URLs to check."}

    key = (os.environ.get("GOOGLE_SAFE_BROWSING_API_KEY") or os.environ.get("SAFE_BROWSING_API_KEY") or "").strip()
    if not key:
        return {
            "status": "unavailable",
            "matches": [],
            "note": "Live URL reputation key not configured; using offline URL model and local threat database.",
        }

    payload = {
        "client": {"clientId": "scamshield-ai", "clientVersion": "2.2.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": u} for u in clean_urls],
        },
    }
    try:
        resp = httpx.post(
            GSB_ENDPOINT,
            params={"key": key},
            json=payload,
            timeout=httpx.Timeout(timeout_seconds, connect=2.0),
            follow_redirects=False,
        )
        if resp.status_code == 429:
            LOGGER.warning("Live URL reputation rate-limited (HTTP 429)")
            return {"status": "provider_error", "matches": [], "note": "Live URL reputation rate-limited (HTTP 429); local checks retained."}
        resp.raise_for_status()
        data = resp.json()
        raw_matches = data.get("matches") or []
        matches = [
            {
                "url": m.get("threat", {}).get("url", ""),
                "threat_type": m.get("threatType", "SOCIAL_ENGINEERING"),
                "provider": "Google Safe Browsing",
            }
            for m in raw_matches
            if isinstance(m, dict) and m.get("threat", {}).get("url")
        ]
        if matches:
            return {
                "status": "threat_match",
                "matches": matches,
                "note": f"Live URL reputation matched {len(matches)} threat(s) via Google Safe Browsing.",
            }
        return {
            "status": "no_match",
            "matches": [],
            "note": "Live URL reputation returned no match (absence does not guarantee safety).",
        }
    except (httpx.TimeoutException, httpx.HTTPError, ValueError) as exc:
        LOGGER.warning("Live URL reputation unavailable: %s", type(exc).__name__)
        return {
            "status": "provider_error",
            "matches": [],
            "note": "Live URL reputation check failed or timed out; local checks retained.",
        }
