"""Regression cases for explicit regional OTP disclosure, not language-wide accuracy."""
import pytest
from scamshield.engine import analyze

CASES = [
    ('ta', 'உங்கள் வங்கிக் கணக்கு முடக்கப்படும். உடனே உங்கள் OTP எண்ணை எங்களிடம் சொல்லுங்கள்.',
     'உங்கள் ஓடிபி குறியீட்டை என்னிடம் கொடுங்கள்.',
     'உங்கள் OTP எண்ணை எங்களிடம் சொல்லாதீர்கள்.', 'உங்கள் OTP 123456. யாரிடமும் சொல்லாதீர்கள்.'),
    ('ml', 'നിങ്ങളുടെ ബാങ്ക് അക്കൗണ്ട് ബ്ലോക്ക് ചെയ്യും. ഉടൻ നിങ്ങളുടെ OTP ഞങ്ങൾക്ക് നൽകുക.',
     'നിങ്ങളുടെ ഓടിപി കോഡ് എനിക്ക് തരുക.',
     'നിങ്ങളുടെ OTP ഞങ്ങൾക്ക് നൽകരുത്.', 'നിങ്ങളുടെ OTP 123456. ആരോടും പറയരുത്.'),
    ('gu', 'તમારું બેંક ખાતું બંધ થઈ જશે. તરત જ તમારો OTP અમને આપો.',
     'તમારો ઓટીપી કોડ મને કહો.',
     'તમારો OTP અમને આપો નહીં.', 'તમારો OTP 123456 છે. કોઈને આપશો નહીં.'),
    ('pa', 'ਤੁਹਾਡਾ ਬੈਂਕ ਖਾਤਾ ਬੰਦ ਹੋ ਜਾਵੇਗਾ। ਤੁਰੰਤ ਆਪਣਾ OTP ਸਾਨੂੰ ਦਿਓ।',
     'ਆਪਣਾ ਓਟੀਪੀ ਕੋਡ ਮੈਨੂੰ ਦੱਸੋ।',
     'ਆਪਣਾ OTP ਸਾਨੂੰ ਨਾ ਦਿਓ।', 'ਤੁਹਾਡਾ OTP 123456 ਹੈ। ਕਿਸੇ ਨੂੰ ਨਾ ਦਿਓ।'),
]

@pytest.mark.parametrize('lang,threat,variant,advice,notice', CASES)
def test_explicit_disclosure_high_risk(lang, threat, variant, advice, notice):
    for text in (threat, variant):
        for output in ('en', lang):
            result = analyze(text, 'upi', output)
            assert result['level'] == 'high', result
            finding = next(i for i in result['indicators'] if i['id'] == lang+'_code_request')
            assert finding['evidence'] == text[finding['start']:finding['end']]

@pytest.mark.parametrize('lang,threat,variant,advice,notice', CASES)
def test_negative_advice_and_notices_not_disclosure(lang, threat, variant, advice, notice):
    for text in (advice, notice):
        result = analyze(text, 'sms', lang)
        assert result['level'] in {'unknown', 'review', 'no_clear_signal'}, result
        assert lang+'_code_request' not in {i['id'] for i in result['indicators']}
