
from core.behavior_analyzer import analyze_event


def check(name, event, expected_score, expected_level):
    result = analyze_event(event)
    score = result["risk_score"]
    level = result["risk_level"]

    passed = score == expected_score and level == expected_level
    print(
        f"{'PASS' if passed else 'FAIL'}: {name} | "
        f"score={score}, level={level} | "
        f"expected={expected_score}, {expected_level}"
    )
    return passed


tests = [
    ("Normal web search", {
        "domain": "web",
        "event_type": "simulated_search",
        "details": {"path": "/search", "query_keys": []},
    }, 0, "low"),

    ("Sensitive .env path", {
        "domain": "web",
        "event_type": "request",
        "details": {"path": "/.env", "query_keys": []},
    }, 20, "low"),

    ("Suspicious query key", {
        "domain": "web",
        "event_type": "request",
        "details": {"path": "/search", "query_keys": ["cmd"]},
    }, 20, "low"),

    ("Path traversal", {
        "domain": "web",
        "event_type": "request",
        "details": {"path": "/../../etc/passwd", "query_keys": []},
    }, 60, "high"),

    ("Normal SSH connection", {
        "domain": "ssh",
        "event_type": "connection_attempt",
        "details": {},
    }, 0, "low"),

    ("SSH session closed", {
        "domain": "ssh",
        "event_type": "cowrie.session.closed",
        "details": {},
    }, 0, "low"),

    ("Failed SSH login", {
        "domain": "ssh",
        "event_type": "cowrie.login.failed",
        "details": {},
    }, 30, "medium"),

    ("Successful simulated SSH login", {
        "domain": "ssh",
        "event_type": "cowrie.login.success",
        "details": {},
    }, 5, "low"),

    ("Suspicious shell command", {
        "domain": "ssh",
        "event_type": "cowrie.command.input",
        "details": {"command": "cat /etc/passwd"},
    }, 30, "medium"),

    ("Unknown domain", {
        "domain": "unknown",
        "event_type": "test",
        "details": {},
    }, 0, "unassessed"),
]


passed = 0
for name, event, expected_score, expected_level in tests:
    if check(name, event, expected_score, expected_level):
        passed += 1

print(f"\nResult: {passed}/{len(tests)} tests passed")
