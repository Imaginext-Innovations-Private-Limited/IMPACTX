from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_general_rescue_shortcut_does_not_assume_user_action():
    html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
    assert 'class="rescue-shortcut" href="#rescue">Need help staying safe? Get guidance' in html
    assert 'Already clicked, shared details or paid?' not in html
    assert 'name="rescue" value="link"' in html

def test_link_specific_guidance_is_only_in_selected_rescue_path():
    js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    guidance = js.split('const rescueGuidance=Object.freeze({', 1)[1].split('});', 1)[0]
    prevention = guidance.split('none:[', 1)[1].split('],', 1)[0]
    assert 'links' not in prevention and 'website' not in prevention
    assert 'link:["Stop using the suspicious website"' in guidance
