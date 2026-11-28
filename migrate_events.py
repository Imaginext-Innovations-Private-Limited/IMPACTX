
import json
from pathlib import Path

from core.database import save_event_to_database

LOG_FILE = Path("data/events.jsonl")

imported = 0
skipped = 0

if not LOG_FILE.exists():
    print("Event log not found:", LOG_FILE)
    raise SystemExit(1)

with LOG_FILE.open("r", encoding="utf-8") as file:
    for line in file:
        try:
            event = json.loads(line)

            required = {
                "event_id", "timestamp", "domain",
                "event_type", "source_ip"
            }

            if not required.issubset(event):
                skipped += 1
                continue

            event.setdefault("details", {})
            event.setdefault(
                "risk_assessment",
                {
                    "risk_score": 0,
                    "risk_level": "unassessed",
                    "indicators": []
                }
            )
            event.setdefault("response_policy", {})

            save_event_to_database(event)
            imported += 1

        except (json.JSONDecodeError, KeyError, TypeError) as error:
            skipped += 1
            print("Skipped invalid record:", error)

print("Migration finished.")
print("Processed records:", imported)
print("Skipped records:", skipped)
