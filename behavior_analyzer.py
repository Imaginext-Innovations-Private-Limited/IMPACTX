
from urllib.parse import unquote


def analyze_event(event):
    """Return explainable risk indicators for a normalized web event."""
    details = event.get("details", {})
    path = unquote(str(details.get("path", "/"))).lower()

    score = 0
    indicators = []

    if event.get("domain") != "web":
        return {
            "risk_score": 0,
            "risk_level": "unassessed",
            "indicators": ["No web-specific rules applied"]
        }

    if ".." in path:
        score += 30
        indicators.append("Path traversal pattern")

    if any(marker in path for marker in (
        "/.env", "/wp-admin", "/phpmyadmin"
    )):
        score += 20
        indicators.append("Sensitive or commonly probed path")

    if any(marker in path for marker in (
        "/etc/passwd", "cmd=", "union select", "<script"
    )):
        score += 30
        indicators.append("Potential injection or discovery pattern")

    score = min(score, 100)

    if score >= 60:
        level = "high"
    elif score >= 30:
        level = "medium"
    else:
        level = "low"

    return {
        "risk_score": score,
        "risk_level": level,
        "indicators": indicators or ["No configured suspicious pattern matched"]
    }
