from datetime import datetime, timezone
from pathlib import Path
import json
import uuid

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
LOG_FILE = DATA_DIR / "events.jsonl"

DATA_DIR.mkdir(parents=True, exist_ok=True)


def normalize_event(domain, event_type, source_ip, details=None):
    if not domain or not event_type:
        raise ValueError("domain and event_type are required")

    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "event_type": event_type,
        "source_ip": source_ip,
        "details": details or {}
    }


def save_event(event):
    required = {
        "event_id", "timestamp", "domain",
        "event_type", "source_ip", "details"
    }

    if not isinstance(event, dict) or not required.issubset(event):
        raise ValueError("Invalid event structure")

    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event) + "\n")

    return event
