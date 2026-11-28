"""Beta language contract tests; translations and speech quality need human review."""
import pytest
from fastapi.testclient import TestClient
from scamshield import main, voice
from scamshield.engine import analyze

CASES = [
    ('ta', 'உங்களுக்கு டிஜிட்டல் கைது செய்யப்பட்டுள்ளது. உடனே பணம் அனுப்புங்கள்.', 'உங்கள் OTP எங்களுக்கு அனுப்புங்கள்.', 'உங்கள் OTP 123456. யாரிடமும் சொல்லாதீர்கள்.'),
    ('ml', 'നിങ്ങൾ ഡിജിറ്റൽ അറസ്റ്റ് ആണ്. ഉടൻ പണം അയയ്ക്കുക.', 'നിങ്ങളുടെ OTP ഞങ്ങൾക്ക് അയയ്ക്കുക.', 'നിങ്ങളുടെ OTP 123456. ആരോടും പറയരുത്.'),
    ('gu', 'તમારી ડિજિટલ ધરપકડ થઈ છે. તરત પૈસા મોકલો.', 'તમારો OTP અમને મોકલો.', 'તમારો OTP 123456 છે. કોઈને આપશો નહીં.'),
    ('pa', 'ਤੁਹਾਡੀ ਡਿਜੀਟਲ ਗ੍ਰਿਫਤਾਰੀ ਹੋਈ ਹੈ। ਹੁਣੇ ਪੈਸੇ ਭੇਜੋ।', 'ਆਪਣਾ OTP ਸਾਨੂੰ ਭੇਜੋ।', 'ਤੁਹਾਡਾ OTP 123456 ਹੈ। ਕਿਸੇ ਨੂੰ ਨਾ ਦਿਓ।'),
]

@pytest.mark.parametrize('lang,arrest,code,benign', CASES)
def test_new_language_scam_and_benign_contrast(lang, arrest, code, benign):
    result = analyze(arrest, language=lang)
    assert result['level'] == 'high'
    assert result['voice_context']['topic'] == 'arrest'
    assert lang+'_arrest_demand' in {i['id'] for i in result['indicators']}
    assert result['voice_context']['display'].count('1930') == 1
    assert voice.DIGITS[lang] in result['voice_context']['text']
    result = analyze(code, language=lang)
    assert result['level'] in {'caution','high'}
    assert lang+'_code_request' in {i['id'] for i in result['indicators']}
    result = analyze(benign, language=lang)
    assert result['level'] == 'no_clear_signal'
    assert not result['indicators']
    assert '123456' not in result['spoken_warning']

@pytest.mark.parametrize('lang', ['ta','ml','gu','pa'])
def test_new_language_input_and_voice_contract(monkeypatch, lang):
    client = TestClient(main.app)
    monkeypatch.setenv('SARVAM_API_KEY','test-key')
    def fake_transcribe(audio, suffix, content_type, language_code, key):
        assert language_code == lang+'-IN'
        return 'Example transcript'
    monkeypatch.setattr(main,'_sarvam_short_transcribe',fake_transcribe)
    response=client.post('/api/transcribe-audio',params={'language':lang},data={'duration_seconds':'12','consent':'true'},files={'file':('demo.mp3',b'fake recording','audio/mpeg')})
    assert response.status_code == 200
    assert response.json()['language_code'] == lang+'-IN'
    assert voice.PROVIDER_LANG[lang] == lang+'-IN'
    assert client.get('/static/voices-basic/'+lang+'/high-generic.mp3').status_code == 200
    assert client.get('/').text.count('value="'+lang+'"') >= 2
