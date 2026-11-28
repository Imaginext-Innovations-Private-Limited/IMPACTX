
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "data/cowrie_dataset/extracted/logs"
OUTPUT = ROOT / "data/ssh_sessions.csv"

sessions = defaultdict(lambda: {
    "failed_logins": 0,
    "successful_logins": 0,
    "commands": 0,
    "failed_commands": 0,
    "downloads": 0,
    "unique_commands": set(),
    "first_seen": "",
    "last_seen": "",
})

for path in sorted(LOG_DIR.glob("cowrie.json.*")):
    print("Processing:", path.name, flush=True)

    with path.open(encoding="utf-8", errors="replace") as file:
        for line in file:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            session_id = event.get("session")
            if not session_id:
                continue

            # Include the sensor to avoid combining unrelated sessions.
            key = (str(event.get("sensor", "")), str(session_id))
            record = sessions[key]

            event_id = event.get("eventid", "")
            timestamp = str(event.get("timestamp", ""))

            if timestamp:
                if not record["first_seen"] or timestamp < record["first_seen"]:
                    record["first_seen"] = timestamp
                if timestamp > record["last_seen"]:
                    record["last_seen"] = timestamp

            if event_id == "cowrie.login.failed":
                record["failed_logins"] += 1

            elif event_id == "cowrie.login.success":
                record["successful_logins"] += 1

            elif event_id == "cowrie.command.input":
                record["commands"] += 1
                command = str(event.get("input", "")).strip()
                if command:
                    record["unique_commands"].add(command)

            elif event_id == "cowrie.command.failed":
                record["failed_commands"] += 1

            elif event_id == "cowrie.session.file_download":
                record["downloads"] += 1

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

fields = [
    "sensor", "session", "first_seen", "last_seen",
    "failed_logins", "successful_logins",
    "commands", "failed_commands",
    "downloads", "unique_command_count"
]

with OUTPUT.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()

    for (sensor, session_id), record in sessions.items():
        writer.writerow({
            "sensor": sensor,
            "session": session_id,
            "first_seen": record["first_seen"],
            "last_seen": record["last_seen"],
            "failed_logins": record["failed_logins"],
            "successful_logins": record["successful_logins"],
            "commands": record["commands"],
            "failed_commands": record["failed_commands"],
            "downloads": record["downloads"],
            "unique_command_count": len(record["unique_commands"]),
        })

print("\nDataset created:", OUTPUT)
print("Total sessions:", len(sessions))
