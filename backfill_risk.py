
import json

from core.behavior_analyzer import analyze_event
from core.database import get_connection


def main():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT event_id, domain, event_type, source_ip,
                   details, risk_score, risk_level, indicators
            FROM events
            WHERE risk_level = 'unassessed'
               OR risk_level IS NULL
               OR TRIM(risk_level) = ''
            ORDER BY domain, event_type
        """).fetchall()

    print(f"Unassessed records found: {len(rows)}")
    proposed = 0

    for row in rows:
        record = dict(row)

        try:
            details = json.loads(record.get("details") or "{}")
        except (json.JSONDecodeError, TypeError):
            details = {}

        event = {
            "event_id": record["event_id"],
            "domain": record["domain"],
            "event_type": record["event_type"],
            "source_ip": record["source_ip"],
            "details": details,
        }

        assessment = analyze_event(event)

        if assessment["risk_level"] == "unassessed":
            print(
                f"REVIEW | {record['domain']} | "
                f"{record['event_type']} | "
                "no applicable rule"
            )
            continue

        proposed += 1
        print(
            f"PROPOSE | {record['domain']} | "
            f"{record['event_type']} | "
            f"{assessment['risk_score']} "
            f"({assessment['risk_level']}) | "
            f"{'; '.join(assessment['indicators'])}"
        )

    print(f"\nProposed classifications: {proposed}")
    print("DRY RUN ONLY: database was not modified.")


if __name__ == "__main__":
    main()
