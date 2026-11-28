"""Tests for live online intelligence (Groq + Google Safe Browsing) and fallback reliability."""
import httpx

from scamshield import cloud, live_reputation


def test_live_reputation_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_SAFE_BROWSING_API_KEY", raising=False)
    monkeypatch.delenv("SAFE_BROWSING_API_KEY", raising=False)
    res = live_reputation.check_urls_live(["https://example.com/login"])
    assert res["status"] == "unavailable"
    assert res["matches"] == []


def test_live_reputation_threat_match_and_no_match(monkeypatch):
    monkeypatch.setenv("GOOGLE_SAFE_BROWSING_API_KEY", "test-gsb-key")

    class FakeResp:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError("err", request=None, response=self)

        def json(self):
            return self._payload

    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **kw: FakeResp(
            200,
            {"matches": [{"threatType": "SOCIAL_ENGINEERING", "threat": {"url": "http://evil.example/login"}}]},
        ),
    )
    hit = live_reputation.check_urls_live(["http://evil.example/login"])
    assert hit["status"] == "threat_match"
    assert hit["matches"][0]["url"] == "http://evil.example/login"

    monkeypatch.setattr(httpx, "post", lambda *a, **kw: FakeResp(200, {}))
    clean = live_reputation.check_urls_live(["https://example.org/page"])
    assert clean["status"] == "no_match"
    assert "guarantee safety" in clean["note"]


def test_live_reputation_rate_limit_and_timeout_fallback(monkeypatch):
    monkeypatch.setenv("GOOGLE_SAFE_BROWSING_API_KEY", "test-gsb-key")

    class RateLimitResp:
        status_code = 429

    monkeypatch.setattr(httpx, "post", lambda *a, **kw: RateLimitResp())
    rl = live_reputation.check_urls_live(["https://example.com"])
    assert rl["status"] == "provider_error"

    def raise_timeout(*a, **kw):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(httpx, "post", raise_timeout)
    to = live_reputation.check_urls_live(["https://example.com"])
    assert to["status"] == "provider_error"


def test_cloud_hybrid_never_suppresses_confirmed_offline_evidence(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    class FakeAssessment:
        level = "no_clear_signal"
        category = ""
        findings = []

    monkeypatch.setattr(cloud, "ask", lambda *a, **kw: FakeAssessment())
    local = {
        "level": "high",
        "language": "en",
        "score": 8,
        "categories": ["Verified phishing link"],
        "indicators": [{"id": "url_threat_db", "title": "Verified phishing", "evidence": "http://phish.example", "weight": 7}],
        "entities": {"urls": ["http://phish.example"], "phones": [], "upi_ids": []},
        "complaint": "draft",
    }
    out = cloud.hybrid("Check http://phish.example", local, "en")
    assert out["level"] == "high"
    assert any(i["id"] == "url_threat_db" for i in out["indicators"])
