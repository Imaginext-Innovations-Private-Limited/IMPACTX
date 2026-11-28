"""Self-contained HTML audit report (prints to PDF from any browser)."""

from __future__ import annotations

import base64

from jinja2 import Environment, select_autoescape

from .compose import msg, to_html
from .grievance import letters

ENV = Environment(autoescape=select_autoescape(["html"]))

TEMPLATE = ENV.from_string("""<!DOCTYPE html>
<html lang="{{ lang }}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kharcha Kavach report {{ v.id }}</title>
<style>
 body{font-family:"Noto Sans","Noto Sans Devanagari","Noto Sans Kannada","Noto Sans Gujarati","Noto Sans Tamil","Noto Sans Telugu",system-ui,sans-serif;
      max-width:900px;margin:24px auto;padding:0 16px;color:#1f2328;line-height:1.5}
 h1{font-size:22px;margin-bottom:4px} h2{font-size:18px;margin-top:28px;border-bottom:1px solid #ddd}
 .sum{background:#f6f8fa;border-radius:8px;padding:12px 16px}
 .f{border-left:5px solid #999;padding:8px 12px;margin:10px 0;background:#fafafa;border-radius:4px}
 .red{border-color:#c62828}.amber{border-color:#ef8f00}.grey{border-color:#888}.green{border-color:#2e7d32}.info{border-color:#1565c0}
 .tag{font-size:12px;font-weight:600;padding:1px 6px;border-radius:4px;background:#eee;margin-right:6px}
 a.fig{font-weight:600;color:#0b57d0;text-decoration:none;border-bottom:1px dotted}
 .small{font-size:13px;color:#555} .proof{border:1px solid #e1e4e8;border-radius:6px;padding:8px 12px;margin:8px 0}
 .proof img{max-width:100%;border:1px solid #ccc} pre{white-space:pre-wrap;background:#f6f8fa;padding:12px;border-radius:6px}
 .page{position:relative;margin:8px 0} .page img{width:100%;display:block} .page svg{position:absolute;left:0;top:0;width:100%;height:100%}
</style></head><body>
<h1>Kharcha Kavach</h1>
<div class="small">{{ v.header.hospital_name or "" }} · {{ v.header.admission_date or "" }} → {{ v.header.discharge_date or "" }}</div>
<div class="sum">{% for s in v.summary %}<div>{{ seg(s) }}</div>{% endfor %}</div>
<p class="small">{{ msg("disclaimer") }}</p>

{% if pages %}<h2>Bill</h2>
{% for p in pages %}{% set pno = loop.index %}<div class="page"><img src="data:image/png;base64,{{ p.b64 }}" alt="page {{ loop.index }}">
<svg viewBox="0 0 {{ p.w }} {{ p.h }}" preserveAspectRatio="none">
{% for l in v.lines if l.bbox and l.bbox.page == pno %}
<rect x="{{ l.bbox.x0 }}" y="{{ l.bbox.y0 }}" width="{{ l.bbox.x1 - l.bbox.x0 }}" height="{{ l.bbox.y1 - l.bbox.y0 }}"
 fill="{{ colours[l.verdict] }}" fill-opacity="0.18" stroke="{{ colours[l.verdict] }}"/>{% endfor %}
</svg></div>{% endfor %}{% endif %}

<h2>Findings</h2>
{% for f in v.findings if f.verdict != "green" %}
<div class="f {{ f.verdict }}"><span class="tag">{{ f.verdict_label }}</span><b>{{ f.title }}</b>
 <span class="small">· {{ f.rule_id }} · {{ f.legal_label }}{% if f.line_id %} · {{ f.line_id }}{% endif %}</span>
 <div>{{ seg(f.text) }}</div>
 {% for c in f.conditions %}<div class="small">• {{ c }}</div>{% endfor %}
 {% for a in f.asks %}<div class="small">→ {{ a }}</div>{% endfor %}
 {% for b in f.basis %}<div class="small"><b>Official basis:</b> <i>{{ b.quote }}</i> ({{ b.title }}{% if b.ref %}, {{ b.ref }}{% endif %})</div>{% endfor %}
 {% if f.sources %}<div class="small">Sources: {% for s in f.sources %}<a href="{{ url(s) or '#' }}">{{ title(s) }}</a>{% if not loop.last %}; {% endif %}{% endfor %}</div>{% endif %}
</div>{% endfor %}
{% set greens = v.findings | selectattr("verdict", "equalto", "green") | list %}
{% if greens %}<details><summary>{{ greens|length }} × {{ msg("verdict_green") }}</summary>
{% for f in greens %}<div class="f green"><b>{{ f.title }}</b> <div>{{ seg(f.text) }}</div></div>{% endfor %}</details>{% endif %}

<h2>Proof of every number</h2>
{% for fid, p in v.proofs.items() %}<div class="proof" id="{{ fid }}"><b>{{ fid }} = {{ p.display }}</b>
 <span class="small">({{ p.role }}, {{ p.origin }}{% if p.confidence < 1 %}, OCR confidence {{ "%.2f"|format(p.confidence) }}{% endif %})</span>
 {% if crops.get(fid) %}<div><img src="data:image/png;base64,{{ crops[fid] }}" alt="crop"></div>{% endif %}
 {% if p.rule %}<div class="small">Rule data {{ p.rule.row }} · <a href="{{ p.rule.source_url or '#' }}">{{ p.rule.source_title }}</a> · {{ p.rule.ref }}</div>{% endif %}
 {% if p.formula %}<div class="small">{{ p.formula.text }}: {% for i in p.formula.inputs %}<a class="fig" href="#{{ i.id }}">{{ i.id }} = {{ i.display }}</a>{% if not loop.last %}, {% endif %}{% endfor %}</div>{% endif %}
 {% if p.note %}<div class="small">{{ p.note }}</div>{% endif %}
</div>{% endfor %}

{% if lets %}<h2>Letters</h2>
{% for l in lets %}<h3>{{ l.name }}</h3>
<div class="small">{% if l.phone %}Phone {{ l.phone }} · {% endif %}{% if l.url %}<a href="{{ l.url }}">{{ l.url }}</a>{% endif %}{% if l.escalation %} · Escalation: {{ l.escalation }}{% endif %}</div>
{% for lg, body in l.letters.items() %}<pre>{{ body }}</pre>{% endfor %}{% endfor %}{% endif %}

<h2>Data versions</h2><div class="small">{% for k, h in v.data_versions.items() %}{{ k }}: {{ h }}<br>{% endfor %}</div>
</body></html>""")

COLOURS = {"red": "#c62828", "amber": "#ef8f00", "grey": "#888888", "green": "#2e7d32", "info": "#1565c0"}


def render_report(auditor, session, lang: str = "en") -> str:
    from markupsafe import Markup

    v = auditor.view(session, lang)
    kb = auditor.kb
    pages = []
    for i, img in enumerate(session.images, start=1):
        pages.append({"b64": base64.b64encode(auditor.page_png(session, i)).decode(),
                      "w": img.shape[1], "h": img.shape[0]})
    crops = {fid: c for fid in v["proofs"] if (c := auditor.crop_b64(session, fid))}
    return TEMPLATE.render(
        v=v, lang=lang, pages=pages, crops=crops, colours=COLOURS,
        seg=lambda segs: Markup(to_html(segs)), msg=lambda k: msg(k, lang),
        title=kb.source_title, url=kb.source_url,
        lets=letters(session.result, lang, kb.dir))
