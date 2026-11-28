
import ipaddress
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

from core.database import get_connection

API_URL = "https://ipwho.is/{}"
API_TIMEOUT = 8


def classify_ip_address(ip_address):
    """Classify an IP without attempting to geolocate non-public addresses."""
    original_ip = str(ip_address).strip()

    try:
        address = ipaddress.ip_address(original_ip)
    except ValueError:
        return {
            "ip_address": original_ip,
            "ip_type": "invalid",
            "lookup_status": "invalid_ip",
            "message": "Invalid IP address."
        }

    if address.is_loopback:
        ip_type = "loopback"
    elif address.is_link_local:
        ip_type = "link_local"
    elif address.is_private:
        ip_type = "private"
    elif address.is_reserved or not address.is_global:
        ip_type = "reserved_or_non_global"
    else:
        ip_type = "public"

    return {
        "ip_address": str(address),
        "ip_type": ip_type,
        "lookup_status": "pending" if ip_type == "public" else "skipped_non_public",
        "message": (
            "Public IP eligible for GeoIP lookup."
            if ip_type == "public"
            else f"{ip_type.replace('_', ' ').title()} IP; geographic location unavailable."
        )
    }


def validate_public_ip(ip_address):
    result = classify_ip_address(ip_address)

    if result["ip_type"] == "invalid":
        raise ValueError("Invalid IP address.")

    if result["ip_type"] != "public":
        return None

    return result["ip_address"]


def get_cached_location(ip_address):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM ip_geolocation WHERE ip_address = ?",
            (ip_address,)
        ).fetchone()

    return dict(row) if row else None


def lookup_ip_geolocation(ip_address, force_refresh=False):
    classification = classify_ip_address(ip_address)

    if classification["ip_type"] == "invalid":
        return classification

    if classification["ip_type"] != "public":
        return classification

    normalized_ip = classification["ip_address"]

    if not force_refresh:
        cached = get_cached_location(normalized_ip)
        if cached and cached["lookup_status"] == "success":
            cached["ip_type"] = "public"
            cached["cache_hit"] = True
            return cached

    request = urllib.request.Request(
        API_URL.format(normalized_ip),
        headers={"User-Agent": "Universal-AI-Honeypot/1.0"}
    )

    try:
        with urllib.request.urlopen(request, timeout=API_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))

    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        return {
            "ip_address": normalized_ip,
            "ip_type": "public",
            "lookup_status": "api_error",
            "message": str(error)
        }

    if not data.get("success"):
        return {
            "ip_address": normalized_ip,
            "ip_type": "public",
            "lookup_status": "not_found",
            "message": data.get("message", "Geolocation lookup failed.")
        }

    connection_data = data.get("connection") or {}
    timezone_data = data.get("timezone") or {}

    result = {
        "ip_address": normalized_ip,
        "country": data.get("country"),
        "country_code": data.get("country_code"),
        "region": data.get("region"),
        "city": data.get("city"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "isp": connection_data.get("isp"),
        "organization": connection_data.get("org"),
        "asn": connection_data.get("asn"),
        "timezone": timezone_data.get("id"),
        "lookup_status": "success",
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

    with get_connection() as connection:
        connection.execute("""
            INSERT OR REPLACE INTO ip_geolocation (
                ip_address, country, country_code, region, city,
                latitude, longitude, isp, organization, asn,
                timezone, lookup_status, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tuple(result.values()))

    result["ip_type"] = "public"
    result["cache_hit"] = False
    return result
