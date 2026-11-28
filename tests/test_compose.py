from conftest import bill

from kk.compose import explain, plain, render_finding
from kk.compose.translate import SlotsChanged, translate
from kk.compose.verifier import verify
from kk.grievance import letters
from kk.models import Verdict


def _stent(auditor):
    return auditor.audit_structured(bill([{"description": "DES stent", "qty": "1", "rate": "58000", "amount": "58000"}]),
                                    {"payer": "cash"})


def test_render_all_languages(auditor):
    s = _stent(auditor)
    [f] = [x for x in s.result.findings if x.verdict == Verdict.RED]
    for lang in ("en", "hi", "kn", "gu"):
        text = plain(render_finding(f, s.result, lang)["text"])
        assert "₹16,854.67" in text and "₹41,145.33" in text


def test_verifier(auditor):
    s = _stent(auditor)
    [f] = [x for x in s.result.findings if x.verdict == Verdict.RED]
    figs = s.result.figures
    offered = {fid: figs[fid] for fid in f.slots.values()}
    ex = f.excess_fig
    assert verify(f"You may get back [excess:{ex}].", offered, "en", required=[ex]).ok
    assert not verify("You may get back ₹16,854.", offered, "en").ok                       # digits
    assert not verify(f"You may get back [ceiling_ex_gst:{ex}].", offered, "en").ok        # wrong role
    assert not verify("You may get back [excess:F999].", offered, "en").ok                  # not offered
    assert not verify("ನಿಮಗೆ ೧೬೮೫೪ ಮರಳಿ ಸಿಗಬಹುದು", offered, "kn").ok                      # Kannada digits
    assert not verify("about fifty thousand rupees", offered, "en").ok                      # number words
    assert not verify("ನಿಮಗೆ ಸಾವಿರ ಮರಳಿ", offered, "kn").ok
    assert not verify("Everything is fine.", offered, "en", required=[ex]).ok               # omits the red finding


def test_explain_falls_back_to_template_when_llm_misbehaves(auditor):
    s = _stent(auditor)
    bad = lambda prompt: "The hospital overcharged you by ₹20,000."
    out = explain(s.result, "en", llm=bad)
    assert out["source"] == "template"
    good_fid = s.result.recoverable_fig
    ok = lambda prompt: f"The stent cost more than the legal limit. You may get back [total:{good_fid}]."
    out = explain(s.result, "en", llm=ok)
    assert out["source"] == "llm" and any(seg.get("fig") == good_fid for seg in out["segments"])


def test_translation_keeps_slots():
    assert translate("Refund [excess:F3] now", lambda t: t.replace("Refund", "Rückerstattung")) == \
        "Rückerstattung [excess:F3] now"
    try:
        translate("Refund [excess:F3]", lambda t: "Refund")
        raise AssertionError("should have failed")
    except SlotsChanged:
        pass


def test_letters_route_by_channel(auditor):
    s = auditor.audit_structured(bill([
        {"description": "DES stent", "qty": "1", "rate": "58000", "amount": "58000"},
        {"description": "Room rent", "section": "room", "qty": "6", "rate": "1000", "amount": "6000"},
    ]), {"payer": "cash"})
    out = letters(s.result, "kn", auditor.kb.dir)
    chans = {l["channel"] for l in out}
    assert chans == {"nppa", "hospital_desk"}
    nppa = next(l for l in out if l["channel"] == "nppa")
    assert "kn" in nppa["letters"] and "en" in nppa["letters"]
    assert "₹16,854.67" in nppa["letters"]["kn"]
