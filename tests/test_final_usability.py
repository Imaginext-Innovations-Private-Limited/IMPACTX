from pathlib import Path
import pytest
from scamshield.engine import analyze

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('text', [
    'Send OTP WIN MONEY', 'Send OTP win cash', 'Share your OTP to claim your prize.',
    'To receive cash, provide your OTP.', 'Please give your CVV and get a bonus.',
])
def test_direct_reward_for_secret(text):
    result = analyze(text)
    assert result['level'] == 'high'
    finding = next(f for f in result['indicators'] if f['id'] == 'credential_reward_context')
    assert finding['evidence'] in text

@pytest.mark.parametrize('text', [
    'Never send OTP to win money.', 'Do not share your OTP to claim a prize.',
    'Your OTP is 123456. Do not share your OTP with anyone.',
    'Win money in our school quiz. Never share OTP.',
    'Your bank will never ask you to send OTP to win money.',
    'Claim your reward in our official app. Your OTP is for login only.',
])
def test_reward_rule_does_not_escalate_prevention(text):
    result = analyze(text)
    assert not any(f['id'] == 'credential_reward_context' for f in result['indicators'])
    assert result['level'] != 'high'


def test_new_controls_keep_single_analysis_and_local_rescue():
    html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
    js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    for control in ('tab-text', 'tab-file', 'tab-voice', 'voice-sub-mic', 'voice-sub-audio', 'language', 'image-drop', 'rescue-steps'):
        assert f'id="{control}"' in html
    assert html.count('id="analyze-btn"') == 1
    assert 'English guidance for this release' in html
    assert 'href="tel:1930"' in html
    handler = js.split('function showRescue(choice){',1)[1].split('function setupUsability',1)[0]
    assert 'fetch(' not in handler and 'localStorage' not in handler
