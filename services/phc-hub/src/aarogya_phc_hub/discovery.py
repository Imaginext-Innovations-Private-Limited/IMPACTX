"""Offline LAN/Hotspot peer discovery, live peer registry, and connect helper.

Provides:
- ``PeerRecord`` & thread-safe ``PeerRegistry`` tracking Tier-0 Watch and Tier-1
  Phone peers observed via HTTP sync, WebSocket mesh sync, or mDNS.
- ``detect_lan_ipv4()`` pure-stdlib local IPv4 detection (zero external network
  calls; safe in Airplane Mode and air-gapped CI).
- ``MdnsAdvertiser`` fail-soft ``_aarogya-mesh._tcp.local.`` mDNS advertiser
  using optional ``zeroconf`` when installed and enabled.
- ``create_discovery_router(...)`` FastAPI router exposing ``GET /api/v1/peers``
  and ``GET /api/v1/discovery/connect-info``.
"""

from __future__ import annotations

import array
import importlib
import ipaddress
import socket
import struct
import sys
import threading
import time
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from aarogya_contracts import HardwareCapabilityManifest, NodeTier, WatchMode

MDNS_SERVICE_TYPE = "_aarogya-mesh._tcp.local."
PeerSource = Literal["sync_http", "sync_ws", "mdns"]

_RFC1918_ROUTE_PROBES: tuple[tuple[str, int], ...] = (
    ("10.255.255.255", 1),
    ("192.168.0.1", 1),
    ("172.16.0.1", 1),
)


class PeerRecord(BaseModel):
    """Summary of a mesh peer node observed by the Tier-2 PHC Hub."""

    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., min_length=1, max_length=128)
    tier: NodeTier
    ram_mb: int = Field(..., ge=1)
    cpu_cores: int = Field(..., ge=1)
    battery_pct: int = Field(default=100, ge=0, le=100)
    watch_mode: WatchMode | None = None
    last_seen_ms: int = Field(..., ge=0)
    source: PeerSource
    sync_count: int = Field(default=1, ge=1)


class ConnectInfo(BaseModel):
    """Offline LAN/Hotspot connection metadata for pairing Tier-0/Tier-1 devices."""

    model_config = ConfigDict(extra="forbid")

    hub_node_id: str = Field(..., min_length=1, max_length=128)
    tier: NodeTier
    lan_ip: str = Field(..., min_length=7, max_length=45)
    port: int = Field(..., ge=1, le=65535)
    preferred_url: str | None = None
    http_url: str
    ws_url: str
    mdns_service: str
    mdns_active: bool
    field_pwa_hint: str
    watch_companion_hint: str


class PeerRegistry:
    """Thread-safe in-memory registry of peers seen via HTTP sync, WS mesh, or mDNS."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._peers: dict[str, PeerRecord] = {}

    def record_peer(
        self,
        manifest: HardwareCapabilityManifest,
        source: PeerSource = "sync_http",
        *,
        now_ms: int | None = None,
    ) -> PeerRecord:
        """Upsert a peer from its HardwareCapabilityManifest and increment sync_count."""
        timestamp_ms = int(time.time() * 1000) if now_ms is None else now_ms
        with self._lock:
            existing = self._peers.get(manifest.node_id)
            next_count = (existing.sync_count + 1) if existing is not None else 1
            record = PeerRecord(
                node_id=manifest.node_id,
                tier=manifest.tier,
                ram_mb=manifest.ram_mb,
                cpu_cores=manifest.cpu_cores,
                battery_pct=manifest.battery_pct,
                watch_mode=manifest.watch_mode,
                last_seen_ms=timestamp_ms,
                source=source,
                sync_count=next_count,
            )
            self._peers[manifest.node_id] = record
            return record

    def list_peers(self) -> list[PeerRecord]:
        """Return all observed peers sorted by last_seen_ms descending (node_id tie-break)."""
        with self._lock:
            records = list(self._peers.values())
        records.sort(key=lambda peer: (-peer.last_seen_ms, peer.node_id))
        return records

    def get_peer(self, node_id: str) -> PeerRecord | None:
        """Return a single peer by node_id, or None if unseen."""
        with self._lock:
            return self._peers.get(node_id)

    def count(self) -> int:
        """Return the number of distinct peers tracked."""
        with self._lock:
            return len(self._peers)


_IGNORED_IFACE_PREFIXES: tuple[str, ...] = (
    "lo",
    "docker",
    "virbr",
    "br-",
    "veth",
    "podman",
    "lxc",
    "cni",
    "flannel",
)
_DOCKER_DEFAULT_NET = ipaddress.IPv4Network("172.17.0.0/16")
_SIOCGIFCONF = 0x8912
_SIOCGIFFLAGS = 0x8913
_IFF_UP = 0x1
_IFF_LOOPBACK = 0x8
_IFF_RUNNING = 0x40


def _is_usable_lan_ipv4(candidate: str) -> bool:
    """Return True if candidate is a routable local IPv4 (not loopback/unspecified/link-local)."""
    try:
        addr = ipaddress.IPv4Address(candidate)
    except ValueError:
        return False
    return not (addr.is_loopback or addr.is_unspecified or addr.is_link_local)


def _is_ignored_interface(name: str) -> bool:
    """Return True for loopback, docker, libvirt, and container bridge interfaces."""
    lowered = name.strip().lower()
    return any(lowered.startswith(prefix) for prefix in _IGNORED_IFACE_PREFIXES)


def _is_docker_default_ip(candidate: str) -> bool:
    """Return True if candidate falls inside the default Docker bridge subnet 172.17.0.0/16."""
    try:
        return ipaddress.IPv4Address(candidate) in _DOCKER_DEFAULT_NET
    except ValueError:
        return False


def _enumerate_linux_lan_ipv4s() -> list[str]:
    """Enumerate active non-virtual IPv4 addresses on Linux via SIOCGIFCONF + SIOCGIFFLAGS."""
    if not sys.platform.startswith("linux"):
        return []
    try:
        import fcntl
    except ImportError:
        return []

    ifreq_size = 40 if struct.calcsize("P") == 8 else 32
    max_bytes = 8192
    candidates: list[tuple[bool, bool, str]] = []

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            buf = array.array("B", b"\0" * max_bytes)
            addr_ptr, _buf_len = buf.buffer_info()
            ifconf = struct.pack("iL", max_bytes, addr_ptr)
            res = fcntl.ioctl(sock.fileno(), _SIOCGIFCONF, ifconf)
            out_bytes = struct.unpack("iL", res)[0]
            raw = buf.tobytes()[:out_bytes]

            for offset in range(0, len(raw), ifreq_size):
                if offset + 24 > len(raw):
                    break
                iface_name = raw[offset : offset + 16].split(b"\0", 1)[0].decode(
                    "utf-8", errors="ignore"
                )
                if not iface_name or _is_ignored_interface(iface_name):
                    continue
                ip_str = socket.inet_ntoa(raw[offset + 20 : offset + 24])
                if not _is_usable_lan_ipv4(ip_str) or _is_docker_default_ip(ip_str):
                    continue

                flags_req = struct.pack("256s", iface_name.encode("utf-8"))
                flags_res = fcntl.ioctl(sock.fileno(), _SIOCGIFFLAGS, flags_req)
                flags = struct.unpack("H", flags_res[16:18])[0]
                if not (flags & _IFF_UP) or (flags & _IFF_LOOPBACK):
                    continue

                is_running = bool(flags & _IFF_RUNNING)
                is_private = ipaddress.IPv4Address(ip_str).is_private
                candidates.append((is_running, is_private, ip_str))
    except (OSError, AttributeError, ValueError):
        return []

    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [ip_str for _run, _priv, ip_str in candidates]


def detect_lan_ipv4() -> str:
    """Best-effort pure-stdlib LAN/Hotspot IPv4 detection with zero external requests.

    Enumerates active local interfaces first (ignoring loopback, DOWN, docker0,
    and virbr* interfaces), then falls back to RFC1918 UDP routing-table probes
    and hostname resolution, and finally ``127.0.0.1``.
    """
    iface_ips = _enumerate_linux_lan_ipv4s()
    if iface_ips:
        return iface_ips[0]

    for probe_ip, probe_port in _RFC1918_ROUTE_PROBES:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(0.0)
                sock.connect((probe_ip, probe_port))
                local_ip = sock.getsockname()[0]
            if _is_usable_lan_ipv4(local_ip) and not _is_docker_default_ip(local_ip):
                return local_ip
        except OSError:
            continue

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            candidate = str(info[4][0])
            if _is_usable_lan_ipv4(candidate) and not _is_docker_default_ip(candidate):
                return candidate
    except OSError:
        pass

    return "127.0.0.1"


class MdnsAdvertiser:
    """Fail-soft mDNS advertiser for ``_aarogya-mesh._tcp.local.``.

    Uses optional ``zeroconf`` when installed and ``enabled=True``. Cleanly
    no-ops with ``mdns_active=False`` if ``zeroconf`` is absent, disabled, or
    the host is air-gapped / blocks multicast sockets.
    """

    def __init__(
        self,
        manifest: HardwareCapabilityManifest,
        *,
        port: int = 8000,
        lan_ip: str | None = None,
        enabled: bool = False,
        service_type: str = MDNS_SERVICE_TYPE,
    ) -> None:
        self._manifest = manifest
        self.port = port
        self._lan_ip = lan_ip
        self.enabled = enabled
        self._service_type = service_type
        self._active = False
        self._zeroconf: Any = None
        self._service_info: Any = None

    @property
    def mdns_active(self) -> bool:
        """Whether mDNS advertisement is currently active on the local network."""
        return self._active

    @property
    def service_type(self) -> str:
        """The mDNS service type advertised by this Hub."""
        return self._service_type

    def start(self) -> bool:
        """Start mDNS advertisement if enabled; fail-soft to False on any error."""
        if not self.enabled:
            self._active = False
            return False
        if self._active:
            return True

        zc: Any = None
        try:
            zeroconf_mod = importlib.import_module("zeroconf")
            service_info_cls = zeroconf_mod.ServiceInfo
            zeroconf_cls = zeroconf_mod.Zeroconf

            advertise_ip = self._lan_ip or detect_lan_ipv4()
            service_name = f"{self._manifest.node_id}.{self._service_type}"
            properties = {
                "node_id": self._manifest.node_id,
                "tier": self._manifest.tier.value,
                "ram_mb": str(self._manifest.ram_mb),
                "schema_version": "1.0",
            }
            info = service_info_cls(
                type_=self._service_type,
                name=service_name,
                addresses=[socket.inet_aton(advertise_ip)],
                port=self.port,
                properties=properties,
            )
            zc = zeroconf_cls()
            zc.register_service(info)
            self._zeroconf = zc
            self._service_info = info
            self._active = True
            return True
        except Exception:
            if zc is not None:
                try:
                    zc.close()
                except Exception:
                    pass
            self._zeroconf = None
            self._service_info = None
            self._active = False
            return False

    def stop(self) -> None:
        """Stop mDNS advertisement cleanly (idempotent and fail-soft)."""
        zc = self._zeroconf
        info = self._service_info
        self._zeroconf = None
        self._service_info = None
        self._active = False
        if zc is None:
            return
        try:
            if info is not None:
                zc.unregister_service(info)
        except Exception:
            pass
        try:
            zc.close()
        except Exception:
            pass

    def __enter__(self) -> MdnsAdvertiser:
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()


def create_discovery_router(
    registry: PeerRegistry,
    manifest: HardwareCapabilityManifest,
    port: int = 8000,
    mdns_advertiser: MdnsAdvertiser | None = None,
) -> APIRouter:
    """Build the FastAPI router exposing peer discovery and offline connect info."""
    router = APIRouter(tags=["discovery"])

    @router.get("/api/v1/peers", response_model=list[PeerRecord])
    def list_peers() -> list[PeerRecord]:
        return registry.list_peers()

    @router.get("/api/v1/discovery/connect-info", response_model=ConnectInfo)
    def get_connect_info() -> ConnectInfo:
        lan_ip = detect_lan_ipv4()
        http_url = f"http://{lan_ip}:{port}"
        preferred_url = http_url if _is_usable_lan_ipv4(lan_ip) else None
        ws_url = f"ws://{lan_ip}:{port}/ws/mesh"
        service_type = (
            mdns_advertiser.service_type if mdns_advertiser is not None else MDNS_SERVICE_TYPE
        )
        mdns_active = mdns_advertiser.mdns_active if mdns_advertiser is not None else False
        return ConnectInfo(
            hub_node_id=manifest.node_id,
            tier=manifest.tier,
            lan_ip=lan_ip,
            port=port,
            preferred_url=preferred_url,
            http_url=http_url,
            ws_url=ws_url,
            mdns_service=service_type,
            mdns_active=mdns_active,
            field_pwa_hint=f"Set Field PWA Hub URL to {http_url} (same Wi-Fi / hotspot).",
            watch_companion_hint=(
                f"Connect Watch Companion to {ws_url} or discover {service_type} on LAN."
            ),
        )

    return router
