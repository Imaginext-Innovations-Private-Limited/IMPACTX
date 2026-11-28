"""Marathi contract tests; not a native-speaker accuracy assessment."""
import base64
from pathlib import Path
import httpx
import pytest
from fastapi.testclient import TestClient
from scamshield.engine import analyze
from scamshield import voice
from scamshield.main import app

client = TestClient(app)

@pytest.mark.parametrize('message,topic', [
    ('तुम्हाला डिजिटल अटक करण्यात आली आहे. ताबडतोब पैसे पाठवा.', 'arrest'),
    ('तुमचे KYC संपले आहे. खाते बंद होईल. OTP सांगा.', 'kyc'),
    ('पैसे मिळवण्यासाठी UPI PIN टाका.', 'upi'),
    ('तुमच्या पार्सलमध्ये अवैध वस्तू आहेत. तात्काळ पैसे पाठवा.', 'courier'),
])
def test_marathi_scam_phrases(message, topic):
    d = analyze(message, language='mr')
    assert d['level'] == 'high'
    assert d['voice_context']['topic'] == topic
    assert any(x['id'].startswith('mr_') for x in d['indicators'])

@pytest.mark.parametrize('message', [
    'तुमचा OTP 123456 आहे. कोणालाही सांगू नका.',
    'महाविद्यालयाची फी शुक्रवारी भरा.',
    'OTP शेअर करा नका.',
    'पैसे मिळवण्यासाठी UPI PIN टाका नका.',
    'तुमची बैठक उद्या सकाळी दहा वाजता आहे.',
])
def test_marathi_benign_examples(message):
    assert analyze(message, language='mr')['level'] in {'review','no_clear_signal','unknown'}

def test_marathi_voice_provider_and_offline_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(voice, 'CACHE', tmp_path)
    monkeypatch.setenv('SARVAM_API_KEY','mock-key')
    audio = (Path(__file__).resolve().parents[1]/'static/voices-basic/en/high-generic.mp3').read_bytes()
    calls = []
    def mock_post(url, **kwargs):
        calls.append(kwargs)
        return httpx.Response(200, json={'audios':[base64.b64encode(audio).decode()]})
    monkeypatch.setattr(voice.httpx,'post',mock_post)
    params = {'language':'mr','level':'high','topic':'arrest'}
    assert client.post('/api/voice/generate',json=params).status_code == 200
    assert calls[0]['json']['language_code'] == 'mr-IN'
    assert calls[0]['json']['speaker'] == 'ratan'
    assert calls[0]['json']['text'] == voice.voice_text('mr','high','arrest')
    monkeypatch.delenv('SARVAM_API_KEY')
    assert client.get('/api/voice/status',params=params).json() == {'cached':True,'configured':False}
    assert client.get('/api/voice/audio',params=params).content == audio
    assert client.post('/api/voice/generate',json=params).status_code == 200
    assert len(calls) == 1

def test_marathi_both_selectors_and_studio():
    assert client.get('/').text.count('value="mr"') == 2
    assert 'value="mr"' in client.get('/static/voice-studio.html').text
    assert 'mr:"mr-IN"' in client.get('/static/app.js').text

def test_marathi_ocr_explicit_missing_language(monkeypatch):
    import io
    from PIL import Image
    import pytesseract
    monkeypatch.setattr(pytesseract, 'get_languages', lambda **k: ['eng'])
    image = io.BytesIO(); Image.new('RGB',(100,100),'white').save(image,'PNG')
    result = client.post('/api/ocr?language=mr', files={'file':('x.png',image.getvalue(),'image/png')})
    assert result.status_code == 503 and 'mar' in result.text

@pytest.mark.parametrize('topic',voice.TOPICS)
def test_marathi_high_risk_voice_scripts(topic):
    speech = voice.voice_text('mr','high',topic)
    assert speech and voice.DIGITS['mr'] in speech
    assert len(speech) < 2500
