from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]

class LanguageOptions(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.languages = {"language": [], "input-language": []}
        self.defaults = {"language": [], "input-language": []}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "select":
            self.current = attrs.get("id")
        elif tag == "option" and self.current in self.languages:
            self.languages[self.current].append(attrs.get("value"))
            if "selected" in attrs:
                self.defaults[self.current].append(attrs.get("value"))

    def handle_endtag(self, tag):
        if tag == "select":
            self.current = None


def test_compact_language_picker_preserves_all_options():
    html = (ROOT / "static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "static/app.js").read_text(encoding="utf-8")
    parser = LanguageOptions()
    parser.feed(html)
    expected = ["bn", "en", "gu", "hi", "kn", "ml", "mr", "or", "pa", "ta", "te"]
    for options in parser.languages.values():
        assert options == expected
    assert parser.defaults == {"language": ["en"], "input-language": ["en"]}
    assert html.count('id="language"') == 1
    assert 'id="more-languages"' not in html
    assert 'id="language-buttons"' not in html
    assert 'aria-label="Response language"' in html
    assert '$("language").addEventListener("change",readyToAnalyze)' in js
    assert 'language:$("language").value' in js
    assert 'setupLanguagePicker' not in js
