import json
import time
from pathlib import Path

from core.pipeline import process_event, sanitize_ssh_details

COWRIE_LOG = Path.home() / "cowrie/var/log/cowrie/cowrie.json"
POLL_INTERVAL = 0.5


def translate_event(raw):
    """Convert selected Cowrie events without forwarding passwords."""

    event_id = raw.get("eventid", "")

    event_types = {
        "cowrie.session.connect": "connection_attempt",
        "cowrie.session.closed": "ssh_session_closed",
        "cowrie.login.success": "cowrie.login.success",
        "cowrie.login.failed": "cowrie.login.failed",
        "cowrie.command.input": "cowrie.command.input",
    }

    event_type = event_types.get(event_id)
    source_ip = raw.get("src_ip")

    if not event_type or not source_ip:
        return None

    # Explicit allowlist: never copy the raw Cowrie record.
    details = {
        "service": "cowrie",
        "protocol": "ssh",
        "original_timestamp": raw.get("timestamp"),
        "destination_port": raw.get("dst_port", 2222),
        "session_id": raw.get("session"),
        "cowrie_event_id": event_id,
        "sensor": raw.get("sensor"),
    }

    if event_id in ("cowrie.login.success", "cowrie.login.failed"):
        details["username"] = raw.get("username", "")

    if event_id == "cowrie.command.input":
        details["command"] = raw.get("input", "")

    if event_id == "cowrie.session.closed":
        details["duration_ms"] = raw.get("duration_ms")

    # Sanitize before forwarding anything to the event pipeline.
    details = sanitize_ssh_details(details)

    return event_type, source_ip, details


def follow_cowrie_log():
    """Follow new Cowrie events and reopen the log after rotation."""

    if not COWRIE_LOG.exists():
        raise FileNotFoundError(f"Cowrie log not found: {COWRIE_LOG}")

    print(f"Following Cowrie log: {COWRIE_LOG}")
    print("Waiting for new events. Press Ctrl+C to stop.")

    log = None
    current_inode = None
    processed_events = set()

    try:
        while True:
            try:
                stat = COWRIE_LOG.stat()

                if log is None or stat.st_ino != current_inode:
                    if log is not None:
                        log.close()

                    log = COWRIE_LOG.open("r", encoding="utf-8")
                    log.seek(0, 2)
                    current_inode = stat.st_ino
                    print("Opened current Cowrie log file.")

                line = log.readline()

                if not line:
                    time.sleep(POLL_INTERVAL)
                    continue

                try:
                    raw = json.loads(line)

                    event_key = (
                        raw.get("session"),
                        raw.get("eventid"),
                        raw.get("timestamp"),
                    )

                    if event_key in processed_events:
                        continue

                    translated = translate_event(raw)

                    if translated is None:
                        continue

                    event_type, source_ip, details = translated

                    event = process_event(
                        domain="ssh",
                        event_type=event_type,
                        source_ip=source_ip,
                        details=details,
                    )

                    processed_events.add(event_key)

                    risk = event.get("risk_assessment", {})

                    print(
                        f"Cowrie event: {event_type} | "
                        f"source={source_ip} | "
                        f"risk={risk.get('risk_score')} "
                        f"({risk.get('risk_level')})"
                    )

                except (json.JSONDecodeError, ValueError) as error:
                    print(f"Skipped invalid event: {error}")

            except FileNotFoundError:
                time.sleep(POLL_INTERVAL)

    finally:
        if log is not None:
            log.close()


if __name__ == "__main__":
    try:
        follow_cowrie_log()
    except KeyboardInterrupt:
        print("\nCowrie adapter stopped.")
