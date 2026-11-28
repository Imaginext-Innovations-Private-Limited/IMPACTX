"""Unit and API tests for Tier-2 PHC Hub mDNS discovery and peer registry."""

from __future__ import annotations

import ipaddress
import socket
import threading
import types
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from aarogya_contracts import HardwareCapabilityManifest, NodeTier, WatchMode
from aarogya_phc_hub import discovery
from aarogya_phc_hub.discovery import (
    MDNS_SERVICE_TYPE,
    ConnectInfo,
    MdnsAdvertiser,
    PeerRecord,
    PeerRegistry,
    create_discovery_router,
    detect_lan_ipv4,
)


def _hub_manifest(node_id: str = "phc-hub-01") -> HardwareCapabilityManifest:
    return HardwareCapabilityManifest(
        node_id=node_id,
        tier=NodeTier.TIER_2_HUB,
        ram_mb=16384,
        cpu_cores=8,
        battery_pct=100,
    )


def _phone_manifest(
    node_id: str = "phone-asha-01",
    *,
    battery_pct: int = 85,
) -> HardwareCapabilityManifest:
    return HardwareCapabilityManifest(
        node_id=node_id,
        tier=NodeTier.TIER_1_PHONE,
        ram_mb=4096,
        cpu_cores=8,
        battery_pct=battery_pct,
    )


def _watch_manifest(
    node_id: str = "watch-asha-01",
    *,
    watch_mode: WatchMode = WatchMode.CHW_COMPANION,
) -> HardwareCapabilityManifest:
    return HardwareCapabilityManifest(
        node_id=node_id,
        tier=NodeTier.TIER_0_WATCH,
        ram_mb=256,
        cpu_cores=2,
        battery_pct=70,
        watch_mode=watch_mode,
    )


def test_peer_record_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        PeerRecord(
            node_id="phone-01",
            tier=NodeTier.TIER_1_PHONE,
            ram_mb=4096,
            cpu_cores=8,
            battery_pct=80,
            last_seen_ms=1_700_000_000_000,
            source="sync_http",
            sync_count=1,
            unexpected_field="boom",  # type: ignore[call-arg]
        )


def test_peer_registry_upsert_ordering_and_sync_count() -> None:
    registry = PeerRegistry()
    assert registry.list_peers() == []
    assert registry.count() == 0

    phone = _phone_manifest("phone-01", battery_pct=90)
    watch = _watch_manifest("watch-01", watch_mode=WatchMode.CHW_COMPANION)

    first = registry.record_peer(phone, source="sync_http", now_ms=1000)
    assert first.sync_count == 1
    assert first.source == "sync_http"
    assert first.battery_pct == 90

    registry.record_peer(watch, source="sync_ws", now_ms=2000)
    peers = registry.list_peers()
    assert [p.node_id for p in peers] == ["watch-01", "phone-01"]
    assert peers[0].watch_mode == WatchMode.CHW_COMPANION

    # Re-recording phone updates fields, increments sync_count, and moves it to top.
    phone_updated = _phone_manifest("phone-01", battery_pct=65)
    second = registry.record_peer(phone_updated, source="mdns", now_ms=3000)
    assert second.sync_count == 2
    assert second.battery_pct == 65
    assert second.source == "mdns"

    peers_after = registry.list_peers()
    assert registry.count() == 2
    assert [p.node_id for p in peers_after] == ["phone-01", "watch-01"]
    assert peers_after[0].sync_count == 2
    assert registry.get_peer("phone-01") == second
    assert registry.get_peer("unknown-node") is None


def test_peer_registry_thread_safety() -> None:
    registry = PeerRegistry()
    phone = _phone_manifest("phone-concurrent")
    errors: list[Exception] = []

    def worker() -> None:
        try:
            for _ in range(25):
                registry.record_peer(phone, source="sync_http")
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    record = registry.get_peer("phone-concurrent")
    assert record is not None
    assert record.sync_count == 100


def test_detect_lan_ipv4_returns_valid_ipv4_and_falls_back_cleanly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detected = detect_lan_ipv4()
    # Must always be a syntactically valid IPv4 address.
    assert isinstance(ipaddress.IPv4Address(detected), ipaddress.IPv4Address)

    # Simulate completely air-gapped environment where socket probes & DNS fail.
    class _BrokenSocket:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        def __enter__(self) -> _BrokenSocket:
            return self

        def __exit__(self, *_exc: Any) -> None:
            return None

        def settimeout(self, _timeout: float) -> None:
            return None

        def connect(self, _addr: tuple[str, int]) -> None:
            raise OSError("Network is unreachable")

    monkeypatch.setattr(socket, "socket", _BrokenSocket)
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("No hostname")),
    )
    assert detect_lan_ipv4() == "127.0.0.1"


def test_mdns_advertiser_disabled_and_missing_zeroconf_are_fail_soft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _hub_manifest()

    # Disabled advertiser is a clean no-op.
    disabled = MdnsAdvertiser(manifest, port=8000, enabled=False)
    assert disabled.mdns_active is False
    assert disabled.service_type == MDNS_SERVICE_TYPE
    assert disabled.start() is False
    assert disabled.mdns_active is False
    disabled.stop()  # idempotent

    # Enabled advertiser when zeroconf is not installed fails soft.
    def _missing_zeroconf(name: str) -> Any:
        raise ImportError(f"No module named {name!r}")

    monkeypatch.setattr(discovery.importlib, "import_module", _missing_zeroconf)
    missing = MdnsAdvertiser(manifest, port=8000, enabled=True)
    assert missing.start() is False
    assert missing.mdns_active is False
    missing.stop()


def test_mdns_advertiser_registers_and_unregisters_with_mock_zeroconf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, Any]] = []

    class _FakeServiceInfo:
        def __init__(
            self,
            *,
            type_: str,
            name: str,
            addresses: list[bytes],
            port: int,
            properties: dict[str, str],
        ) -> None:
            self.type_ = type_
            self.name = name
            self.addresses = addresses
            self.port = port
            self.properties = properties

    class _FakeZeroconf:
        def register_service(self, info: _FakeServiceInfo) -> None:
            events.append(("register", info))

        def unregister_service(self, info: _FakeServiceInfo) -> None:
            events.append(("unregister", info))

        def close(self) -> None:
            events.append(("close", None))

    fake_mod = types.SimpleNamespace(ServiceInfo=_FakeServiceInfo, Zeroconf=_FakeZeroconf)
    monkeypatch.setattr(discovery.importlib, "import_module", lambda _name: fake_mod)

    manifest = _hub_manifest("phc-hub-mdns")
    advertiser = MdnsAdvertiser(manifest, port=8123, lan_ip="192.168.43.1", enabled=True)
    assert advertiser.start() is True
    assert advertiser.mdns_active is True
    # Calling start() twice is a no-op.
    assert advertiser.start() is True
    assert len(events) == 1

    action, info = events[0]
    assert action == "register"
    assert info.type_ == MDNS_SERVICE_TYPE
    assert info.name == f"phc-hub-mdns.{MDNS_SERVICE_TYPE}"
    assert info.port == 8123
    assert info.addresses == [socket.inet_aton("192.168.43.1")]
    assert info.properties["node_id"] == "phc-hub-mdns"
    assert info.properties["tier"] == "TIER_2_HUB"

    advertiser.stop()
    assert advertiser.mdns_active is False
    assert [e[0] for e in events] == ["register", "unregister", "close"]
    # Second stop() is a clean no-op.
    advertiser.stop()
    assert len(events) == 3


def test_discovery_router_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = PeerRegistry()
    manifest = _hub_manifest("phc-hub-demo")
    advertiser = MdnsAdvertiser(manifest, port=8000, enabled=False)

    app = FastAPI()
    app.include_router(
        create_discovery_router(
            registry=registry,
            manifest=manifest,
            port=8000,
            mdns_advertiser=advertiser,
        )
    )
    client = TestClient(app)

    # Empty peer list initially.
    resp_empty = client.get("/api/v1/peers")
    assert resp_empty.status_code == 200
    assert resp_empty.json() == []

    # Record a phone via HTTP sync and a watch via WS sync.
    registry.record_peer(_phone_manifest("phone-01"), source="sync_http", now_ms=10_000)
    registry.record_peer(
        _watch_manifest("watch-01", watch_mode=WatchMode.PATIENT_FAMILY),
        source="sync_ws",
        now_ms=20_000,
    )

    resp_peers = client.get("/api/v1/peers")
    assert resp_peers.status_code == 200
    peers = [PeerRecord.model_validate(item) for item in resp_peers.json()]
    assert [p.node_id for p in peers] == ["watch-01", "phone-01"]
    assert peers[0].source == "sync_ws"
    assert peers[0].watch_mode == WatchMode.PATIENT_FAMILY
    assert peers[1].source == "sync_http"
    assert peers[1].watch_mode is None

    # Connect info returns deterministic offline URLs and hints.
    monkeypatch.setattr(discovery, "detect_lan_ipv4", lambda: "192.168.43.10")
    resp_info = client.get("/api/v1/discovery/connect-info")
    assert resp_info.status_code == 200
    info = ConnectInfo.model_validate(resp_info.json())
    assert info.hub_node_id == "phc-hub-demo"
    assert info.tier == NodeTier.TIER_2_HUB
    assert info.lan_ip == "192.168.43.10"
    assert info.port == 8000
    assert info.preferred_url == "http://192.168.43.10:8000"
    assert info.http_url == "http://192.168.43.10:8000"
    assert info.ws_url == "ws://192.168.43.10:8000/ws/mesh"
    assert info.mdns_service == MDNS_SERVICE_TYPE
    assert info.mdns_active is False
    assert "http://192.168.43.10:8000" in info.field_pwa_hint
    assert "ws://192.168.43.10:8000/ws/mesh" in info.watch_companion_hint

    # Loopback-only host yields preferred_url=None instead of advertising 127.0.0.1 as LAN.
    monkeypatch.setattr(discovery, "detect_lan_ipv4", lambda: "127.0.0.1")
    resp_loopback = client.get("/api/v1/discovery/connect-info")
    assert resp_loopback.status_code == 200
    loopback_info = ConnectInfo.model_validate(resp_loopback.json())
    assert loopback_info.lan_ip == "127.0.0.1"
    assert loopback_info.preferred_url is None


def test_detect_lan_ipv4_offline_interface_enumeration_filters_virtual_and_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fcntl
    import struct

    ifreq_size = 40 if struct.calcsize("P") == 8 else 32
    entries = [
        ("lo", "127.0.0.1", 0x49),           # UP | LOOPBACK | RUNNING -> ignored
        ("docker0", "172.17.0.1", 0x1043),   # docker* + 172.17.* -> ignored
        ("virbr0", "192.168.122.1", 0x1043), # virbr* -> ignored
        ("eth0", "10.0.0.5", 0x0),           # DOWN -> ignored
        ("wlan0", "192.168.43.1", 0x1043),   # UP | RUNNING -> selected
    ]
    raw_buf = bytearray()
    flag_map: dict[str, int] = {}
    for name, ip_str, flags in entries:
        rec = bytearray(ifreq_size)
        name_bytes = name.encode("utf-8")[:15]
        rec[: len(name_bytes)] = name_bytes
        rec[20:24] = socket.inet_aton(ip_str)
        raw_buf.extend(rec)
        flag_map[name] = flags

    class _FakeIoctlSocket:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        def __enter__(self) -> _FakeIoctlSocket:
            return self

        def __exit__(self, *_exc: Any) -> None:
            return None

        def fileno(self) -> int:
            return 99

        def settimeout(self, _timeout: float) -> None:
            return None

        def connect(self, _addr: tuple[str, int]) -> None:
            raise OSError("Network is unreachable")

    def _fake_ioctl(_fd: int, req: int, arg: bytes) -> bytes:
        if req == discovery._SIOCGIFCONF:
            _buf_len, addr_ptr = struct.unpack("iL", arg)
            import ctypes

            ctypes.memmove(addr_ptr, bytes(raw_buf), len(raw_buf))
            return struct.pack("iL", len(raw_buf), addr_ptr)
        if req == discovery._SIOCGIFFLAGS:
            iface_name = arg[:16].split(b"\0", 1)[0].decode("utf-8")
            flags = flag_map.get(iface_name, 0)
            out = bytearray(256)
            out[16:18] = struct.pack("H", flags)
            return bytes(out)
        raise OSError("Unsupported ioctl")

    monkeypatch.setattr(sys := discovery.sys, "platform", "linux")
    monkeypatch.setattr(socket, "socket", _FakeIoctlSocket)
    monkeypatch.setattr(fcntl, "ioctl", _fake_ioctl)
    assert sys.platform == "linux"
    assert detect_lan_ipv4() == "192.168.43.1"
