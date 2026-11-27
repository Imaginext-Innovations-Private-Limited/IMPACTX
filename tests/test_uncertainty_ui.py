"""No-signal or unknown assessments must not look like verified safety."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_uncertainty_is_visible_before_actions_and_never_green():
    html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
    css = (ROOT / 'static/styles.css').read_text(encoding='utf-8')
    assert html.index('id="safety-note"') < html.index('id="actions"')
    assert html.index('id="coverage-note"') < html.index('id="actions"')
    assert 'id="risk-index-panel"' in html
    style = re.search(r'\.risk-badge\.no_clear_signal,\.risk-badge\.unknown\{([^}]+)\}', css)
    assert style and 'color:#ffdca0' in style.group(1)


def test_inconclusive_label_and_copy_and_meter():
    js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    assert 'data.level==="no_clear_signal"||data.level==="unknown"' in js
    assert 'data.analysis_mode==="hybrid"' in js.split('function coverageNote(data)', 1)[1].split('function render(data)', 1)[0]
    assert '$("risk-index-panel").classList.toggle("hidden",unconfirmed)' in js
    assert '$("risk-level").textContent=safetyUnconfirmed(data)?safetyLabel(data)' in js
    assert 'safetyUnconfirmed(d)?[safetyLabel(d),safetyNote(d)' in js.split('function copyReport()', 1)[1].split('\n', 1)[0]
    labels = js.split('const safetyUnconfirmedLabels=Object.freeze({', 1)[1].split('});', 1)[0]
    assert set(re.findall(r'\b([a-z]{2}):"', labels)) == {'en','hi','bn','kn','te','or','mr','ta','ml','gu','pa'}
