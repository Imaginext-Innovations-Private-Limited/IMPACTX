"""Shareable proof card: one image a family can forward on WhatsApp.

It shows one disputed line, the billed amount, the most the rule allows, the excess, and the
official order it rests on, with a QR code that opens that order. The hospital name is masked.
Every amount on it is a figure from the store, formatted the same way as on screen.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .compose import figure_proof, fmt_figure
from .compose.render import msg
from .models import Verdict

FONTS = Path(__file__).parent / "web" / "fonts"
SCRIPT_FONT = {"hi": "NotoSansDevanagari", "kn": "NotoSansKannada", "gu": "NotoSansGujarati",
               "ta": "NotoSansTamil", "te": "NotoSansTelugu", "en": "NotoSans"}
W, H = 1080, 1350
NAVY, INK, MUTED, RED, GREEN, LINE, PAPER = "#1E2A5E", "#1E2A5E", "#5A6688", "#C0283A", "#178A5A", "#D5DCEB", "#FFFFFF"


def _font(lang: str, size: int, bold: bool = False):
    name = SCRIPT_FONT.get(lang, "NotoSans") + ("-Bold" if bold else "-Regular") + ".woff2"
    return ImageFont.truetype(str(FONTS / name), size, layout_engine=ImageFont.Layout.RAQM)


def _latin(size: int, bold: bool = False):
    return _font("en", size, bold)


def _runs(text: str):
    """Split text into (is_latin, chunk) runs so Latin letters and digits use the Latin font."""
    out = []
    for ch in text:
        lat = ord(ch) < 0x0900 or ch in "₹–—•"
        if ch == " " and out:
            lat = out[-1][0]
        if out and out[-1][0] == lat:
            out[-1][1] += ch
        else:
            out.append([lat, ch])
    return out


def _mlen(d, text, lang, size, bold=False):
    return sum(d.textlength(c, font=_latin(size, bold) if lat or lang == "en" else _font(lang, size, bold))
               for lat, c in _runs(text))


def _mtext(d, xy, text, lang, size, fill, bold=False):
    x, y = xy
    for lat, c in _runs(text):
        f = _latin(size, bold) if lat or lang == "en" else _font(lang, size, bold)
        d.text((x, y), c, font=f, fill=fill)
        x += d.textlength(c, font=f)


def _mwrap(d, text, lang, size, width, bold=False):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if _mlen(d, trial, lang, size, bold) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def mask(name: str | None) -> str:
    """'Sample Heart Hospital' -> 'S••••• H•••• H•••••' : enough to recognise, not to identify."""
    if not name:
        return "•••"
    return " ".join(w[0] + "•" * min(len(w) - 1, 6) if len(w) > 1 else w for w in name.split())


def pick_finding(result, fid: str | None = None):
    """The finding to show: the one with this excess figure, else the largest red one with an excess."""
    reds = [f for f in result.findings if f.verdict == Verdict.RED and f.excess_fig]
    if fid:
        reds = [f for f in reds if f.excess_fig == fid] or reds
    if not reds:
        return None
    return max(reds, key=lambda f: result.figures[f.excess_fig].value)


def _source(f, result, kb):
    """(title, url, ref) of the official order behind this finding."""
    for key in ("ceiling", "allowed"):
        fid = f.slots.get(key)
        if fid:
            p = figure_proof(fid, result, kb)
            if p.get("rule"):
                r = p["rule"]
                return r["source_title"], r.get("source_url"), r.get("row")
    for b in kb.basis(f.source_ids):
        return b["title"], b["url"], b.get("ref")
    sid = (f.source_ids or [None])[0]
    return (kb.source_title(sid), kb.source_url(sid), None) if sid else ("", None, None)


def _wrap(draw, text, font, width):
    """Greedy word wrap by measured width (works for every script)."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def can_shape() -> bool:
    """True when Pillow can join Indian-script letters (libraqm). Without it, server cards use English labels."""
    from PIL import features
    return bool(features.check("raqm"))


def qr_data_url(url: str) -> str | None:
    import base64
    import qrcode
    if not url:
        return None
    q = qrcode.QRCode(border=1, box_size=8, error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(url)
    q.make(fit=True)
    buf = io.BytesIO()
    q.make_image(fill_color=NAVY, back_color="white").convert("RGB").save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def card_data(auditor, session, lang: str = "en", fid: str | None = None) -> dict:
    """Everything the proof card shows: labels in the user's language, amounts as formatted figures."""
    r, kb = session.result, auditor.kb
    f = pick_finding(r, fid)
    if f is None:
        raise LookupError("no red finding with an amount on this bill")
    figs = r.figures
    line = next((l for l in session.bill.lines if l.id == f.line_id), None)
    h = session.bill.header
    rows = []
    if f.slots.get("billed"):
        rows.append({"label": msg("card_billed", lang), "value": fmt_figure(figs[f.slots["billed"]])})
    scheme = None
    if f.slots.get("allowed"):
        sub = None
        if f.slots.get("ceiling") and f.slots.get("gst"):
            sub = f"{fmt_figure(figs[f.slots['ceiling']])} + {fmt_figure(figs[f.slots['gst']])}% GST"
            if f.slots.get("qty") and figs[f.slots["qty"]].value != 1:
                sub = f"{fmt_figure(figs[f.slots['qty']])} × " + sub
        rows.append({"label": msg("card_allowed", lang), "value": fmt_figure(figs[f.slots["allowed"]]), "sub": sub})
    elif f.rule_id.startswith("ENT-"):
        scheme = msg("card_scheme", lang)
    title, url, ref = _source(f, r, kb)
    stay = None
    if h.admission_date:
        stay = h.admission_date.strftime("%d %b %Y") + (f"  –  {h.discharge_date.strftime('%d %b %Y')}" if h.discharge_date else "")
    return {
        "lang": lang, "finding": f.excess_fig, "rule_id": f.rule_id,
        "title": msg("card_title", lang),
        "hospital_label": msg("card_hospital", lang), "hospital": mask(h.hospital_name),
        "stay_label": msg("card_stay", lang), "stay": stay,
        "item": line.description if line else "",
        "rows": rows, "scheme": scheme,
        "excess_label": msg("card_claim" if f.rule_id.startswith("ENT-") else "card_excess", lang),
        "excess": fmt_figure(figs[f.excess_fig]),
        "rule_label": msg("card_rule", lang), "rule_title": title, "rule_ref": ref, "rule_url": url,
        "qr": qr_data_url(url), "scan": msg("card_scan", lang), "foot": msg("card_foot", lang),
    }


def render(auditor, session, lang: str = "en", fid: str | None = None) -> bytes:
    import qrcode

    if lang != "en" and not can_shape():
        lang = "en"     # never draw broken letters; the browser draws the card in every language
    r, kb = session.result, auditor.kb
    f = pick_finding(r, fid)
    if f is None:
        raise LookupError("no red finding with an amount on this bill")
    figs = r.figures
    line = next((l for l in session.bill.lines if l.id == f.line_id), None)
    h = session.bill.header

    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    M = 64

    # header band
    d.rectangle([0, 0, W, 170], fill=NAVY)
    d.text((M, 38), "Kharcha Kavach", font=_latin(54, True), fill="white")
    _mtext(d, (M, 108), msg("card_title", lang), lang, 32, "#C9D3F0")

    y = 210
    _mtext(d, (M, y), msg("card_hospital", lang), lang, 26, MUTED)
    d.text((M + 330, y), mask(h.hospital_name), font=_latin(30, True), fill=INK)
    y += 48
    if h.admission_date:
        stay = h.admission_date.strftime("%d %b %Y") + (f"  –  {h.discharge_date.strftime('%d %b %Y')}" if h.discharge_date else "")
        _mtext(d, (M, y), msg("card_stay", lang), lang, 26, MUTED)
        d.text((M + 330, y), stay, font=_latin(28), fill=INK)
        y += 48
    y += 18
    d.line([M, y, W - M, y], fill=LINE, width=3)
    y += 34

    # the disputed line
    item = line.description if line else ""
    for ln in _wrap(d, item, _latin(46, True), W - 2 * M)[:2]:
        d.text((M, y), ln, font=_latin(46, True), fill=INK)
        y += 62
    y += 20

    def row(label, value, colour=INK, big=False, sub=None):
        nonlocal y
        lab = _mwrap(d, label, lang, 30, W - 2 * M - 420)
        for i, ln in enumerate(lab[:2]):
            _mtext(d, (M, y + (18 if big else 6) + i * 38), ln, lang, 30, MUTED)
        vf = _latin(72 if big else 46, True)
        tw = d.textlength(value, font=vf)
        d.text((W - M - tw, y), value, font=vf, fill=colour)
        y += 100 if big else 66
        if sub:
            sf = _latin(26)
            d.text((W - M - d.textlength(sub, font=sf), y - 10), sub, font=sf, fill=MUTED)
            y += 34

    if f.slots.get("billed"):
        row(msg("card_billed", lang), fmt_figure(figs[f.slots["billed"]]))
    if f.slots.get("allowed"):
        sub = None
        if f.slots.get("ceiling") and f.slots.get("gst"):
            sub = f"{fmt_figure(figs[f.slots['ceiling']])} + {fmt_figure(figs[f.slots['gst']])}% GST"
            if f.slots.get("qty") and figs[f.slots["qty"]].value != 1:
                sub = f"{fmt_figure(figs[f.slots['qty']])} × " + sub
        row(msg("card_allowed", lang), fmt_figure(figs[f.slots["allowed"]]), sub=sub)
    elif f.rule_id.startswith("ENT-"):
        _mtext(d, (M, y), msg("card_scheme", lang), lang, 34, GREEN, bold=True)
        y += 70
    y += 6
    d.line([M, y, W - M, y], fill=LINE, width=3)
    y += 26
    label = msg("card_claim" if f.rule_id.startswith("ENT-") else "card_excess", lang)
    row(label, fmt_figure(figs[f.excess_fig]), colour=RED, big=True)

    # official order + QR, right after the amounts
    title, url, ref = _source(f, r, kb)
    y += 40
    box_top = y
    qr_size = 220
    inner = W - 2 * M - qr_size - 40
    d.rounded_rectangle([M - 16, box_top, W - M + 16, box_top + qr_size + 96], radius=22, outline=LINE, width=3)
    _mtext(d, (M + 8, box_top + 22), msg("card_rule", lang), lang, 26, NAVY, bold=True)
    ty = box_top + 66
    for ln in _wrap(d, title, _latin(27), inner)[:4]:
        d.text((M + 8, ty), ln, font=_latin(27), fill=INK)
        ty += 36
    if ref:
        for ln in _wrap(d, str(ref), _latin(23), inner)[:2]:
            d.text((M + 8, ty + 4), ln, font=_latin(23), fill=MUTED)
            ty += 30
    if url:
        q = qrcode.QRCode(border=1, box_size=8, error_correction=qrcode.constants.ERROR_CORRECT_M)
        q.add_data(url)
        q.make(fit=True)
        qi = q.make_image(fill_color=NAVY, back_color="white").convert("RGB").resize((qr_size, qr_size), Image.NEAREST)
        qx = W - M - qr_size
        im.paste(qi, (qx, box_top + 20))
        cy = box_top + qr_size + 30
        for ln in _mwrap(d, msg("card_scan", lang), lang, 19, qr_size + 20)[:2]:
            _mtext(d, (qx + qr_size / 2 - _mlen(d, ln, lang, 19) / 2, cy), ln, lang, 19, MUTED)
            cy += 24

    # footer, then trim the unused bottom
    fy = box_top + qr_size + 130
    for ln in _mwrap(d, msg("card_foot", lang), lang, 24, W - 2 * M)[:3]:
        _mtext(d, (M, fy), ln, lang, 24, MUTED)
        fy += 34

    im = im.crop((0, 0, W, min(H, int(fy) + 40)))
    out = io.BytesIO()
    im.save(out, "PNG", optimize=True)
    return out.getvalue()
