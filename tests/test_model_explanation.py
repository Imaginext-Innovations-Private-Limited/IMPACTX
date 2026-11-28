"""The UI must distinguish a classifier Review from literal rule evidence."""
from pathlib import Path
import pytest
from scamshield.engine import analyze

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('language', ['en', 'hi', 'bn', 'kn', 'te', 'or', 'mr'])
def test_ml_only_review_has_no_invented_evidence(language):
    result = analyze('Send your verification code to our agent to get your refund.', language=language)
    assert result['level'] == 'review'
    assert result['score'] == 2
    assert result['model_signal'] == 'suspicious_wording'
    assert result['indicators'] == []
    assert result['language'] == language


def test_explanation_has_separate_visible_region_and_copy_support():
    html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
    js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    assert 'id="model-only-note"' in html
    assert html.index('id="model-only-note"') < html.index('id="actions"')
    assert 'classList.toggle("hidden",!mlNote)' in js
    assert 'data.model_signal!=="suspicious_wording"' in js
    assert 'data.indicators.length!==0' in js
    assert 'data.analysis_mode==="hybrid"' in js
    assert 'modelOnlyNote(d)' in js.split('function copyReport()', 1)[1].split('\n', 1)[0]
