"""Offline phishing URL classifier and local verified-threat lookup.

Uses strictly URL-surface lexical features (no network requests, no HTML/DOM
fetching). An unlisted URL is never claimed to be safe.
"""
from __future__ import annotations

import hashlib
import math
import re
import sqlite3
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack

DATA_DIR = Path(__file__).resolve().parent / "data"
MODEL_PATH = DATA_DIR / "url_model.joblib"
THREAT_DB_PATH = DATA_DIR / "verified_threats.db"

SHORTENER_DOMAINS = {
    "bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "shorturl.at",
    "rb.gy", "tiny.cc", "goo.gl", "ow.ly", "bit.do", "t.ly",
}
SUSPICIOUS_TLDS = {
    "xyz", "top", "icu", "click", "link", "online", "site", "shop", "live",
    "vip", "cfd", "sbs", "buzz", "rest", "monster", "work", "cc", "tk",
    "ml", "ga", "cf", "gq", "ru", "pw", "club", "info",
}
PHISH_KEYWORDS = (
    "login", "signin", "sign-in", "verify", "verification", "update", "kyc",
    "secure", "account", "banking", "wallet", "confirm", "password", "otp",
    "refund", "cashback", "prize", "claim", "suspend", "blocked", "unlock",
)
BRAND_TOKENS = (
    "sbi", "hdfc", "icici", "axis", "kotak", "pnb", "paytm", "phonepe",
    "gpay", "googlepay", "npci", "bhim", "upi", "irctc", "indiapost",
    "fedex", "dhl", "bluedart", "amazon", "flipkart", "uidai", "aadhaar",
    "epfo", "incometax", "rbi", "cbi", "paypal", "apple", "microsoft",
)
OFFICIAL_DOMAINS = {
    "sbi.co.in", "onlinesbi.sbi", "onlinesbi.com", "hdfcbank.com", "icicibank.com",
    "axisbank.com", "kotak.com", "pnbindia.in", "bankofbaroda.in", "canarabank.com",
    "idfcfirstbank.com", "yesbank.in", "indusind.com", "paytm.com", "phonepe.com",
    "google.com", "npci.org.in", "bhimupi.org.in", "amazon.in", "amazon.com",
    "flipkart.com", "irctc.co.in", "fedex.com", "dhl.com", "bluedart.com",
    "delhivery.com", "jio.com", "jiomart.com", "airtel.in", "whatsapp.com",
    "wa.me", "indiapost.gov.in", "indiapost.in",
}

_IPV4_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")


def normalize_url(raw_url: str) -> str:
    """Normalize a URL string for consistent hashing and feature extraction."""
    u = (raw_url or "").strip().rstrip(".,;:!?")
    if not u:
        return ""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", u):
        u = "http://" + u
    parsed = urlparse(u)
    host = (parsed.hostname or "").lower().rstrip(".")
    port = f":{parsed.port}" if parsed.port and parsed.port not in (80, 443) else ""
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme.lower()}://{host}{port}{path}{query}"


def registered_domain(host: str) -> str:
    """Best-effort eTLD+1 extraction without external PSL dependency."""
    labels = [x for x in host.lower().split(".") if x]
    if len(labels) >= 3 and labels[-2] in {"co", "com", "gov", "org", "ac", "nic", "net"} and len(labels[-1]) == 2:
        return ".".join(labels[-3:])
    if len(labels) >= 2:
        return ".".join(labels[-2:])
    return host.lower()


def is_official_host(host: str) -> bool:
    h = host.lower().rstrip(".")
    return h.endswith((".gov.in", ".nic.in")) or registered_domain(h) in OFFICIAL_DOMAINS


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text)
    n = len(text)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def extract_url_features(raw_url: str) -> tuple[str, list[float], list[str]]:
    """Extract strictly URL-surface lexical features and human-readable reasons.

    Returns (normalized_url_for_ngram, numeric_feature_vector, lexical_reasons).
    """
    norm = normalize_url(raw_url)
    parsed = urlparse(norm)
    host = (parsed.hostname or "").lower()
    path_q = (parsed.path or "") + (("?" + parsed.query) if parsed.query else "")
    surface = host + path_q

    url_len = float(len(surface))
    host_len = float(len(host))
    path_len = float(len(parsed.path or ""))
    query_len = float(len(parsed.query or ""))

    num_dots = float(surface.count("."))
    num_hyphens = float(surface.count("-"))
    num_underscores = float(surface.count("_"))
    num_slashes = float(surface.count("/"))
    num_digits = float(sum(ch.isdigit() for ch in surface))
    num_letters = float(sum(ch.isalpha() for ch in surface))
    num_params = float(parsed.query.count("&") + (1 if parsed.query else 0))
    num_at = float(raw_url.count("@"))
    num_percent = float(surface.count("%"))

    denom = max(url_len, 1.0)
    digit_ratio = num_digits / denom
    letter_ratio = num_letters / denom
    special_ratio = max(0.0, url_len - num_digits - num_letters) / denom

    is_ip = 1.0 if _IPV4_RE.match(host) else 0.0
    has_punycode = 1.0 if "xn--" in host else 0.0
    has_port = 1.0 if (parsed.port is not None and parsed.port not in (80, 443)) else 0.0
    subdomain_count = float(max(0, len([x for x in host.split(".") if x]) - 2))

    host_entropy = _shannon_entropy(host)
    url_entropy = _shannon_entropy(surface)

    tld = host.rsplit(".", 1)[-1] if "." in host else ""
    suspicious_tld = 1.0 if tld in SUSPICIOUS_TLDS else 0.0
    is_shortener = 1.0 if registered_domain(host) in SHORTENER_DOMAINS else 0.0

    official = is_official_host(host)
    host_tokens = [t for t in re.split(r"[.\-_]", host) if t]
    brand_impersonation = 0.0
    if not official:
        if any(b in t for t in host_tokens for b in BRAND_TOKENS):
            brand_impersonation = 1.0

    lower_surface = surface.lower()
    kw_hits = sum(1 for kw in PHISH_KEYWORDS if kw in lower_surface)

    feats = [
        url_len, host_len, path_len, query_len,
        num_dots, num_hyphens, num_underscores, num_slashes,
        num_digits, num_params, num_at, num_percent,
        digit_ratio, letter_ratio, special_ratio,
        is_ip, has_punycode, has_port, subdomain_count,
        host_entropy, url_entropy,
        suspicious_tld, is_shortener, brand_impersonation, float(kw_hits),
    ]

    reasons: list[str] = []
    if is_ip:
        reasons.append("raw IP address host")
    if has_punycode:
        reasons.append("punycode (xn--) domain")
    if brand_impersonation:
        reasons.append("brand keyword in non-official domain")
    if suspicious_tld:
        reasons.append(f"high-risk TLD (.{tld})")
    if is_shortener:
        reasons.append("URL shortener")
    if kw_hits >= 1:
        reasons.append("credential/verification keyword in URL")
    if num_hyphens >= 3 or subdomain_count >= 3:
        reasons.append("excessive subdomains or hyphens")

    return surface, feats, reasons


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def lookup_threat(raw_url: str, db_path: Path = THREAT_DB_PATH) -> dict[str, Any]:
    """Check if normalized URL hash exists in local verified-threat SQLite DB.

    Absence from this DB NEVER proves a URL is safe.
    """
    norm = normalize_url(raw_url)
    if not norm or not db_path.is_file():
        return {"matched": False, "source": None}
    url_hash = _sha256_hex(norm)
    # Also check http/https scheme-normalized variant for exact path match
    parsed = urlparse(norm)
    alt_scheme = "https" if parsed.scheme == "http" else "http"
    alt_norm = norm.replace(f"{parsed.scheme}://", f"{alt_scheme}://", 1)
    alt_hash = _sha256_hex(alt_norm)
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            cur = conn.execute(
                "SELECT source FROM threats WHERE url_hash IN (?, ?) LIMIT 1",
                (url_hash, alt_hash),
            )
            row = cur.fetchone()
            if row:
                return {"matched": True, "source": row[0]}
        finally:
            conn.close()
    except sqlite3.Error:
        return {"matched": False, "source": None}
    return {"matched": False, "source": None}


@lru_cache(maxsize=1)
def _load_url_bundle(model_path: str = str(MODEL_PATH)) -> dict[str, Any] | None:
    p = Path(model_path)
    if not p.is_file():
        return None
    try:
        return joblib.load(p)
    except Exception:
        return None


def classify_url(
    raw_url: str,
    model_path: Path = MODEL_PATH,
    db_path: Path = THREAT_DB_PATH,
) -> dict[str, Any]:
    """Classify a URL using local threat DB + URL-only lexical ML model."""
    norm = normalize_url(raw_url)
    parsed = urlparse(norm)
    host = (parsed.hostname or "").lower()
    official = bool(host) and is_official_host(host)

    db_hit = lookup_threat(norm, db_path=db_path)
    surface, feats, reasons = extract_url_features(norm)

    bundle = _load_url_bundle(str(model_path))
    phishing_prob: float | None = None
    if bundle is not None and surface:
        vec = bundle["vectorizer"]
        scaler = bundle["scaler"]
        clf = bundle["classifier"]
        x_ngram = vec.transform([surface])
        x_num = scaler.transform(np.array([feats], dtype=np.float32))
        x_all = hstack([x_ngram, csr_matrix(x_num)])
        phishing_prob = float(clf.predict_proba(x_all)[0][1])

    # Conservative thresholding; official domains are never ML-flagged alone
    # unless explicitly present in the verified threat DB.
    ml_flag = "none"
    if not official and phishing_prob is not None:
        if phishing_prob >= 0.85:
            ml_flag = "high"
        elif phishing_prob >= 0.65:
            ml_flag = "review"

    return {
        "url": norm,
        "host": host,
        "official_domain": official,
        "threat_db_match": db_hit["matched"],
        "threat_db_source": db_hit["source"],
        "phishing_probability": phishing_prob,
        "ml_flag": ml_flag,
        "reasons": reasons,
    }
