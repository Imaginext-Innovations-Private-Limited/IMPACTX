import json
import uuid
import ipaddress
from datetime import datetime, timezone
from pathlib import Path

from core.database import get_connection

BASE_DIR = Path(__file__).resolve().parent.parent
EVENT_LOG = BASE_DIR / "data" / "events.jsonl"
AUDIT_LOG = BASE_DIR / "data" / "adaptation_audit.jsonl"

MAX_EVENTS = 5000

SENSITIVE_KEYS = {
    "username", "password", "message", "command",
    "rawcommand", "input", "rawinput", "secret",
    "credential", "credentials"
}


def sanitize(value):
    """Remove sensitive fields recursively from report data."""

    if isinstance(value, dict):
        result = {}

        for key, item in value.items():
            normalized = key.lower().replace("_", "").replace("-", "")

            if normalized in SENSITIVE_KEYS:
                continue

            result[key] = sanitize(item)

        return result

    if isinstance(value, list):
        return [sanitize(item) for item in value]

    return value


def read_jsonl(path):
    records = []

    if not path.exists():
        return records

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return records


def generate_forensic_report(source_ip):
    # Validate the requested IP address.
    try:
        source_ip = str(ipaddress.ip_address(source_ip))
    except ValueError:
        raise ValueError("Invalid attacker IP address.")

    with get_connection() as connection:
        aggregate = connection.execute("""
            SELECT COUNT(*) AS total_events,
                   MIN(timestamp) AS first_seen,
                   MAX(timestamp) AS last_seen,
                   MAX(COALESCE(risk_score, 0)) AS highest_risk_score
            FROM events
            WHERE source_ip=?
        """, (source_ip,)).fetchone()

        total = aggregate["total_events"]

        domain_rows = connection.execute("""
            SELECT DISTINCT domain
            FROM events
            WHERE source_ip=? AND domain IS NOT NULL
        """, (source_ip,)).fetchall()

        detail_rows = connection.execute("""
            SELECT DISTINCT details
            FROM events
            WHERE source_ip=?
        """, (source_ip,)).fetchall()

        geo_row = connection.execute("""
            SELECT country, country_code, region, city,
                   latitude, longitude, isp, organization,
                   asn, timezone, lookup_status, last_updated
            FROM ip_geolocation
            WHERE ip_address=?
            LIMIT 1
        """, (source_ip,)).fetchone()

        rows = connection.execute("""
            SELECT event_id, timestamp, domain, event_type,
                   source_ip, details, risk_score, risk_level,
                   indicators, response_policy,
                   response_message, response_action
            FROM events
            WHERE source_ip=?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (source_ip, MAX_EVENTS)).fetchall()

    targeted_domains = sorted({
        row["domain"] for row in domain_rows if row["domain"]
    })

    targeted_services = set()

    for detail_row in detail_rows:
        try:
            details = json.loads(detail_row["details"] or "{}")
        except (json.JSONDecodeError, TypeError):
            continue

        if isinstance(details, dict) and details.get("service"):
            targeted_services.add(str(details["service"]))

    geoip = None
    if geo_row:
        geoip = dict(geo_row)

    if not rows:
        return None

    # Index web ML predictions by event ID.
    ml_by_event = {
        event.get("event_id"): event.get("ml_prediction")
        for event in read_jsonl(EVENT_LOG)
        if event.get("event_id")
    }

    # Index SSH adaptation decisions by session ID.
    adaptations = {}

    for record in read_jsonl(AUDIT_LOG):
        session_id = record.get("session_id")

        if session_id:
            adaptations[session_id] = record

    timeline = []

    for row in rows:
        event = dict(row)

        try:
            details = json.loads(event.pop("details") or "{}")
        except (json.JSONDecodeError, TypeError):
            details = {}

        try:
            indicators = json.loads(event.pop("indicators") or "[]")
        except (json.JSONDecodeError, TypeError):
            indicators = []

        details = sanitize(details)

        item = {
            **event,
            "details": details,
            "indicators": sanitize(indicators),
            "ml_prediction": sanitize(
                ml_by_event.get(event["event_id"])
            ),
        }

        session_id = details.get("session_id")

        if event["domain"] == "ssh" and session_id:
            audit = adaptations.get(session_id)

            if audit:
                item["ssh_adaptation"] = {
                    "risk_score": audit.get("risk_score"),
                    "risk_level": audit.get("risk_level"),
                    "indicators": sanitize(audit.get("indicators", [])),
                    "selected_response": audit.get("selected_response"),
                    "mode": audit.get("mode"),
                    "ssh_ml": sanitize(audit.get("ssh_ml", {})),
                }

        timeline.append(item)

    highest_score = int(aggregate["highest_risk_score"] or 0)

    return {
        "report_id": str(uuid.uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_type": "Security Incident Forensic Report",
        "attacker_ip": source_ip,
        "geoip": geoip,
        "summary": {
            "total_events": total,
            "included_events": len(timeline),
            "truncated": total > len(timeline),
            "first_seen": aggregate["first_seen"],
            "last_seen": aggregate["last_seen"],
            "highest_risk_score": highest_score,
            "highest_risk_level": (
                "high" if highest_score >= 60
                else "medium" if highest_score >= 30
                else "low"
            ),
            "targeted_domains": targeted_domains,
            "targeted_services": sorted(targeted_services),
        },
        "timeline": timeline,
        "privacy": {
            "usernames_included": False,
            "passwords_included": False,
            "raw_messages_included": False,
            "raw_command_arguments_included": False,
        },
        "limitations": [
            "ML predictions are experimental shadow-mode outputs.",
            "Historical records may not contain linked ML predictions.",
            "This report summarizes recorded honeypot evidence; "
            "it does not independently prove attacker identity.",
            "IP geolocation is approximate and does not identify an exact physical location.",
            "The detailed timeline is limited to the configured maximum; "
            "summary statistics cover all matching database events."
        ],
    }
