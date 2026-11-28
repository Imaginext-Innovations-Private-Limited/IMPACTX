"""Regression and contrast checks; not independent accuracy evidence."""
import pytest
from scamshield.engine import analyze
from scamshield.regional_context import regional_context_findings
from scamshield.training_data import SUSPICIOUS, BENIGN
from fastapi.testclient import TestClient
from scamshield.main import app
from benchmark.regional_audit_cases import CASES

REGIONAL = [(lang, a, b) for lang, pairs in CASES.items() if lang != 'en' for a,b in pairs]

@pytest.mark.parametrize('lang,suspicious,benign', REGIONAL)
def test_compositional_native_script_context(lang,suspicious,benign):
    findings = regional_context_findings(suspicious)
    assert findings, (lang,suspicious)
    assert not regional_context_findings(benign), (lang,benign)
    for f in findings:
        assert 0 <= f['start'] < f['end'] <= len(suspicious)
        assert suspicious[f['start']:f['end']].startswith(f['evidence'])
    assert analyze(suspicious, language='en')['level'] in {'review','caution','high'}

@pytest.mark.parametrize('message,rule,topic', [
 ('તમારી સામે પોલીસ કેસ છે. ધરપકડ ટાળવા માટે પૈસા મોકલો.','regional_context_arrest','arrest'),
 ('வேலை பெற பதிவு கட்டணமாக ரூ. 5000 செலுத்துங்கள்.','regional_context_job','generic'),
 ('നിങ്ങൾക്ക് ലോട്ടറി സമ്മാനം ലഭിച്ചു. സമ്മാനം ലഭിക്കാൻ ആദ്യം 2000 രൂപ അടയ്ക്കുക.','regional_context_prize','generic'),
 ('ਪੈਸੇ ਪ੍ਰਾਪਤ ਕਰਨ ਲਈ ਆਪਣਾ UPI PIN ਦਰਜ ਕਰੋ।','regional_context_receive_pin','upi'),
])
def test_known_misses_api(message,rule,topic):
    r=TestClient(app).post('/api/analyze',json={'text':message,'language':'en'})
    assert r.status_code==200
    d=r.json()
    assert d['level'] in {'caution','high'}
    assert rule in {i['id'] for i in d['indicators']}
    assert d['voice_context']['topic']==topic

def test_plain_payment_and_mixed_language_awareness():
    assert not regional_context_findings('ફી ભરો. આજે છેલ્લી તારીખ છે.')
    assert not regional_context_findings('પૈસા મેળવવા UPI PIN દાખલ કરો નહીં.')
    assert not regional_context_findings('Do not: પૈસા મેળવવા UPI PIN દાખલ કરો.')
    assert regional_context_findings('તમારો OTP કોઈને આપશો નહીં. ધરપકડ ટાળવા માટે પૈસા મોકલો.')

def test_release_health_and_data():
    assert len(SUSPICIOUS)==len(BENIGN)==197
    assert TestClient(app).get('/api/health').json()['training_samples']==394
