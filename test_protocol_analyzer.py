
import pytest
from core.behavior_analyzer import analyze_event


tests = [
    ("FTP normal QUIT", {
        "domain": "network",
        "event_type": "ftp_command",
        "details": {"service": "ftp_test", "command": "QUIT"},
    }, 0),

    ("FTP sensitive file access", {
        "domain": "network",
        "event_type": "ftp_command",
        "details": {
            "service": "ftp_test",
            "command": "RETR",
            "argument": "/etc/passwd",
        },
    }, 30),

    ("Telnet failed login", {
        "domain": "network",
        "event_type": "telnet_authentication_failed",
        "details": {"service": "telnet_test"},
    }, 30),

    ("SMTP normal EHLO", {
        "domain": "network",
        "event_type": "smtp_command",
        "details": {"service": "smtp_test", "command": "EHLO"},
    }, 0),

    ("SMTP enumeration", {
        "domain": "network",
        "event_type": "smtp_command",
        "details": {"service": "smtp_test", "command": "VRFY"},
    }, 20),

    ("POP3 failed login", {
        "domain": "network",
        "event_type": "pop3_authentication_failed",
        "details": {"service": "pop3_test"},
    }, 30),

    ("IMAP failed login", {
        "domain": "network",
        "event_type": "imap_authentication_failed",
        "details": {"service": "imap_test"},
    }, 30),

    ("MySQL failed authentication", {
        "domain": "network",
        "event_type": "mysql_authentication_attempt",
        "details": {
            "service": "mysql_test",
            "authentication_failed": True,
        },
    }, 30),

    ("PostgreSQL protocol rejection", {
        "domain": "network",
        "event_type": "postgres_protocol_rejected",
        "details": {"service": "postgres_test"},
    }, 20),

    ("Normal IMAP logout", {
        "domain": "network",
        "event_type": "imap_command",
        "details": {"service": "imap_test", "command": "LOGOUT"},
    }, 0),
]


@pytest.mark.parametrize(
    "name,event,expected",
    tests,
    ids=[test[0] for test in tests],
)
def test_protocol_analyzer(name, event, expected):
    result = analyze_event(event)

    assert result["risk_score"] == expected, (
        f"{name}: got {result['risk_score']}, "
        f"expected {expected}. "
        f"Indicators: {result['indicators']}"
    )
