
import sqlite3
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "honeypot.db"


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                domain TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source_ip TEXT NOT NULL,
                details TEXT NOT NULL,
                risk_score INTEGER,
                risk_level TEXT,
                indicators TEXT,
                response_policy TEXT,
                response_message TEXT,
                response_action TEXT
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS ip_geolocation (
                ip_address TEXT PRIMARY KEY,
                country TEXT,
                country_code TEXT,
                region TEXT,
                city TEXT,
                latitude REAL,
                longitude REAL,
                isp TEXT,
                organization TEXT,
                asn TEXT,
                timezone TEXT,
                lookup_status TEXT NOT NULL,
                last_updated TEXT NOT NULL
            )
        """)


def save_event_to_database(event):
    assessment = event.get("risk_assessment", {})
    response = event.get("response_policy", {})

    with get_connection() as connection:
        connection.execute("""
            INSERT OR REPLACE INTO events (
                event_id, timestamp, domain, event_type,
                source_ip, details, risk_score, risk_level,
                indicators, response_policy, response_message,
                response_action
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event["event_id"],
            event["timestamp"],
            event["domain"],
            event["event_type"],
            event["source_ip"],
            json.dumps(event.get("details", {})),
            assessment.get("risk_score", 0),
            assessment.get("risk_level", "unassessed"),
            json.dumps(assessment.get("indicators", [])),
            response.get("policy", "none"),
            response.get("message", ""),
            response.get("action", "")
        ))


def get_recent_events(limit=50):
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT * FROM events
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,)).fetchall()

    return [dict(row) for row in rows]


initialize_database()
