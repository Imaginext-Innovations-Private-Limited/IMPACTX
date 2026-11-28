
import json
from pathlib import Path

from core.pipeline import process_event, sanitize_ssh_details

PROJECT_DIR = Path(__file__).resolve().parent.parent
COWRIE_LOG = (
    Path.home() / "cowrie" / "var" / "log" / "cowrie" / "cowrie.json"
)
CHECKPOINT = PROJECT_DIR / "data" / "cowrie_checkpoint.txt"


def import_cowrie_events():
    if not COWRIE_LOG.exists():
        raise FileNotFoundError(f"Cowrie log not found: {COWRIE_LOG}")

    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)

    # Resume from the last successfully processed byte offset.
    try:
        offset = int(CHECKPOINT.read_text().strip())
    except (FileNotFoundError, ValueError):
        offset = 0

    imported = 0
    last_good_offset = offset

    with COWRIE_LOG.open("rb") as logfile:
        # If the log was rotated or truncated, start from its beginning.
        if offset > COWRIE_LOG.stat().st_size:
            offset = 0
            last_good_offset = 0

        logfile.seek(offset)

        while True:
            line = logfile.readline()
            if not line:
                break

            try:
                record = json.loads(line.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Don't checkpoint an incomplete or malformed line.
                break

            event_type = record.get("eventid", "")
            if not event_type.startswith("cowrie."):
                last_good_offset = logfile.tell()
                continue

            details = {
                "cowrie_eventid": event_type,
                "session_id": record.get("session") or record.get("session_id"),
                "protocol": record.get("protocol", "ssh"),
                "destination_port": record.get("dst_port"),
            }

            raw_command = (
                str(record.get("input") or "")
                .removeprefix("CMD: ")
                .strip()
            )

            if raw_command:
                details["command"] = raw_command

            details = sanitize_ssh_details(details)

            process_event(
                domain="ssh",
                event_type=event_type,
                source_ip=record.get("src_ip", "unknown"),
                details=details,
            )

            imported += 1
            last_good_offset = logfile.tell()

    CHECKPOINT.write_text(str(last_good_offset), encoding="utf-8")
    return imported


if __name__ == "__main__":
    count = import_cowrie_events()
    print(f"Imported {count} new Cowrie events.")
