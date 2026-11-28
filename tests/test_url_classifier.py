"""Tests for offline phishing URL classifier and local verified-threat DB."""
import hashlib
import sqlite3

from scamshield.url_classifier import (
    classify_url,
    extract_url_features,
    is_official_host,
    lookup_threat,
    normalize_url,
    registered_domain,
)


def test_url_normalization_and_official_domains():
    assert normalize_url("https://SBI.CO.IN/login.") == "https://sbi.co.in/login"
    assert registered_domain("netbanking.hdfcbank.com") == "hdfcbank.com"
    assert registered_domain("onlinesbi.sbi.co.in") == "sbi.co.in"
    assert is_official_host("sbi.co.in") is True
    assert is_official_host("cybercrime.gov.in") is True
    assert is_official_host("sbi-kyc-update.xyz") is False


def test_extract_url_features_reasons():
    _, _, reasons_ip = extract_url_features("http://192.168.1.50/kyc/login")
    assert "raw IP address host" in reasons_ip
    assert "credential/verification keyword in URL" in reasons_ip

    _, _, reasons_brand = extract_url_features("https://sbi-kyc-verify.xyz/update")
    assert "brand keyword in non-official domain" in reasons_brand
    assert "high-risk TLD (.xyz)" in reasons_brand

    _, _, reasons_puny = extract_url_features("https://xn--pypal-4ve.com/signin")
    assert "punycode (xn--) domain" in reasons_puny


def test_lookup_threat_sqlite(tmp_path):
    db_path = tmp_path / "threats.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE threats (url_hash TEXT PRIMARY KEY, source TEXT NOT NULL)")
    norm = normalize_url("http://evil-phish.example/login")
    h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
    conn.execute("INSERT INTO threats (url_hash, source) VALUES (?, ?)", (h, "PhishTank"))
    conn.commit()
    conn.close()

    hit = lookup_threat("https://evil-phish.example/login", db_path=db_path)
    assert hit == {"matched": True, "source": "PhishTank"}

    miss = lookup_threat("https://unlisted-site.example/page", db_path=db_path)
    assert miss == {"matched": False, "source": None}


def test_classify_url_official_and_suspicious():
    official = classify_url("https://www.sbi.co.in/web/personal-banking")
    assert official["official_domain"] is True
    assert official["ml_flag"] == "none"

    phish = classify_url("http://sbi-kyc-update-alert.xyz/verify/otp-login?id=12345")
    assert phish["official_domain"] is False
    assert phish["phishing_probability"] is not None
    assert phish["phishing_probability"] > 0.5
    assert "brand keyword in non-official domain" in phish["reasons"]
