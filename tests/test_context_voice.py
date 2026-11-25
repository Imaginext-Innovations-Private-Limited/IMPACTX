import base64
from pathlib import Path
import pytest
import httpx
from fastapi.testclient import TestClient
from scamshield import voice
from scamshield.engine import analyze
from scamshield.main import app

client = TestClient(app)
EXAMPLES = {
    'arrest':'I am a CBI officer. You are under digital arrest. Transfer money immediately to avoid arrest.',
    'upi':'To receive your cashback refund, enter your UPI PIN and approve the collect request immediately.',
    'kyc':'Your bank KYC has expired. Account will be suspended today. Click the link and share your OTP.',
    'courier':'Your courier parcel has been seized by customs for illegal drugs. Pay a security deposit within 30 minutes to avoid legal action.',
    'phishing':'Your SBI account login: http://sbi-kyc-update.xyz/login now immediately.',
    'remote':'Install AnyDesk and share your screen so we can verify the transaction.',
}
@pytest.mark.parametrize('lang', list(voice.LANGUAGE_NAMES))
def test_context_selection_and_privacy(lang):
    texts=set()
    for topic,message in EXAMPLES.items():
        r=analyze(message+' Private ref 984521 test-secret-only', 'message', lang)
        assert r['voice_context']['topic']==topic, (topic,r['categories'])
        assert r['voice_context']['text']==voice.voice_text(lang,r['level'],topic)
        assert 'test-secret-only' not in r['voice_context']['text']
        assert '984521' not in r['voice_context']['text']
        texts.add(r['voice_context']['text'])
    assert len(texts)==len(EXAMPLES)
    assert analyze('Normal class meeting tomorrow at ten.',language=lang)['voice_context']['topic']=='generic'

@pytest.fixture
def isolated_cache(tmp_path,monkeypatch):
    monkeypatch.setattr(voice,'CACHE',tmp_path)
    monkeypatch.delenv('SARVAM_API_KEY',raising=False)
    return tmp_path

def test_odia_provider_language_and_cached_offline(isolated_cache,monkeypatch):
    monkeypatch.setenv('SARVAM_API_KEY','mock-key')
    # Use a real bundled MP3 as response bytes; external service is mocked.
    audio=(Path(__file__).resolve().parents[1]/'static/voices-basic/en/high-generic.mp3').read_bytes()
    calls=[]
    def fake_post(url, **kw):
        calls.append(kw)
        assert url=='https://api.sarvam.ai/text-to-speech'
        return httpx.Response(200,json={'audios':[base64.b64encode(audio).decode()]})
    monkeypatch.setattr(voice.httpx,'post',fake_post)
    payload={'language':'or','level':'high','topic':'arrest'}
    assert client.get('/api/voice/status',params=payload).json()=={'cached':False,'configured':True}
    assert client.post('/api/voice/generate',json=payload).status_code==200
    assert calls[0]['json']['language_code']=='od-IN'
    assert calls[0]['json']['text']==voice.voice_text('or','high','arrest')
    assert calls[0]['headers']['api-subscription-key']=='mock-key'
    monkeypatch.delenv('SARVAM_API_KEY')
    assert client.post('/api/voice/generate',json=payload).status_code==200
    assert len(calls)==1
    r=client.get('/api/voice/audio',params=payload)
    assert r.status_code==200 and r.content==audio
    assert client.get('/api/voice/status',params=payload).json()=={'cached':True,'configured':False}

@pytest.mark.parametrize('payload',[{'language':'../../secret','level':'high','topic':'arrest'}, {'language':'en','level':'high','topic':'arbitrary'}, {'language':'en','level':'unknown','topic':'arrest'}, {'language':'en','level':'high','topic':'arrest','text':'private OTP 123456'}])
def test_only_allowlisted_voice_selection(payload,isolated_cache,monkeypatch):
    monkeypatch.setattr(voice.httpx,'post',lambda *a,**k:pytest.fail('unexpected API request'))
    assert client.post('/api/voice/generate',json=payload).status_code==422

def test_provider_failure_and_no_key(isolated_cache,monkeypatch):
    p={'language':'or','level':'high','topic':'kyc'}
    assert client.post('/api/voice/generate',json=p).status_code==503
    monkeypatch.setenv('SARVAM_API_KEY','secret')
    monkeypatch.setattr(voice.httpx,'post',lambda *a,**k:httpx.Response(401,text='secret'))
    r=client.post('/api/voice/generate',json=p)
    assert r.status_code==503 and 'secret' not in r.text
    assert client.get('/api/voice/audio',params=p).status_code==404
    assert not list(isolated_cache.rglob('*.mp3'))

@pytest.mark.parametrize('bad_audio',['not base64!',base64.b64encode(b'not audio'*100).decode()])
def test_invalid_audio_not_cached(bad_audio,isolated_cache,monkeypatch):
    monkeypatch.setenv('SARVAM_API_KEY','mock-key')
    monkeypatch.setattr(voice.httpx,'post',lambda *a,**k:httpx.Response(200,json={'audios':[bad_audio]}))
    assert client.post('/api/voice/generate',json={'language':'en','level':'high','topic':'upi'}).status_code==503
    assert not list(isolated_cache.rglob('*.mp3'))

def test_cross_site_generation_rejected(isolated_cache):
    assert client.post('/api/voice/generate',json={'language':'en','level':'high'},headers={'Origin':'https://other.example'}).status_code==403

@pytest.mark.parametrize('lang',list(voice.LANGUAGE_NAMES))
def test_helpline_written_digits_spoken_words(lang):
    r=analyze(EXAMPLES['arrest'],language=lang)['voice_context']
    assert '1930' in r['display']
    assert voice.DIGITS[lang] in r['text']

def test_ordinary_payment_and_awareness_regression():
    assert analyze('Please pay Rs 5000 for tuition by Friday.')['level'] in {'review','no_clear_signal'}
    assert analyze('Beware of digital arrest scams. Police never ask for money to avoid arrest.')['level'] in {'review','no_clear_signal'}
    assert analyze('Never share OTP. Send OTP 123456 to verify your account.')['level']=='high'

def test_ocr_language_validation():
    assert client.post('/api/ocr?language=xx',files={'file':('x.png',b'x','image/png')}).status_code==422

def test_existing_audio_served():
    # Provider-generated legacy audio is optional and intentionally gitignored.
    for lang in ('en','hi','bn','kn','te'):
        path=Path(__file__).resolve().parents[1]/f'static/voices/{lang}/high.mp3'
        response=client.get(f'/static/voices/{lang}/high.mp3')
        if path.is_file():
            assert response.status_code==200 and voice.valid_audio(response.content)
        else:
            assert response.status_code==404
        fallback=client.get(f'/static/voices-basic/{lang}/high-generic.mp3')
        assert fallback.status_code==200 and voice.valid_audio(fallback.content)

def test_input_language_and_voice_studio_link():
    html=client.get('/').text
    assert 'id="input-language"' in html and 'href="/static/voice-studio.html"' in html
