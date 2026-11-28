"""Tests for Milestone 9 consolidated 3-tab UI, file routing, and protection controls."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_consolidated_three_top_level_tabs_and_sub_options():
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    tab_ids = re.findall(r'id="(tab-[^"]+)"', html)
    assert tab_ids == ["tab-text", "tab-file", "tab-voice"]
    assert "Text &amp; Links" in html
    assert "Upload File" in html
    assert "Voice &amp; Audio" in html
    assert 'id="voice-sub-mic"' in html and "Microphone" in html
    assert 'id="voice-sub-audio"' in html and "Audio Recording" in html
    assert 'id="file-input"' in html and ".eml" in html


def test_protection_controls_independent_and_local_by_default():
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    assert "Automatic Analysis" in html
    assert "Online Protection" in html
    assert 'id="auto-protect" checked' in html
    assert 'id="cloud-consent" disabled' in html
    # Automatic analysis and online consent remain independent
    assert "scheduleAutoProtect" in js
    assert "AbortController" in js and "pendingRequest.abort()" in js
    assert "handleUploadedFile" in js and "/api/parse-email" in js and "/api/ocr" in js
    assert "modeSummary" in js
    assert "Offline intelligence" in js and "Offline fallback" in js and "Online intelligence" in js
    assert "QR" in html and ".eml" in html and "URL" in html
