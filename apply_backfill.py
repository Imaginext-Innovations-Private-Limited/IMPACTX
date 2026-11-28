
import json

from core.behavior_analyzer import analyze_event
from core.database import get_connection


def main():
    updated = 0
    skipped = 0

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        rows = connection.execute("""
            SELECT event_id, domain, event_type, source_ip, details
            FROM events
            WHERE risk_level = 'unassessed'
               OR risk_level IS NULL
               OR TRIM(risk_level) = ''
        """).fetchall()

        for row in rows:
            try:
                details = json.loads(row["details"] or "{}")
            except (json.JSONDecodeError, TypeError):
                skipped += 1
                continue

            event = {
                "event_id": row["event_id"],
                "domain": row["domain"],
                "event_type": row["event_type"],
                "source_ip": row["source_ip"],
                "details": details,
            }

            assessment = analyze_event(event)

            if assessment["risk_level"] == "unassessed":
                skipped += 1
                continue

            connection.execute("""
                UPDATE events
                SET risk_score = ?,
                    risk_level = ?,
                    indicators = ?
                WHERE event_id = ?
                  AND (
                    risk_level = 'unassessed'
                    OR risk_level IS NULL
                    OR TRIM(risk_level) = ''
                  )
            """, (
                assessment["risk_score"],
                assessment["risk_level"],
                json.dumps(assessment["indicators"]),
                row["event_id"],
            ))

            updated += connection.execute(
                "SELECT changes()"
            ).fetchone()[0]

        connection.commit()

    print(f"Historical records updated: {updated}")
    print(f"Records left unassessed: {skipped}")
    print("Event IDs, timestamps, details and JSONL log preserved.")


if __name__ == "__main__":
    main()
