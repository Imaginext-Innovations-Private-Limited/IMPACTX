from datetime import datetime, timezone
from core.event_engine import normalize_event, save_event
from core.behavior_analyzer import analyze_event
from core.response_policy import choose_response
from core.database import save_event_to_database
from ml.predict_event import predict_event
from core.geoip_worker import enqueue_geolocation


def classify_ssh_command(raw_command):
    """Convert raw SSH input into a safe, fixed classification."""
    command = str(raw_command or "").lower().strip()

    if not command:
        return None

    safe_labels = {
        "read_sensitive_file",
        "download_attempt",
        "network_request",
        "privilege_modification",
        "interactive_shell",
        "reverse_shell_attempt",
        "identity_check",
        "other_command",
    }

    if command in safe_labels:
        return command

    if command.startswith((
        "cat /etc/passwd",
        "cat /etc/shadow",
        "cat ~/.ssh/",
        "cat /root/.ssh/",
    )):
        return "read_sensitive_file"

    if command.startswith(("wget http://", "wget https://")):
        return "download_attempt"

    if command.startswith(("curl http://", "curl https://")):
        return "network_request"

    if command.startswith("chmod +s "):
        return "privilege_modification"

    if command.startswith("bash -i"):
        return "interactive_shell"

    if command.startswith(("nc -e ", "netcat -e ")):
        return "reverse_shell_attempt"

    if command.split()[0] == "whoami":
        return "identity_check"

    return "other_command"


def sanitize_ssh_details(details):
    """Keep only approved SSH metadata and safe command classifications."""
    allowed_fields = (
        "service",
        "protocol",
        "destination_port",
        "session_id",
        "cowrie_event_id",
        "cowrie_eventid",
        "sensor",
        "duration_ms",
        "original_timestamp",
    )

    safe_details = {
        key: details[key]
        for key in allowed_fields
        if key in details
    }

    raw_command = details.get("command") or details.get("input")
    safe_command = classify_ssh_command(raw_command)

    if safe_command:
        safe_details["command"] = safe_command

    return safe_details


def process_event(domain, event_type, source_ip, details=None):
    incoming_details = details or {}

    # Sanitize SSH data BEFORE analysis and storage.
    if domain == "ssh":
        incoming_details = sanitize_ssh_details(incoming_details)

    event = normalize_event(
        domain=domain,
        event_type=event_type,
        source_ip=source_ip,
        details=incoming_details
    )

    # Preserve Cowrie occurrence time separately from ingestion time.
    if domain == "ssh":
        ingested_at = datetime.now(timezone.utc).isoformat()
        event["details"]["ingested_at"] = ingested_at

        original_timestamp = incoming_details.get("original_timestamp")

        if original_timestamp:
            try:
                occurrence_time = datetime.fromisoformat(
                    str(original_timestamp).replace("Z", "+00:00")
                )

                # Only accept timestamps with an explicit timezone.
                if occurrence_time.tzinfo is not None:
                    event["timestamp"] = occurrence_time.astimezone(
                        timezone.utc
                    ).isoformat()

            except (ValueError, TypeError, OverflowError):
                pass  # Keep normalize_event's generated UTC timestamp.

    # Existing rule-based analysis remains unchanged.
    event["risk_assessment"] = analyze_event(event)
    event["response_policy"] = choose_response(
        event["risk_assessment"]
    )

    # ML shadow mode: predictions do not control responses.
    if domain == "web":
        try:
            event["ml_prediction"] = predict_event(event)
        except Exception as error:
            event["ml_prediction"] = {
                "mode": "shadow",
                "status": "error",
                "message": str(error)
            }
    else:
        event["ml_prediction"] = {
            "mode": "shadow",
            "status": "skipped",
            "reason": "Current classifier is prepared for web requests"
        }

    # Save the event and shadow prediction to JSONL.
    save_event(event)

    # Preserve the existing SQLite event storage.
    save_event_to_database(event)

    # Look up public attacker IPs asynchronously.
    try:
        enqueue_geolocation(source_ip)
    except Exception:
        pass  # Geolocation must never interrupt event processing.

    return event
