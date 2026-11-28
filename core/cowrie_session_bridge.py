import json
import sqlite3
from datetime import datetime
from pathlib import Path

from core.adaptive_engine import evaluate_session
from core.ssh_command_classifier import classify_ssh_command
from ml.predict_ssh import predict_ssh

PROJECT_DIR = Path(__file__).resolve().parent.parent
COWRIE_LOG = Path.home() / "cowrie/var/log/cowrie/cowrie.json"
CHECKPOINT = PROJECT_DIR / "data" / "session_bridge_checkpoint.txt"
STATE_DB = PROJECT_DIR / "data" / "session_bridge.db"

BEHAVIOR_EVENTS = {
    "cowrie.login.failed",
    "cowrie.login.success",
    "cowrie.command.input",
    "cowrie.command.failed",
    "cowrie.session.file_download",
    "cowrie.session.file_download.failed",
}


def connect_db():
    STATE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(STATE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_events (
            session_id TEXT NOT NULL,
            event_json TEXT NOT NULL,
            PRIMARY KEY (session_id, event_json)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS evaluated_sessions (
            session_id TEXT PRIMARY KEY,
            evaluated_at TEXT NOT NULL
        )
    """)
    return conn

def sanitize_cowrie_event(event):
    """Keep safe metadata and redact sensitive Cowrie event content."""

    safe_fields = {
        "eventid",
        "session",
        "timestamp",
        "src_ip",
        "src_port",
        "dst_ip",
        "dst_port",
        "protocol",
        "sensor",
        "uuid",
        "input",
    }

    safe = {
        key: event[key]
        for key in safe_fields
        if key in event
    }

    # Preserve a sanitized executable token for existing ML features.
    # Store the behavior category separately for rule-based analysis.
    if "input" in safe:
        raw_command = str(safe["input"]).strip()

        first_token = raw_command.split()[0] if raw_command else ""
        first_token = first_token.replace("\\", "/").split("/")[-1]

        safe["command_token"] = "".join(
            char for char in first_token
            if char.isalnum() or char in "_.+-"
        )[:64]

        safe["input"] = classify_ssh_command(raw_command)

    return safe
def summarize_events(events):
    from collections import Counter

    command_events = [
        e for e in events
        if e.get("eventid") == "cowrie.command.input"
    ]

    # Preserve the original executable-token feature for Isolation Forest.
    # Historical records fall back to their original input field.
    commands = [
        str(e.get("command_token") or e.get("input") or "").strip()
        for e in command_events
        if str(e.get("command_token") or e.get("input") or "").strip()
    ]

    # New safe behavior categories for rule-based session analysis.
    command_categories = Counter(
        str(e.get("input")).strip()
        for e in command_events
        if e.get("input")
    )

    timestamps = []
    for event in events:
        raw_timestamp = event.get("timestamp")
        if not raw_timestamp:
            continue
        try:
            parsed = datetime.fromisoformat(
                str(raw_timestamp).replace("Z", "+00:00")
            )
            if parsed.tzinfo is not None:
                timestamps.append(parsed)
        except (ValueError, TypeError):
            continue

    duration_seconds = 0
    if len(timestamps) >= 2:
        duration_seconds = max(
            0, int((max(timestamps) - min(timestamps)).total_seconds())
        )

    return {
        "duration_seconds": duration_seconds,
        "failed_logins": sum(
            e.get("eventid") == "cowrie.login.failed" for e in events
        ),
        "successful_logins": sum(
            e.get("eventid") == "cowrie.login.success" for e in events
        ),
        "commands": len(commands),
        "failed_commands": sum(
            e.get("eventid") == "cowrie.command.failed" for e in events
        ),
        "downloads": sum(
            e.get("eventid") == "cowrie.session.file_download" for e in events
        ),
        "unique_command_count": len(set(commands)),
        "command_categories": dict(command_categories),
    }


def process_closed_sessions():
    if not COWRIE_LOG.exists():
        raise FileNotFoundError(f"Cowrie log not found: {COWRIE_LOG}")

    try:
        offset = int(CHECKPOINT.read_text().strip())
    except (FileNotFoundError, ValueError):
        offset = 0

    conn = connect_db()
    evaluated = 0
    last_good_offset = offset

    try:
        with COWRIE_LOG.open("rb") as logfile:
            size = COWRIE_LOG.stat().st_size

            if offset > size:
                raise RuntimeError(
                    "Cowrie log is smaller than the checkpoint. "
                    "Log rotation or truncation may have occurred; "
                    "preserve state and reconcile before continuing."
                )

            logfile.seek(offset)

            while True:
                line = logfile.readline()
                if not line:
                    break

                                # Do not consume an incomplete final log record.
                if not line.endswith(b"\n"):
                    break

                try:
                    event = json.loads(line.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Skip this complete malformed record safely.
                    last_good_offset = logfile.tell()
                    continue

                last_good_offset = logfile.tell()
                session_id = event.get("session")
                event_id = event.get("eventid", "")

                if not session_id:
                    continue

                if event_id in BEHAVIOR_EVENTS:
                    # Store only sanitized event metadata.
                    safe_event = sanitize_cowrie_event(event)

                    event_json = json.dumps(
                        safe_event, sort_keys=True, separators=(',', ':')
                    )
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO session_events
                        (session_id, event_json) VALUES (?, ?)
                        """,
                        (session_id, event_json),
                    )

                elif event_id == "cowrie.session.closed":
                    already_done = conn.execute(
                        "SELECT 1 FROM evaluated_sessions WHERE session_id = ?",
                        (session_id,),
                    ).fetchone()

                    if already_done:
                        continue

                    rows = conn.execute(
                        """
                        SELECT event_json FROM session_events
                        WHERE session_id = ?
                        """,
                        (session_id,),
                    ).fetchall()

                    events = [json.loads(row[0]) for row in rows]
                    
                    
                    features = summarize_events(events)

                    # Run SSH ML in shadow mode before auditing.
                    try:
                        ssh_ml = predict_ssh(features)
                    except Exception as error:
                        ssh_ml = {
                            "model": "IsolationForest",
                            "prediction": "unavailable",
                            "anomaly_score": None,
                            "mode": "shadow",
                            "is_confirmed_attack": False,
                            "status": "error",
                            "message": str(error),
                        }

                    # Include the ML prediction in the audit record.
                    result = evaluate_session(
                        features,
                        session_id=session_id,
                        ssh_ml=ssh_ml,
                    )

                    conn.execute(
                        """
                        INSERT INTO evaluated_sessions
                        (session_id, evaluated_at)
                        VALUES (?, datetime('now'))
                        """,
                        (session_id,),
                    )
                    conn.commit()

                    print(json.dumps({
                        "session_id": session_id,
                        "events": len(events),
                        "features": features,
                        "analysis": result["analysis"],
                        "adaptation": result["adaptation"],
                        "ssh_ml": ssh_ml,
                    }))
                    evaluated += 1

        conn.commit()
        CHECKPOINT.write_text(str(last_good_offset), encoding="utf-8")

    finally:
        conn.close()

    return evaluated


if __name__ == "__main__":
    count = process_closed_sessions()
    print(f"Evaluated {count} newly closed Cowrie sessions.")
