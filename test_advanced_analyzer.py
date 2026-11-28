import pytest
from core.behavior_analyzer import analyze_event


@pytest.mark.parametrize(
    "name,event,expected",
    [
        (
            "SQL injection pattern",
            {
                "domain": "network",
                "event_type": "database_query",
                "details": {
                    "service": "mysql_test",
                    "payload": "SELECT * FROM users UNION SELECT password FROM accounts",
                },
            },
            30,
        ),
        (
            "DNS long query",
            {
                "domain": "network",
                "event_type": "dns_query",
                "details": {
                    "service": "dns_test",
                    "query_name": "a" * 105 + ".example.com",
                },
            },
            40,
        ),
        (
            "Normal DNS query",
            {
                "domain": "network",
                "event_type": "dns_query",
                "details": {
                    "service": "dns_test",
                    "query_name": "example.com",
                },
            },
            0,
        ),
        (
            "SMB metadata only",
            {
                "domain": "network",
                "event_type": "smb_data_received",
                "details": {
                    "service": "smb_test",
                    "bytes_received": 100,
                },
            },
            0,
        ),
        (
            "Normal FTP RETR",
            {
                "domain": "network",
                "event_type": "ftp_command",
                "details": {
                    "service": "ftp_test",
                    "command": "RETR",
                    "argument": "report.txt",
                },
            },
            0,
        ),
    ],
)
def test_advanced_analyzer(name, event, expected):
    result = analyze_event(event)
    assert result["risk_score"] == expected, (
        f"{name}: got {result['risk_score']}, expected {expected}"
    )
