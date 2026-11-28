"""Resolve public IP addresses observed in a capture to map coordinates.

The dashboard must never draw invented route lines. Locations come only from
addresses that were actually seen in the captured packets, resolved through
ip-api.com (no API key required, HTTP only on the free tier).

If the lookup is unavailable, the result says so and returns no locations, so
the globe has nothing to draw rather than falling back to fake answers.
"""

import ipaddress
import json
import socket
import time
import urllib.error
import urllib.request

from backend.services.process_owner import lookup_connection_owners

try:
    import dns.resolver
    import dns.reversename
except ImportError:  # Reverse DNS simply stays unavailable.
    dns = None

BATCH_URL = (
    "http://ip-api.com/batch"
    "?fields=status,message,query,country,city,lat,lon"
)
SELF_URL = (
    "http://ip-api.com/json/"
    "?fields=status,message,query,country,city,lat,lon"
)

TIMEOUT_SECONDS = 6
CACHE_TTL_SECONDS = 6 * 60 * 60

# Reverse DNS is only a fallback, so it is queried directly against the
# configured DNS servers with a short deadline. The OS resolver hangs on this
# machine; a direct UDP query answers immediately.
PTR_TIMEOUT_SECONDS = 2.5
PTR_MAX_LOOKUPS = 20
PTR_CACHE_TTL_SECONDS = 6 * 60 * 60
PTR_NEGATIVE_TTL_SECONDS = 10 * 60
# ip-api.com accepts up to 100 addresses per batch request.
MAX_LOOKUPS = 100

# NAT64/CLAT traffic (common on IPv6-first mobile and Wi-Fi networks) carries
# the real destination IPv4 in the low 32 bits of an IPv6 address.
NAT64_NETWORKS = (
    ipaddress.ip_network("64:ff9b::/96"),
    ipaddress.ip_network("64:ff9b:1::/48"),
)

# Live detector results attached to each captured flow, keyed to a short name.
THREAT_DETECTORS = (
    ("ddos_detection", "DDoS"),
    ("c2_detection", "C2"),
)

BENIGN_VERDICTS = {"benign", "normal", "false", "no threat"}

# Confidence bands used to colour the map by threat level.
THREAT_BANDS = (
    (0.9, "critical"),
    (0.75, "high"),
    (0.5, "medium"),
    (0.0, "low"),
)

_cache = {}
_ptr_cache = {}


def geolocatable_address(value):
    """Return the public IPv4 to geolocate for an observed address, or None.

    Private, loopback, link-local, multicast and reserved ranges cannot be
    geolocated. ip-api.com also cannot resolve native IPv6, but NAT64 traffic
    embeds the real destination IPv4, which is unwrapped here.
    """
    if not value:
        return None

    try:
        address = ipaddress.ip_address(str(value).strip())
    except ValueError:
        return None

    if address.version == 4:
        if address.is_global and not address.is_multicast:
            return str(address)

        return None

    for network in NAT64_NETWORKS:
        if address in network:
            embedded = ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)

            if embedded.is_global and not embedded.is_multicast:
                return str(embedded)

            return None

    return None


def is_public_ip(value):
    """True only for addresses that can be resolved to a real location."""
    return geolocatable_address(value) is not None


def _local_addresses():
    """Addresses assigned to this machine.

    The host's own address can appear inside its own captured traffic; it is
    the origin of the map, never a connected network.
    """
    found = set()

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            address = info[4][0]

            if address:
                found.add(address)
    except OSError:
        pass

    return found


def _cached(address):
    entry = _cache.get(address)

    if not entry:
        return None

    stored_at, record = entry

    if time.time() - stored_at > CACHE_TTL_SECONDS:
        _cache.pop(address, None)
        return None

    return record


def _remember(records):
    now = time.time()

    for address, record in records.items():
        if record:
            _cache[address] = (now, record)


def _record_from_payload(payload):
    if not isinstance(payload, dict) or payload.get("status") != "success":
        return None

    try:
        lat = float(payload.get("lat"))
        lng = float(payload.get("lon"))
    except (TypeError, ValueError):
        return None

    return {
        "ip": payload.get("query"),
        "city": payload.get("city") or None,
        "country": payload.get("country") or None,
        "lat": lat,
        "lng": lng,
    }


def _request(url, body=None):
    data = None
    headers = {"Accept": "application/json"}

    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers)

    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def lookup_own_location():
    """Geolocate this machine's public address, used as the map origin."""
    try:
        return _record_from_payload(_request(SELF_URL))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def lookup_addresses(addresses):
    """Resolve a list of addresses, honouring the cache. Never raises."""
    wanted = []
    resolved = {}

    for address in addresses:
        cached = _cached(address)

        if cached:
            resolved[address] = cached
        else:
            wanted.append(address)

    if not wanted:
        return resolved

    chunks = [
        wanted[index:index + MAX_LOOKUPS]
        for index in range(0, len(wanted), MAX_LOOKUPS)
    ]

    for chunk in chunks:
        try:
            payload = _request(
                BATCH_URL,
                [{"query": address} for address in chunk],
            )
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            break

        if not isinstance(payload, list):
            break

        fetched = {}

        for item in payload:
            record = _record_from_payload(item)

            if record and record.get("ip"):
                fetched[record["ip"]] = record

        _remember(fetched)
        resolved.update(fetched)

    return resolved


def _dns_name_map(flows, excluded):
    """Map observed addresses to the DNS names this capture resolved for them.

    Only names carried by real DNS responses in the capture are used. AAAA
    answers are also mapped through their low 32 bits, which is where
    NAT64/464XLAT keeps the IPv4 the device actually reached.
    """
    names = {}

    for flow in flows or []:
        for packet in flow.get("packets") or []:
            name = str(packet.get("dns_query") or "").strip().rstrip(".")
            answers = packet.get("dns_answers") or []
            legacy = packet.get("dns_answer")

            if legacy and legacy not in answers:
                answers = list(answers) + [legacy]

            if not name or not answers:
                continue

            for answer in answers:
                try:
                    address = ipaddress.ip_address(str(answer).strip())
                except ValueError:
                    continue

                candidate = (
                    address
                    if address.version == 4
                    else ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)
                )
                key = str(candidate)

                if key in excluded:
                    continue

                if candidate.is_global and not candidate.is_multicast:
                    names.setdefault(key, name)

    return names


def _ptr_resolver():
    """Resolver that asks the configured DNS servers directly."""
    if dns is None:
        return None

    try:
        resolver = dns.resolver.Resolver(configure=True)
    except Exception:
        return None

    if not resolver.nameservers:
        return None

    resolver.timeout = PTR_TIMEOUT_SECONDS
    resolver.lifetime = PTR_TIMEOUT_SECONDS
    resolver.retries = 0

    return resolver


def _ptr_lookup(addresses):
    """Reverse-DNS names for addresses, with a short timeout and a cache."""
    names = {}
    pending = []
    now = time.monotonic()

    for address in addresses:
        cached = _ptr_cache.get(address)

        if cached is not None:
            name, cached_at, ttl = cached

            if now - cached_at < ttl:
                if name:
                    names[address] = name

                continue

        pending.append(address)

    if not pending:
        return names

    resolver = _ptr_resolver()

    if resolver is None:
        return names

    for address in pending[:PTR_MAX_LOOKUPS]:
        name = None

        try:
            answer = resolver.resolve(
                dns.reversename.from_address(address),
                "PTR",
                lifetime=PTR_TIMEOUT_SECONDS,
            )
            name = str(answer[0]).strip().rstrip(".") or None
        except Exception:
            name = None

        _ptr_cache[address] = (
            name,
            now,
            PTR_CACHE_TTL_SECONDS if name else PTR_NEGATIVE_TTL_SECONDS,
        )

        if name:
            names[address] = name

    return names


def _threat_level(confidence):
    for floor, level in THREAT_BANDS:
        if confidence >= floor:
            return level

    return "low"


def _flow_threat(flow):
    """Strongest non-benign live verdict attached to one captured flow."""
    strongest = {
        "level": "none",
        "detector": None,
        "verdict": "No threat detected",
        "confidence": 0.0,
    }

    for key, label in THREAT_DETECTORS:
        result = flow.get(key)

        if not isinstance(result, dict) or not result.get("success"):
            continue

        verdict = str(result.get("prediction") or "").strip()

        if not verdict or verdict.lower() in BENIGN_VERDICTS:
            continue

        try:
            confidence = float(result.get("confidence"))
        except (TypeError, ValueError):
            confidence = 0.0

        if confidence >= strongest["confidence"]:
            strongest = {
                "level": _threat_level(confidence),
                "detector": label,
                "verdict": verdict,
                "confidence": round(confidence, 4),
            }

    return strongest


def _address_keys(value):
    """Keys an address can be matched by.

    A public IPv4 is its own key. An IPv6 address is additionally keyed by its
    low 32 bits: that is where NAT64/CLAT (and the connection table on an
    IPv6-first network) keeps the IPv4 the device actually reached.
    """
    keys = []
    normalized = geolocatable_address(value)

    if normalized:
        keys.append(normalized)

    try:
        address = ipaddress.ip_address(str(value).strip())
    except ValueError:
        return keys

    if address.version == 6:
        embedded = ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)

        if embedded.is_global and not embedded.is_multicast:
            key = str(embedded)

            if key not in keys:
                keys.append(key)

    return keys


def _port(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _owner_index(rows):
    """Index connection owners by remote endpoint and by local port.

    Each key keeps every process seen owning it. A location is an aggregate of
    many connections, so every process that reached it is a fact about that
    location rather than a guess between them.
    """
    remote = {}
    local = {}

    for row in rows or []:
        process = str(row.get("process") or "").strip()

        if not process:
            continue

        port = _port(row.get("port"))

        if port is not None:
            for address in _address_keys(row.get("ip")):
                remote.setdefault((address, port), set()).add(process)

        local_port = _port(row.get("local_port"))

        if local_port is not None:
            local.setdefault(local_port, set()).add(process)

    return remote, local


def _flow_endpoints(flow, excluded):
    """(address, port, protocol, local_port) for each captured remote end.

    Only ports and protocols present in the capture are returned; a packet
    without ports (ICMP, for example) yields a protocol with no port. The
    local port is what identifies a socket whose connection already closed.
    """
    endpoints = set()

    for packet in flow.get("packets") or []:
        protocol = str(packet.get("protocol") or "OTHER").strip().upper()

        for address_key, port_key, local_key in (
            ("src_ip", "src_port", "dst_port"),
            ("dst_ip", "dst_port", "src_port"),
        ):
            raw = packet.get(address_key)

            if not raw or raw in excluded:
                continue

            address = geolocatable_address(raw)

            if not address:
                continue

            endpoints.add((
                address,
                _port(packet.get(port_key)),
                protocol,
                _port(packet.get(local_key)),
            ))

    return endpoints


def _applications(endpoints, remote_owners, local_owners):
    """Processes behind the remote endpoints of one captured flow.

    The remote endpoint is checked first, then the local port the flow used: a
    connection that opened and closed between snapshots is still identifiable
    by the socket it ran on.
    """
    found = {}

    for address, port, _protocol, local_port in endpoints:
        names = set()

        if port is not None:
            names = remote_owners.get((address, port), set())

        if not names and local_port is not None:
            names = local_owners.get(local_port, set())

        for name in names:
            found[name] = found.get(name, 0) + 1

    return found


def _observations(flows, excluded, remote_owners, local_owners):
    """Count public addresses per flow and keep their verdict, apps, ports."""
    counts = {}
    threats = {}
    applications = {}
    endpoints_by_address = {}

    for flow in flows or []:
        endpoints = _flow_endpoints(flow, excluded)
        seen = {address for address, _, _, _ in endpoints}

        if not seen:
            continue

        threat = _flow_threat(flow)
        processes = _applications(endpoints, remote_owners, local_owners)

        for address in seen:
            counts[address] = counts.get(address, 0) + 1

            current = threats.get(address)

            if current is None or threat["confidence"] > current["confidence"]:
                threats[address] = threat

            if processes:
                per_address = applications.setdefault(address, {})

                for process, hits in processes.items():
                    per_address[process] = per_address.get(process, 0) + hits

        for address, port, protocol, _local_port in endpoints:
            per_endpoint = endpoints_by_address.setdefault(address, {})
            key = (port, protocol)
            per_endpoint[key] = per_endpoint.get(key, 0) + 1

    return counts, threats, applications, endpoints_by_address


def resolve_session_geo(flows, earlier_owners=None):
    """Build the map's location layer from captured flows only.

    ``earlier_owners`` is an optional set of connection-owner snapshots taken
    before and during the capture; they are merged with a fresh one so
    connections that closed during the capture can still be attributed to
    their process.
    """
    origin = lookup_own_location()
    origin_ip = origin.get("ip") if origin else None

    excluded = _local_addresses()

    if origin_ip:
        excluded.add(origin_ip)

    remote_owners, local_owners = _owner_index(
        list(earlier_owners or []) + lookup_connection_owners()
    )
    counts, threats, applications, endpoints = _observations(
        flows, excluded, remote_owners, local_owners
    )
    capture_names = _dns_name_map(flows, excluded)
    dns_names = dict(capture_names)

    observed = [address for address in counts if address != origin_ip]
    observed.sort(key=lambda address: counts[address], reverse=True)
    observed = observed[:MAX_LOOKUPS]

    # Locations with no name from the capture get one from a direct PTR query.
    missing_names = [
        address for address in observed if not dns_names.get(address)
    ]

    if missing_names:
        for address, name in _ptr_lookup(missing_names).items():
            dns_names.setdefault(address, name)

    resolved = lookup_addresses(observed) if observed else {}

    locations = []

    for address in observed:
        record = resolved.get(address)

        if not record:
            continue

        threat = threats.get(address) or {
            "level": "none",
            "detector": None,
            "verdict": "No threat detected",
            "confidence": 0.0,
        }

        hostname = dns_names.get(address)
        apps = [
            {"name": name, "connections": connections}
            for name, connections in applications.get(address, {}).items()
        ]
        apps.sort(
            key=lambda item: (-item["connections"], item["name"])
        )
        ports_seen = [
            {"port": port, "protocol": protocol, "flows": flows_seen}
            for (port, protocol), flows_seen in endpoints.get(address, {}).items()
        ]
        ports_seen.sort(
            key=lambda item: (
                -item["flows"],
                item["port"] if item["port"] is not None else 0,
                item["protocol"],
            )
        )

        locations.append({
            "ip": record["ip"],
            "city": record["city"],
            "country": record["country"],
            "lat": record["lat"],
            "lng": record["lng"],
            "connections": counts.get(address, 0),
            "hostname": hostname,
            "hostname_source": (
                "capture"
                if address in capture_names
                else "ptr"
                if hostname
                else None
            ),
            "applications": apps[:5],
            "ports": ports_seen[:6],
            "threat": threat,
        })

    return {
        "source": "ip-api.com",
        "resolved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "available": bool(origin and locations),
        "observed_ip_count": len(counts),
        "origin": origin,
        "locations": locations,
    }
