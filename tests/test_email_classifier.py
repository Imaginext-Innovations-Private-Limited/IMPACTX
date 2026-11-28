"""Tests for the specialized MeAJOR-trained offline email phishing classifier."""
from scamshield.email_classifier import classify_email_text
from scamshield.engine import analyze


def test_email_classifier_flags_polished_phishing_and_spares_safety_notice():
    phish = (
        "Dear Valued Client, our quarterly compliance review requires confirming your online "
        "banking preferences. Please sign in at our verification portal to avoid account restriction."
    )
    res = classify_email_text(phish)
    assert res["available"] is True
    assert res["score"] is not None
    assert res["flag"] in {"review", "caution"}

    eng = analyze(phish, channel="email", language="en")
    assert eng["level"] in {"review", "caution", "high"}

    awareness = (
        "Security awareness reminder: Our bank will never ask for your password, OTP, "
        "or UPI PIN by email or phone. Always open the official app yourself."
    )
    eng_safe = analyze(awareness, channel="email", language="en")
    assert eng_safe["level"] == "no_clear_signal"


def test_email_classifier_ignores_too_short_text():
    res = classify_email_text("Hello team")
    assert res["flag"] == "none"
