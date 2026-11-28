
import json
import ipaddress
from collections import Counter

from core.database import get_connection


SIMULATED_PROTOCOLS = {
    "VNC_TEST",
    "MSRPC_TCP_TEST",
    "SMB_TEST",
    "RDP_TEST",
}


SERVICE_PROTOCOL_MAP = {
    "ftp_test": "FTP",
    "telnet_test": "TELNET",
    "alternate_http": "HTTP",
    "https_test": "HTTPS",
    "cowrie": "SSH",
    "mysql_test": "MYSQL",
    "postgres_test": "POSTGRESQL",
    "smtp_test": "SMTP",
    "pop3_test": "POP3",
    "imap_test": "IMAP",
    "dns_test": "DNS",
    "vnc_test": "VNC_TEST",
    "rdp_test": "RDP_TEST",
    "smb_test": "SMB_TEST",
    "msrpc_test": "MSRPC_TCP_TEST",
}


def classify_attacker_ip(ip_address):
    """Classify an attacker IP without inventing geographic information."""

    try:
        address = ipaddress.ip_address(str(ip_address).strip())
    except ValueError:
        return {
            "ip_type": "invalid",
            "network_type": "Invalid IP",
            "location_status": "invalid_ip",
        }

    if address.is_loopback:
        return {
            "ip_type": "loopback",
            "network_type": "Localhost",
            "location_status": "skipped_non_public",
        }

    if address.is_link_local:
        return {
            "ip_type": "link_local",
            "network_type": "Link-local network",
            "location_status": "skipped_non_public",
        }

    if address.is_private:
        return {
            "ip_type": "private",
            "network_type": "Private network",
            "location_status": "skipped_non_public",
        }

    if address.is_reserved or not address.is_global:
        return {
            "ip_type": "reserved_or_non_global",
            "network_type": "Reserved / non-global IP",
            "location_status": "skipped_non_public",
        }

    return {
        "ip_type": "public",
        "network_type": "Public IP",
        "location_status": "pending",
    }


def build_dashboard_analytics():

    protocol_counts = Counter()
    event_counts = Counter()
    service_counts = Counter()

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT domain, event_type, source_ip,
                   risk_score, risk_level, details
            FROM events
        """).fetchall()

        attacker_rows = connection.execute("""
            SELECT source_ip,
                   COUNT(*) AS total,
                   MAX(risk_score) AS max_risk
            FROM events
            GROUP BY source_ip
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()

        geo_rows = connection.execute("""
            SELECT ip_address, country, country_code,
                   region, city, latitude, longitude,
                   isp, organization, asn, timezone,
                   lookup_status, last_updated
            FROM ip_geolocation
        """).fetchall()

    for row in rows:
        try:
            details = json.loads(row["details"] or "{}")
        except (json.JSONDecodeError, TypeError):
            details = {}

        protocol = details.get("protocol")
        service = details.get("service")

        event_counts[row["event_type"]] += 1

        if protocol:
            protocol_name = str(protocol).strip().upper()
        elif service:
            protocol_name = SERVICE_PROTOCOL_MAP.get(
                str(service).strip().lower()
            )
        else:
            protocol_name = None

        if protocol_name:
            protocol_counts[protocol_name] += 1

        if service:
            service_counts[str(service)] += 1

    attacker_lookup = {
        row["source_ip"]: dict(row)
        for row in attacker_rows
    }

    geolocation = {}

    # Include existing public GeoIP records and their classifications.
    for row in geo_rows:
        location = dict(row)
        ip_address = location["ip_address"]

        classification = classify_attacker_ip(ip_address)
        location.update(classification)

        attacker = attacker_lookup.get(ip_address, {})
        max_risk = int(attacker.get("max_risk") or 0)

        if max_risk >= 60:
            risk_level = "high"
        elif max_risk >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"

        location["event_count"] = int(attacker.get("total") or 0)
        location["max_risk"] = max_risk
        location["risk_level"] = risk_level

        geolocation[ip_address] = location

    attackers = []

    for row in attacker_rows:
        item = dict(row)
        source_ip = item["source_ip"]

        classification = classify_attacker_ip(source_ip)

        # Create a location placeholder when no GeoIP record exists.
        location = geolocation.get(source_ip, {})

        if not location:
            location = {
                "ip_address": source_ip,
                "country": None,
                "country_code": None,
                "region": None,
                "city": None,
                "latitude": None,
                "longitude": None,
                "isp": None,
                "organization": None,
                "asn": None,
                "timezone": None,
                **classification,
            }

        else:
            location.update(classification)

        item["geolocation"] = location
        attackers.append(item)

    protocol_stats = [
        {
            "name": name,
            "total": count,
            "simulated": name in SIMULATED_PROTOCOLS,
        }
        for name, count in protocol_counts.most_common()
    ]

    attacker_by_ip = {
        item["source_ip"]: item
        for item in attackers
    }

    geolocation_points = []

    # Only public IPs with real coordinates belong on the attack map.
    for ip_address, location in geolocation.items():

        if location.get("ip_type") != "public":
            continue

        latitude = location.get("latitude")
        longitude = location.get("longitude")

        if latitude is None or longitude is None:
            continue

        attacker = attacker_by_ip.get(ip_address, {})
        max_risk = int(attacker.get("max_risk") or 0)

        if max_risk >= 60:
            risk_level = "high"
        elif max_risk >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"

        geolocation_points.append({
            **location,
            "event_count": int(attacker.get("total") or 0),
            "max_risk": max_risk,
            "risk_level": risk_level,
        })

    return {
        "protocol_stats": protocol_stats,
        "event_stats": [
            {"name": name, "total": count}
            for name, count in event_counts.most_common(10)
        ],
        "service_stats": [
            {"name": name, "total": count}
            for name, count in service_counts.most_common(10)
        ],
        "top_attackers": attackers,
        "geolocation": geolocation_points,
    }
