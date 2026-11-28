from pathlib import Path
import re
from fastapi.testclient import TestClient
from scamshield.main import app

ROOT = Path(__file__).resolve().parents[1]


def test_one_analysis_button_and_manual_instructions():
    html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
    assert html.count('id="analyze-btn"') == 1
    assert 'id="cloud-btn"' not in html
    assert 'then click Analyze' in html


def test_only_explicit_click_starts_analysis():
    js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    assert re.findall(r'\bscan\(', js) == ['scan(', 'scan(']  # declaration and explicit request
    assert 'addEventListener("click",requestAnalysis)' in js
    assert 'setTimeout(scan' not in js
    assert 'cloud_consent:useCloud' in js
    assert 'window.confirm(' not in js
    assert 'groqConfigured===true&&$("cloud-consent").checked' in js
    assert 'id="cloud-consent" disabled' in (ROOT / 'static/index.html').read_text(encoding='utf-8')


def test_edit_invalidates_previous_result():
    js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    assert 'pendingRequest.abort();pendingRequest=null' in js
    assert 'revision!==inputRevision' in js
    assert 'addEventListener("change",readyToAnalyze)' in js
    assert 'readyToAnalyze(){invalidateAssessment()' in js


def test_health_exposes_configuration_not_secret(monkeypatch):
    client = TestClient(app)
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    assert client.get('/api/health').json()['groq_configured'] is False
    monkeypatch.setenv('GROQ_API_KEY', 'private-test-key')
    response = client.get('/api/health')
    assert response.json()['groq_configured'] is True
    assert 'private-test-key' not in response.text


def test_network_events_pause_cloud_without_automatic_analysis():
    js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    assert 'window.addEventListener("offline",networkChanged)' in js
    assert 'window.addEventListener("online",networkChanged)' in js
    assert 'choice.disabled=offline||groqConfigured!==true' in js
    assert 'choice.checked=!choice.disabled&&cloudPreference' in js
    assert 'navigator.onLine!==false&&groqConfigured===true' in js
    assert 'cloudFallback=useCloud&&data.analysis_mode==="offline_fallback"' in js
    handler = js.split('function networkChanged(){', 1)[1].split('async function scan', 1)[0]
    assert 'scan(' not in handler and 'invalidateAssessment(' not in handler
