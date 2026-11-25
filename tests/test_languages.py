"""Behavior checks on draft multilingual support, not a language accuracy study."""
import pytest
from fastapi.testclient import TestClient
from scamshield.engine import analyze
from scamshield.main import app
from scamshield.languages import LANGUAGE_NAMES, LEVELS

client = TestClient(app)


@pytest.mark.parametrize('lang', list(LANGUAGE_NAMES))
def test_language_response_and_static_spoken_warning(lang):
    private_message = 'You are under digital arrest. Transfer ₹123456 immediately. Share OTP 987654.'
    d = analyze(private_message, 'call', lang)
    assert d['level'] == 'high'
    assert d['language'] == lang
    assert d['voice_lang'] == LANGUAGE_NAMES[lang][1]
    assert d['spoken_warning'].strip()
    assert '123456' not in d['spoken_warning']
    assert '987654' not in d['spoken_warning']
    assert 'scammer' not in d['spoken_warning'].lower()
    assert d['actions'] and d['title'] and d['summary']
    assert all(item['explanation'] for item in d['indicators'])


@pytest.mark.parametrize('lang', list(LANGUAGE_NAMES))
def test_response_language_does_not_change_detection_result(lang):
    text = 'You are under digital arrest. Transfer money immediately to avoid arrest.'
    baseline = analyze(text, 'sms', 'en')
    chosen = analyze(text, 'sms', lang)
    assert chosen['score'] == baseline['score']
    assert chosen['level'] == baseline['level']
    assert {s['id'] for s in chosen['indicators']} == {s['id'] for s in baseline['indicators']}


@pytest.mark.parametrize('language,text', [
    ('bn', 'আপনাকে ডিজিটাল অ্যারেস্ট করা হয়েছে। এখনই টাকা পাঠান, না হলে গ্রেফতার করা হবে।'),
    ('kn', 'ನಿಮ್ಮನ್ನು ಡಿಜಿಟಲ್ ಅರೆಸ್ಟ್ ಮಾಡಲಾಗಿದೆ. ತಕ್ಷಣ ಹಣ ಕಳುಹಿಸಿ. ಇಲ್ಲದಿದ್ದರೆ ಬಂಧಿಸಲಾಗುತ್ತದೆ.'),
    ('te', 'మీపై డిజిటల్ అరెస్ట్ ఉంది. వెంటనే డబ్బులు పంపండి, లేకపోతే అరెస్టు చేస్తాం.'),
    ('or', 'ଆପଣଙ୍କୁ ଡିଜିଟାଲ ଆରେଷ୍ଟ କରାଯାଇଛି। ତୁରନ୍ତ ଟଙ୍କା ପଠାନ୍ତୁ, ନହେଲେ ଗିରଫ କରିବା।'),
])
def test_regional_arrest_and_money_pressure(language, text):
    result = analyze(text, 'message', language)
    assert result['level'] == 'high', result
    assert 'regional_arrest' in {i['id'] for i in result['indicators']}
    assert 'regional_payment' in {i['id'] for i in result['indicators']}


@pytest.mark.parametrize('language,text', [
    ('bn', 'আপনার ওটিপি 123456, কাউকে বলবেন না।'),
    ('kn', 'ನಿಮ್ಮ ಓಟಿಪಿ 123456. ಯಾರಿಗೂ ಹೇಳಬೇಡಿ.'),
    ('te', 'మీ ఓటీపీ 123456. ఎవరికీ చెప్పవద్దు.'),
    ('or', 'ଆପଣଙ୍କ ଓଟିପି 123456। କାହାକୁ କୁହନ୍ତୁ ନାହିଁ।'),
])
def test_regional_otp_notice_is_not_labeled_high_risk(language, text):
    result = analyze(text, 'sms', language)
    assert result['level'] in {'unknown','no_clear_signal','review'}
    assert not any(s['id'] == 'regional_credential' for s in result['indicators'])


def test_api_voice_prompt_catalog_matches_supported_languages():
    result = client.get('/api/voice-prompts')
    assert result.status_code == 200
    assert set(result.json()) == set(LANGUAGE_NAMES)
    for scripts in result.json().values():
        assert set(scripts) == set(LEVELS)
        assert all(scripts.values())


def test_v12_ui_preserves_core_workflow_and_has_voice_controls():
    html = client.get('/').text
    for key in ['id="message"', 'id="analyze-btn"', 'id="results"', 'id="listen-warning"', 'id="stop-warning"']:
        assert key in html
    for lang in LANGUAGE_NAMES:
        assert f'value="{lang}"' in html
    assert client.get('/static/voice-studio.html').status_code == 200


@pytest.mark.parametrize('language', list(LANGUAGE_NAMES))
def test_api_analysis_accepts_languages(language):
    result = client.post('/api/analyze', json={
        'text': 'Enter your UPI PIN to receive your cashback refund immediately.',
        'language': language, 'channel': 'upi'
    })
    assert result.status_code == 200
    assert result.json()['language'] == language


@pytest.mark.parametrize('language', list(LANGUAGE_NAMES))
def test_distinct_arrest_indicator_reasons_in_every_language(language):
    msg = ('I am a CBI officer. Your Aadhaar is linked to money laundering. '
           'You are under digital arrest. Transfer ₹25,000 immediately to avoid arrest.')
    response = analyze(msg, 'sms', language)
    assert response['level'] == 'high'
    by_id = {item['id']: item for item in response['indicators']}
    assert {'arrest', 'authority', 'legal_threat', 'pay', 'urgency'} <= by_id.keys()
    assert len({by_id[r]['title'] for r in ['arrest', 'authority', 'legal_threat', 'pay', 'urgency']}) == 5
    assert len({by_id[r]['explanation'] for r in ['arrest', 'authority', 'legal_threat', 'pay', 'urgency']}) == 5
    for item in by_id.values():
        assert item['evidence']
        if language != 'en':
            assert item['english_title']
            assert item['english_explanation']


def test_english_screen_displays_1930_but_speech_spells_out_digits():
    result = analyze('You are under digital arrest. Transfer ₹25,000 immediately.', 'sms', 'en')
    assert '1930' in result['display_warning']
    assert 'one nine three zero' not in result['display_warning']
    assert 'one nine three zero' in result['spoken_warning']


def test_untranslated_rules_do_not_have_all_explanations_replaced_by_generic_text():
    r = analyze('Your KYC is expired. Account will be blocked today. Click the link and share OTP now.', 'sms', 'or')
    assert len(r['indicators']) >= 2
    assert len({i['title'] for i in r['indicators']}) >= 2
    assert all(i['indicator_language'] in {'or', 'en'} for i in r['indicators'])
