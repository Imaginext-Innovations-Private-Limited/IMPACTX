
from flask import Flask, request, jsonify, render_template, Response
from pathlib import Path
import json
import hashlib
import platform
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Preformatted, KeepTogether
)

from core.pipeline import process_event
from core.database import get_recent_events, get_connection
from core.forensic_report import generate_forensic_report, sanitize
from core.dashboard_analytics import build_dashboard_analytics
from core.ai_report_generator import generate_ai_report


app = Flask(__name__)

LOG_FILE = Path(__file__).resolve().parent / "data" / "events.jsonl"


def format_ist_timestamp(value):
    """Convert an ISO timestamp to Indian Standard Time."""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(
            ZoneInfo("Asia/Kolkata")
        ).strftime("%d %b %Y, %H:%M:%S IST")
    except (ValueError, TypeError, AttributeError):
        return value



def record_web_event(event_type):
    details = {
        "method": request.method,
        "path": request.path,
        "user_agent": request.headers.get("User-Agent", "")[:200],
        "query_keys": list(request.args.keys()),
        "query_values": [
            value
            for key in request.args
            for value in request.args.getlist(key)
        ],
    }

    return process_event(
        domain="web",
        event_type=event_type,
        source_ip=request.remote_addr or "unknown",
        details=details,
    )


def read_jsonl_events():
    events = []

    if not LOG_FILE.exists():
        return events

    with LOG_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return events


@app.route("/")
def home():
    return jsonify({
        "service": "Universal AI Honeypot Engine",
        "status": "running",
        "endpoints": [
            "/health",
            "/login",
            "/search",
            "/dashboard",
            "/forensic-report"
        ],
    })


@app.route("/login", methods=["GET", "POST"])
def login():
    record_web_event("simulated_login")

    return jsonify({
        "notice": "Simulated login endpoint",
        "message": "This is a honeypot; no credentials are collected.",
    })


@app.route("/search")
def search():
    record_web_event("simulated_search")

    return jsonify({
        "notice": "Simulated search endpoint",
        "page": "simulated_search",
    })



@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# --------------------------------------------------
# LIVE DASHBOARD EVENTS API
# --------------------------------------------------

@app.route("/api/recent-events")
def recent_events_api():

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                event_id,
                timestamp,
                domain,
                event_type,
                source_ip,
                details,
                risk_score,
                risk_level
            FROM events
            ORDER BY timestamp DESC
            LIMIT 15
        """).fetchall()

    events = []

    for row in rows:
        item = dict(row)

        try:
            details = json.loads(
                item.get("details") or "{}"
            )
        except (json.JSONDecodeError, TypeError):
            details = {}

        item["path"] = details.get("path", "-")
        item["risk_score"] = item.get("risk_score") or 0
        item["risk_level"] = (
            item.get("risk_level") or "unassessed"
        )

        # Display the highest risk across the entire SSH session.
        session_id = details.get("session_id")

        if item.get("domain") == "ssh" and session_id:
            with get_connection() as connection:
                session_risk = connection.execute("""
                    SELECT risk_score, risk_level
                    FROM events
                    WHERE domain = 'ssh'
                      AND details LIKE ?
                    ORDER BY risk_score DESC, timestamp DESC
                    LIMIT 1
                """, (f"%{session_id}%",)).fetchone()

            if session_risk:
                item["risk_score"] = int(
                    session_risk["risk_score"] or 0
                )
                item["risk_level"] = (
                    session_risk["risk_level"] or "LOW"
                )

        events.append(item)

    return jsonify({
        "events": events
    })


@app.route("/dashboard")
def dashboard():

    # --------------------------------------------------
    # 1. Retrieve events from SQLite
    # --------------------------------------------------

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                event_id,
                timestamp,
                domain,
                event_type,
                source_ip,
                details,
                risk_score,
                risk_level,
                indicators,
                response_policy,
                response_message,
                response_action
            FROM events
            ORDER BY timestamp DESC
        """).fetchall()

    # --------------------------------------------------
    # 2. Read ML predictions from JSONL
    # --------------------------------------------------

    ml_events = {
        event.get("event_id"): event
        for event in read_jsonl_events()
        if event.get("event_id")
    }

    # --------------------------------------------------
    # ML prediction statistics
    # --------------------------------------------------

    ml_stats = {
        "benign": 0,
        "suspicious": 0,
        "skipped": 0,
        "failed": 0,
        "other": 0,
        "average_confidence": None,
    }

    confidence_values = []

    for logged_event in ml_events.values():
        prediction = logged_event.get("ml_prediction") or {}

        if not isinstance(prediction, dict):
            ml_stats["other"] += 1
            continue

        label = str(prediction.get("prediction") or "").lower()
        status = str(prediction.get("status") or "").lower()

        if label in ("benign", "suspicious"):
            ml_stats[label] += 1
        elif status == "skipped":
            ml_stats["skipped"] += 1
        elif status == "error":
            ml_stats["failed"] += 1
        elif prediction:
            ml_stats["other"] += 1

        confidence = prediction.get("confidence")

        if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
            confidence_values.append(float(confidence))

    ml_stats["evaluated"] = (
        ml_stats["benign"] + ml_stats["suspicious"]
    )

    if confidence_values:
        ml_stats["average_confidence"] = round(
            sum(confidence_values) / len(confidence_values) * 100,
            1
        )

    # --------------------------------------------------
    # 3. Retrieve cached IP geolocation
    # --------------------------------------------------

    with get_connection() as connection:
        geo_rows = connection.execute("""
            SELECT
                ip_address,
                country,
                country_code,
                region,
                city,
                latitude,
                longitude,
                isp,
                organization,
                asn,
                timezone,
                lookup_status
            FROM ip_geolocation
            WHERE lookup_status = 'success'
        """).fetchall()

    geolocation_by_ip = {
        row["ip_address"]: dict(row)
        for row in geo_rows
    }

    # --------------------------------------------------
    # 4. Prepare dashboard events
    # --------------------------------------------------

    events = []

    for row in rows:

        item = dict(row)

        logged_event = ml_events.get(
            item.get("event_id"), {}
        )

        item["ml_prediction"] = logged_event.get(
            "ml_prediction"
        )

        try:
            item["details"] = json.loads(
                item.get("details") or "{}"
            )
        except (json.JSONDecodeError, TypeError):
            item["details"] = {}

        try:
            item["indicators"] = json.loads(
                item.get("indicators") or "[]"
            )
        except (json.JSONDecodeError, TypeError):
            item["indicators"] = []

        item["path"] = item["details"].get(
            "path", "-"
        )

        item["geolocation"] = geolocation_by_ip.get(
            item.get("source_ip")
        )

        if not item["geolocation"]:
            item["geolocation"] = {
                "lookup_status": "not_available",
                "message": (
                    "Private IP or location not yet available."
                )
            }

        item["risk_score"] = (
            item.get("risk_score") or 0
        )

        item["risk_level"] = (
            item.get("risk_level") or "unassessed"
        )

        events.append(item)

    # --------------------------------------------------
    # 5. Read adaptive decision history
    # --------------------------------------------------

    adaptation_records = []

    audit_path = (
        Path(__file__).resolve().parent
        / "data"
        / "adaptation_audit.jsonl"
    )

    ssh_ml_by_session = {}

    if audit_path.exists():

        try:
            with audit_path.open(
                "r",
                encoding="utf-8"
            ) as audit_file:

                for line in audit_file:

                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if record.get("mode") != "simulation_only":
                        continue

                    session_id = record.get("session_id")
                    ssh_ml = record.get("ssh_ml")

                    if session_id and isinstance(ssh_ml, dict):
                        ssh_ml_by_session[session_id] = ssh_ml

                    record.setdefault("ssh_ml", {
                        "model": "IsolationForest",
                        "prediction": (
                            "Not evaluated (historical record)"
                        ),
                        "anomaly_score": None,
                        "mode": "shadow",
                        "status": "historical",
                    })

                    adaptation_records.append(record)

        except OSError:
            app.logger.exception(
                "Could not read adaptation audit log"
            )

    # --------------------------------------------------
    # SSH Isolation Forest statistics
    # --------------------------------------------------

    ssh_ml_stats = {
        "total_sessions": len(adaptation_records),
        "evaluated": 0,
        "normal": 0,
        "review": 0,
        "unavailable": 0,
        "not_evaluated": 0,
        "average_anomaly_score": None,
    }

    anomaly_scores = []

    for record in adaptation_records:
        ssh_ml = record.get("ssh_ml") or {}

        if not isinstance(ssh_ml, dict):
            ssh_ml_stats["not_evaluated"] += 1
            continue

        prediction = str(
            ssh_ml.get("prediction") or ""
        ).strip().lower()

        status = str(
            ssh_ml.get("status") or ""
        ).strip().lower()

        if prediction == "normal":
            ssh_ml_stats["normal"] += 1
        elif prediction == "review":
            ssh_ml_stats["review"] += 1
        elif prediction == "unavailable" or status == "error":
            ssh_ml_stats["unavailable"] += 1
        else:
            ssh_ml_stats["not_evaluated"] += 1

        score = ssh_ml.get("anomaly_score")

        if isinstance(score, (int, float)) and not isinstance(score, bool):
            anomaly_scores.append(float(score))

    ssh_ml_stats["evaluated"] = (
        ssh_ml_stats["normal"] + ssh_ml_stats["review"]
    )

    if anomaly_scores:
        ssh_ml_stats["average_anomaly_score"] = round(
            sum(anomaly_scores) / len(anomaly_scores), 5
        )

    # --------------------------------------------------
    # 6. Attach SSH ML predictions
    # --------------------------------------------------

    for item in events:

        if item.get("domain") != "ssh":
            continue

        details = item.get("details") or {}

        session_id = (
            details.get("session_id")
            or item.get("session_id")
        )

        if session_id and session_id in ssh_ml_by_session:

            item["ml_prediction"] = (
                ssh_ml_by_session[session_id]
            )

        elif not item.get("ml_prediction"):

            item["ml_prediction"] = {
                "model": "IsolationForest",
                "prediction": (
                    "Not available for this event"
                ),
                "anomaly_score": None,
                "mode": "shadow",
                "status": "not_linked",
            }

    adaptation_records = list(
        reversed(adaptation_records[-50:])
    )

    # --------------------------------------------------
    # 7. Build real dashboard analytics
    # --------------------------------------------------

    dashboard_analytics = build_dashboard_analytics()

    # --------------------------------------------------
    # 8. Render dashboard
    # --------------------------------------------------

    return render_template(
        "dashboard.html",

        # Existing event data
        dashboard_events=events,

        # Risk summary
        total=len(events),

        high=sum(
            event["risk_level"] == "high"
            for event in events
        ),

        medium=sum(
            event["risk_level"] == "medium"
            for event in events
        ),

        low=sum(
            event["risk_level"] == "low"
            for event in events
        ),

        unassessed=sum(
            event["risk_level"] == "unassessed"
            for event in events
        ),

        # Existing adaptive history
        adaptation_records=adaptation_records,
        ssh_ml_stats=ssh_ml_stats,

        # New dashboard analytics
        protocol_stats=dashboard_analytics["protocol_stats"],

        event_stats=dashboard_analytics["event_stats"],
        ml_stats=ml_stats,

        service_stats=dashboard_analytics["service_stats"],

        top_attackers=dashboard_analytics["top_attackers"],

        geolocation_points=dashboard_analytics["geolocation"],
    )


# ------------------------------------------------------

# ------------------------------------------------------
# INDIVIDUAL EVENT INVESTIGATION PAGE
# ------------------------------------------------------

@app.route("/event-report/<event_id>")
def event_report_page(event_id):

    with get_connection() as connection:
        row = connection.execute("""
            SELECT event_id, timestamp, domain, event_type,
                   source_ip, details, risk_score, risk_level,
                   indicators, response_policy,
                   response_message, response_action
            FROM events
            WHERE event_id = ?
        """, (event_id,)).fetchone()

        geo_row = connection.execute("""
            SELECT country, country_code, region, city,
                   latitude, longitude, isp, organization,
                   asn, timezone, lookup_status
            FROM ip_geolocation
            WHERE ip_address = ?
        """, (row["source_ip"],)).fetchone() if row else None

    if row is None:
        return "Event not found.", 404

    event = dict(row)

    event_record_hash = hashlib.sha256(
        json.dumps(
            dict(row),
            sort_keys=True,
            ensure_ascii=False,
            default=str
        ).encode("utf-8")
    ).hexdigest()

    cowrie_evidence_lines = []
    event["timestamp"] = format_ist_timestamp(event.get("timestamp"))

    try:
        event["details"] = json.loads(event["details"] or "{}")
    except (json.JSONDecodeError, TypeError):
        event["details"] = {}

    try:
        event["indicators"] = json.loads(event["indicators"] or "[]")
    except (json.JSONDecodeError, TypeError):
        event["indicators"] = []

    event["geolocation"] = dict(geo_row) if geo_row else {}

    # Retrieve actual SSH commands from Cowrie's original JSON log.
    event["ssh_commands"] = []
    session_id = event["details"].get("session_id")

    if event.get("domain") == "ssh" and session_id:

        # Calculate the highest risk recorded in this SSH session.
        with get_connection() as connection:
            session_risk = connection.execute("""
                SELECT risk_score, risk_level
                FROM events
                WHERE domain = 'ssh'
                  AND details LIKE ?
                ORDER BY risk_score DESC, timestamp DESC
                LIMIT 1
            """, (f"%{session_id}%",)).fetchone()

        if session_risk:
            event["risk_score"] = int(session_risk["risk_score"] or 0)
            event["risk_level"] = session_risk["risk_level"] or "LOW"

        cowrie_log = Path.home() / "cowrie/var/log/cowrie/cowrie.json"

        if cowrie_log.exists():
            with cowrie_log.open("r", encoding="utf-8") as log_file:
                for line in log_file:
                    try:
                        cowrie_event = json.loads(line)
                    except (json.JSONDecodeError, TypeError):
                        continue

                    if (
                        cowrie_event.get("session") == session_id
                        and cowrie_event.get("eventid") == "cowrie.command.input"
                    ):
                        actual_command = cowrie_event.get("input", "").strip()

                        if actual_command:
                            event["ssh_commands"].append({
                                "timestamp": format_ist_timestamp(cowrie_event.get("timestamp", "")),
                                "command": actual_command
                            })

    ml_event = next(
        (
            item for item in read_jsonl_events()
            if item.get("event_id") == event_id
        ),
        {}
    )

    event["details"] = sanitize(event["details"])
    event["indicators"] = sanitize(event["indicators"])
    event["ml_prediction"] = sanitize(
        ml_event.get("ml_prediction")
    )

    return render_template(
        "event_report.html",
        event=event
    )



# ------------------------------------------------------
# DOWNLOAD INDIVIDUAL EVENT REPORT
# ------------------------------------------------------


@app.route("/event-report/<event_id>/download")
def download_event_report(event_id):

    with get_connection() as connection:
        row = connection.execute("""
            SELECT event_id, timestamp, domain, event_type,
                   source_ip, details, risk_score, risk_level,
                   indicators, response_policy,
                   response_message, response_action
            FROM events
            WHERE event_id = ?
        """, (event_id,)).fetchone()

        geo_row = connection.execute("""
            SELECT country, country_code, region, city,
                   latitude, longitude, isp, organization,
                   asn, timezone, lookup_status
            FROM ip_geolocation
            WHERE ip_address = ?
        """, (row["source_ip"],)).fetchone() if row else None

    if row is None:
        return jsonify({"error": "Event not found."}), 404

    event = dict(row)

    event_record_hash = hashlib.sha256(
        json.dumps(
            dict(row),
            sort_keys=True,
            ensure_ascii=False,
            default=str
        ).encode("utf-8")
    ).hexdigest()

    cowrie_evidence_lines = []

    try:
        event["details"] = json.loads(event["details"] or "{}")
    except (json.JSONDecodeError, TypeError):
        event["details"] = {}

    try:
        event["indicators"] = json.loads(event["indicators"] or "[]")
    except (json.JSONDecodeError, TypeError):
        event["indicators"] = []

    event["geolocation"] = dict(geo_row) if geo_row else {}
    event["ssh_commands"] = []

    session_id = event["details"].get("session_id")

    # Use the highest recorded risk for this SSH session.
    if event.get("domain") == "ssh" and session_id:
        with get_connection() as connection:
            session_risk = connection.execute("""
                SELECT risk_score, risk_level
                FROM events
                WHERE domain = 'ssh'
                  AND details LIKE ?
                ORDER BY risk_score DESC, timestamp DESC
                LIMIT 1
            """, (f"%{session_id}%",)).fetchone()

        if session_risk:
            event["risk_score"] = int(session_risk["risk_score"] or 0)
            event["risk_level"] = session_risk["risk_level"] or "LOW"

        # Retrieve actual commands from Cowrie's original log.
        cowrie_log = Path.home() / "cowrie/var/log/cowrie/cowrie.json"

        if cowrie_log.exists():
            with cowrie_log.open("r", encoding="utf-8") as log_file:
                for line in log_file:
                    try:
                        cowrie_event = json.loads(line)
                    except (json.JSONDecodeError, TypeError):
                        continue

                    if (
                        cowrie_event.get("session") == session_id
                        and cowrie_event.get("eventid") == "cowrie.command.input"
                    ):
                        cowrie_evidence_lines.append(line.rstrip("\n"))
                        command = cowrie_event.get("input", "").strip()
                        if command:
                            event["ssh_commands"].append({
                                "timestamp": format_ist_timestamp(
                                    cowrie_event.get("timestamp", "")
                                ),
                                "command": command
                            })

    cowrie_evidence_hash = (
        hashlib.sha256(
            "\n".join(cowrie_evidence_lines).encode("utf-8")
        ).hexdigest()
        if cowrie_evidence_lines else None
    )

    event["evidence_hashes"] = {
        "event_record_sha256": event_record_hash,
        "cowrie_log_sha256": cowrie_evidence_hash
    }

    ml_event = next(
        (
            item for item in read_jsonl_events()
            if item.get("event_id") == event_id
        ),
        {}
    )

    event["details"] = sanitize(event["details"])
    event["indicators"] = sanitize(event["indicators"])
    event["ml_prediction"] = sanitize(
        ml_event.get("ml_prediction")
    )

    # Generate AI analysis from sanitized event evidence.
    ai_report = generate_ai_report(event)

    # Build the PDF in memory.
    from xml.sax.saxutils import escape

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=16 * mm,
        bottomMargin=14 * mm,
        title=f"Forensic Event Report - {event_id}",
        author="Universal AI Honeypot Engine"
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontSize=16,
        leading=19,
        textColor=colors.HexColor("#17365D"),
        alignment=TA_CENTER,
        spaceAfter=5
    ))
    styles.add(ParagraphStyle(
        name="ReportSubtitle",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#52657A"),
        alignment=TA_CENTER,
        spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading2"],
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#17365D"),
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    ))
    styles.add(ParagraphStyle(
        name="ReportBody",
        parent=styles["BodyText"],
        fontSize=7.5,
        leading=9.5,
        spaceAfter=3,
        wordWrap="CJK"
    ))
    styles.add(ParagraphStyle(
        name="ReportSmall",
        parent=styles["BodyText"],
        fontSize=6.8,
        leading=8,
        textColor=colors.HexColor("#52657A")
    ))
    styles.add(ParagraphStyle(
        name="ReportCode",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=5.7,
        leading=6.8,
        wordWrap="CJK"
    ))

    def safe(value):
        if value is None or value == "":
            value = "Unavailable"
        return escape(str(value))

    def para(value):
        return Paragraph(safe(value), styles["ReportBody"])

    def section(title):
        return Paragraph(escape(title), styles["SectionHeading"])

    def make_table(rows, widths=None):
        table = Table(
            rows,
            colWidths=widths or [42 * mm, 132 * mm],
            repeatRows=1,
            hAlign="LEFT"
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE6F1")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17365D")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("LEADING", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C7D2DF")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return table

    generated_at = format_ist_timestamp(
        datetime.now(timezone.utc).isoformat()
    )

    story = [
        Paragraph("DIGITAL FORENSIC INVESTIGATION REPORT",
                  styles["ReportTitle"]),
        Paragraph("Universal AI Honeypot Engine | Security Operations",
                  styles["ReportSubtitle"]),
        make_table([
            [para("Report Type"), para("Individual Honeypot Event Report")],
            [para("Event ID"), para(event["event_id"])],
            [para("Report Generated"), para(generated_at)],
            [para("Evidence Source"), para("Honeypot event database and available Cowrie logs")],
        ]),
        section("Case and Examination Information"),
        make_table([
            [para("Field"), para("Value")],
            [para("Case Reference"), para("CASE-" + event_id[:12].upper())],
            [para("Report Version"), para("1.1")],
            [para("Examiner / Analyst"), para("Not configured - system-generated report")],
            [para("Generating System"), para("Universal AI Honeypot Engine")],
            [para("System Host"), para(platform.node() or "Unavailable")],
            [para("Evidence Collection Time"), para(generated_at)],
            [para("Database Source"), para("data/honeypot.db")],
            [para("Cowrie Source"), para("Cowrie JSON event log, when available")],
            [para("Evidence Event ID"), para(event["event_id"])],
            [para("SSH Session ID"), para(session_id or "Not available")],
        ]),
        section("1. Executive Summary"),
        para(
            f"An event of type {event['event_type']} was recorded "
            f"in the {event['domain']} honeypot domain. "
            f"The recorded source IP address was {event['source_ip']}. "
            f"The assessed risk level is {event['risk_level']} "
            f"with a score of {event['risk_score']}/100."
        ),
        section("AI-Generated Investigation Analysis"),
        para("AI Analysis Status: " + ai_report.get("status", "unknown")),
        section("AI Executive Summary"),
        para(ai_report.get("executive_summary")),
        section("Attack Analysis"),
        para(ai_report.get("attack_analysis")),
        section("Attacker Behaviour Assessment"),
        para(ai_report.get("behavior_assessment")),
        section("Potential Security Impact"),
        para(ai_report.get("potential_impact")),
        section("Security Recommendations"),
        *[
            para("- " + str(item))
            for item in ai_report.get("recommendations", [])
        ],
        section("Investigation Conclusion"),
        para(ai_report.get("conclusion")),
        section("2. Event Overview"),
        make_table([
            [para("Field"), para("Recorded Value")],
            [para("Event ID"), para(event["event_id"])],
            [para("Event Type"), para(event["event_type"])],
            [para("Domain / Protocol"), para(event["domain"])],
            [para("Timestamp (IST)"), para(format_ist_timestamp(event["timestamp"]))],
            [para("Risk Level"), para(event["risk_level"])],
            [para("Risk Score"), para(f"{event['risk_score']}/100")],
        ]),
        section("3. Attacker and Network Information"),
        make_table([
            [para("Field"), para("Value")],
            [para("Source IP"), para(event["source_ip"])],
            [para("Country"), para(event["geolocation"].get("country"))],
            [para("Region"), para(event["geolocation"].get("region"))],
            [para("City"), para(event["geolocation"].get("city"))],
            [para("ISP"), para(event["geolocation"].get("isp"))],
            [para("Organization"), para(event["geolocation"].get("organization"))],
            [para("Coordinates"), para(
                f"{event['geolocation'].get('latitude')}, "
                f"{event['geolocation'].get('longitude')}"
                if event["geolocation"].get("latitude") is not None
                and event["geolocation"].get("longitude") is not None
                else "Unavailable"
            )],
        ]),
        para(
            "Geolocation is approximate. Private IP addresses cannot "
            "normally be mapped to a public geographic location."
        ),
        section("4. Event Evidence and Details"),
    ]

    details_text = json.dumps(
        event["details"],
        ensure_ascii=False,
        separators=(",", ": ")
    )
    story.append(Paragraph(
        escape(details_text[:12000]).replace("\\n", "<br/>"),
        styles["ReportCode"]
    ))

    story.append(section("5. SSH Command History"))

    if event["ssh_commands"]:
        command_rows = [[
            para("No."),
            para("Timestamp (IST)"),
            para("Command Captured by Cowrie")
        ]]
        for index, item in enumerate(event["ssh_commands"], 1):
            command_rows.append([
                para(index),
                para(item["timestamp"]),
                para(item["command"])
            ])
        story.append(make_table(
            command_rows,
            widths=[12 * mm, 53 * mm, 109 * mm]
        ))
    elif event["domain"] == "ssh":
        story.append(para(
            "No command input records were found for this session "
            "in the available Cowrie log."
        ))
    else:
        story.append(para("Not applicable to this event."))

    story.append(section("6. Event Timeline"))

    timeline_rows = [
        [para("Sequence"), para("Timestamp (IST)"), para("Activity")]
    ]

    timeline_rows.append([
        para("1"),
        para(format_ist_timestamp(event.get("timestamp", ""))),
        para("Event recorded by honeypot")
    ])

    if event["ssh_commands"]:
        timeline_rows.append([
            para("2"),
            para("See SSH Command History"),
            para(
                f"{len(event['ssh_commands'])} command inputs "
                "captured by Cowrie"
            )
        ])

    story.append(make_table(
        timeline_rows,
        widths=[18 * mm, 53 * mm, 103 * mm]
    ))

    story.append(section("7. Suspicious Indicators"))

    indicators = event["indicators"]
    if isinstance(indicators, list) and indicators:
        for indicator in indicators:
            story.append(Paragraph(
                "• " + safe(indicator),
                styles["ReportBody"]
            ))
    elif indicators and not isinstance(indicators, list):
        story.append(para(json.dumps(indicators, ensure_ascii=False)))
    else:
        story.append(para("No configured suspicious pattern was matched."))

    story.extend([
        section("8. Machine Learning Analysis"),
        Preformatted(
            json.dumps(
                event["ml_prediction"] or {},
                ensure_ascii=False,
                separators=(",", ": ")
            )[:8000],
            styles["ReportCode"]
        ),
        section("9. Honeypot Response"),
        make_table([
            [para("Field"), para("Value")],
            [para("Response Policy"), para(event["response_policy"])],
            [para("Response Action"), para(event["response_action"])],
            [para("Response Message"), para(event["response_message"])],
        ]),
        section("10. SHA-256 Evidence Integrity"),
        para(
            "SHA-256 hashes below identify the exact evidence representations "
            "used by this report. Recalculate the hashes from the same source "
            "records to verify that they have not changed."
        ),
        make_table([
            [para("Evidence Item"), para("SHA-256 Hash")],
            [para("Database event record"), para(event_record_hash)],
            [para("Matching Cowrie command log lines"),
             para(cowrie_evidence_hash or "Unavailable - no matching command records")],
        ]),
        para(
            "The database event hash is calculated from a canonical JSON "
            "representation of the selected database row. The Cowrie hash "
            "covers the original matching command-input log lines collected "
            "for this session."
        ),
        para(
            "The generated PDF has its own SHA-256 checksum. It is supplied "
            "in a separate .sha256 file because including a PDF's own final "
            "hash inside that same PDF would change the hash."
        ),
        section("11. Evidence Notes and Limitations"),
        para(
            "This report is generated from records available in the "
            "Universal AI Honeypot Engine database and associated logs. "
            "The SSH command history is obtained from the available "
            "Cowrie log when a matching session is present."
        ),
        para(
            "The report is a system-generated investigation summary. "
            "It does not independently establish the identity of an "
            "attacker or prove that an observed action was successful."
        ),
        para(
            "For evidentiary use, preserve the original database, "
            "Cowrie logs and JSONL event logs. Maintain access controls "
            "and document any subsequent handling of these files."
        ),
        Spacer(1, 4),
        Paragraph(
            "End of Report",
            ParagraphStyle(
                "EndReport",
                parent=styles["ReportSmall"],
                alignment=TA_CENTER
            )
        )
    ])

    def draw_page(canvas, document):
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(colors.HexColor("#C7D2DF"))
        canvas.line(18 * mm, height - 15 * mm, width - 18 * mm, height - 15 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#52657A"))
        canvas.drawString(18 * mm, 10 * mm, "Universal AI Honeypot Engine")
        canvas.drawRightString(
            width - 18 * mm, 10 * mm,
            f"Page {document.page}"
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)

    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

    report_dir = Path(__file__).resolve().parent / "data" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    checksum_path = report_dir / f"forensic-event-report-{event_id}.pdf.sha256"
    checksum_path.write_text(
        f"{pdf_hash}  forensic-event-report-{event_id}.pdf\\n",
        encoding="utf-8"
    )

    response = Response(
        pdf_bytes,
        mimetype="application/pdf"
    )
    response.headers["X-PDF-SHA256"] = pdf_hash
    response.headers["Content-Disposition"] = (
        f'attachment; filename="forensic-event-report-{event_id}.pdf"'
    )
    response.headers["Cache-Control"] = "no-store"

    return response



@app.route("/event-report/<event_id>/download/checksum")
def download_event_report_checksum(event_id):

    if Path(event_id).name != event_id:
        return "Invalid event ID.", 400

    with get_connection() as connection:
        exists = connection.execute(
            "SELECT 1 FROM events WHERE event_id = ?",
            (event_id,)
        ).fetchone()

    if not exists:
        return "Event not found.", 404

    checksum_path = (
        Path(__file__).resolve().parent
        / "data" / "reports"
        / f"forensic-event-report-{event_id}.pdf.sha256"
    )

    if not checksum_path.is_file():
        return "Generate the PDF report first.", 404

    response = Response(
        checksum_path.read_text(encoding="utf-8"),
        mimetype="text/plain"
    )
    response.headers["Content-Disposition"] = (
        f'attachment; filename="forensic-event-report-{event_id}.pdf.sha256"'
    )
    response.headers["Cache-Control"] = "no-store"
    return response


# FORENSIC REPORT DOWNLOAD
# ------------------------------------------------------

@app.route("/forensic-report")
def forensic_report_download():

    source_ip = request.args.get(
        "ip", ""
    ).strip()

    if not source_ip:

        return jsonify({
            "error": "Missing attacker IP address.",
            "usage": "/forensic-report?ip=192.168.47.128"
        }), 400

    try:

        report = generate_forensic_report(source_ip)

    except ValueError as error:

        return jsonify({
            "error": str(error)
        }), 400

    except Exception:

        app.logger.exception(
            "Forensic report generation failed"
        )

        return jsonify({
            "error": "Could not generate forensic report."
        }), 500

    if report is None:

        return jsonify({
            "error": "No events found for this IP address."
        }), 404

    response = Response(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False
        ),
        mimetype="application/json"
    )

    response.headers["Content-Disposition"] = (
        f'attachment; filename="forensic-report-'
        f'{report["report_id"][:8]}.json"'
    )

    response.headers["Cache-Control"] = "no-store"

    return response


# ------------------------------------------------------
# 404 HANDLER
# ------------------------------------------------------

@app.errorhandler(404)
def not_found(error):

    record_web_event("unknown_route")

    return jsonify({
        "error": "Not found"
    }), 404


# ------------------------------------------------------
# APPLICATION ENTRY POINT
# ------------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
