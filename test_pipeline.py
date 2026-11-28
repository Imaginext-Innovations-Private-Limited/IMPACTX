from unittest.mock import patch
from core.pipeline import process_event, classify_ssh_command


def test_ssh_command_classification():
    assert classify_ssh_command("cat /etc/passwd") == "read_sensitive_file"
    assert classify_ssh_command("wget https://example.com/a") == "download_attempt"
    assert classify_ssh_command("whoami") == "identity_check"
    assert classify_ssh_command("") is None


def test_ssh_event_sanitizes_raw_command():
    with (
        patch("core.pipeline.save_event"),
        patch("core.pipeline.save_event_to_database"),
        patch("core.pipeline.enqueue_geolocation"),
    ):
        event = process_event(
            domain="ssh",
            event_type="cowrie.command.input",
            source_ip="192.168.47.128",
            details={
                "command": "cat /etc/passwd",
                "username": "admin",
                "password": "secret",
                "service": "SSH",
                "protocol": "TCP",
            },
        )

    details = event["details"]
    assert details["command"] == "read_sensitive_file"
    assert "username" not in details
    assert "password" not in details
    assert "risk_assessment" in event
    assert "response_policy" in event
    assert event["ml_prediction"]["status"] == "skipped"


def test_web_event_has_risk_and_response():
    with (
        patch("core.pipeline.predict_event", return_value={
            "mode": "shadow",
            "status": "success",
        }),
        patch("core.pipeline.save_event"),
        patch("core.pipeline.save_event_to_database"),
        patch("core.pipeline.enqueue_geolocation"),
    ):
        event = process_event(
            domain="web",
            event_type="security_test",
            source_ip="127.0.0.1",
            details={
                "method": "GET",
                "path": "/../../etc/passwd",
                "query_keys": [],
            },
        )

    assert "risk_assessment" in event
    assert "response_policy" in event
    assert event["ml_prediction"]["status"] == "success"


def test_web_ml_failure_does_not_stop_event():
    with (
        patch("core.pipeline.predict_event", side_effect=RuntimeError("test error")),
        patch("core.pipeline.save_event"),
        patch("core.pipeline.save_event_to_database"),
        patch("core.pipeline.enqueue_geolocation"),
    ):
        event = process_event(
            domain="web",
            event_type="test",
            source_ip="127.0.0.1",
            details={"method": "GET", "path": "/"},
        )

    assert event["ml_prediction"]["status"] == "error"
    assert "risk_assessment" in event
    assert "response_policy" in event
