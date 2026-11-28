"""Tests for offline PSL registered domain parsing and identity verification."""
from scamshield.identity_verifier import parse_eml_bytes, verify_identity
from scamshield.url_classifier import registered_domain


def test_psl_registered_domain_parsing():
    assert registered_domain("netbanking.sbi.co.in") == "sbi.co.in"
    assert registered_domain("sbi.co.in.verify-login.example") == "verify-login.example"
    assert registered_domain("192.0.2.10") == "192.0.2.10"


def test_sender_domain_and_reply_to_mismatch():
    text = (
        "From: HDFC Bank Security <alerts@hdfc-security-notice.example>\n"
        "Reply-To: support@freelance-mail.example\n"
        "Subject: Mandatory account review\n\n"
        "Dear customer, please review your recent profile preferences in our portal."
    )
    res = verify_identity(text)
    ids = {i["id"] for i in res["indicators"]}
    assert "identity_sender_mismatch" in ids
    assert "identity_reply_to_mismatch" in ids
    assert res["official_domain_match"] is False
    assert res["sender_authenticated"] is False


def test_misleading_subdomain_and_deceptive_hyperlink():
    html_eml = (
        b"From: State Bank of India <notice@sbi.co.in.portal-check.example>\r\n"
        b"Subject: Account notice\r\n"
        b"Content-Type: text/html; charset=utf-8\r\n\r\n"
        b"<html><body><p>Please sign in via "
        b"<a href='https://portal-check.example/auth'>https://www.sbi.co.in/login</a>"
        b"</p><script>alert(1)</script></body></html>"
    )
    parsed = parse_eml_bytes(html_eml)
    assert "alert(1)" not in parsed["body"]
    res = verify_identity(parsed["combined_text"], email_meta=parsed)
    ids = {i["id"] for i in res["indicators"]}
    assert "identity_misleading_subdomain" in ids
    assert "identity_deceptive_hyperlink" in ids


def test_official_domain_match_never_claims_authenticated():
    eml = (
        b"From: HDFC Bank <alerts@hdfcbank.com>\r\n"
        b"Authentication-Results: mx.example; spf=pass dkim=pass dmarc=pass\r\n"
        b"Subject: Monthly statement\r\n\r\n"
        b"Your monthly statement is ready in the official app."
    )
    parsed = parse_eml_bytes(eml)
    res = verify_identity(parsed["combined_text"], email_meta=parsed)
    assert res["official_domain_match"] is True
    assert res["sender_authenticated"] is False
    assert res["authentication_headers"]["verified_independently"] is False
    assert res["authentication_headers"]["claims"] == {"spf": "pass", "dkim": "pass", "dmarc": "pass"}


def test_unknown_org_and_missing_sender_neutral():
    res = verify_identity("Hi team, let us meet at 3 PM to review the quarterly slides.")
    assert res["indicators"] == []
    assert res["claimed_organisations"] == []
    assert res["from_address"] == ""
