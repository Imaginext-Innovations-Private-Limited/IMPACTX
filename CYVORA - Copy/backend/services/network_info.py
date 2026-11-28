"""Describe the machine's capture interfaces and the Wi-Fi network in use.

The Live capture panel has to name the adapter it records from. TShark only
reports a numbered device, so this module asks Windows which Wi-Fi network the
matching adapter is joined to and returns that network's real name. Nothing is
invented: an adapter with no joined network simply has no name.
"""

import re
import subprocess
import sys
import time

TSHARK_PATH = r"C:\Program Files\Wireshark\tshark.exe"
TIMEOUT_SECONDS = 10

# Listing adapters costs a TShark start-up, so the answer is reused; adapters
# and the joined Wi-Fi network change far less often than the dashboard polls.
CACHE_TTL_SECONDS = 120

# The backend is windowless, so helper processes must not open a console
# window (it would flash in front of the dashboard and take focus).
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
_cache = {}

# "4. \Device\NPF_{GUID} (Wi-Fi)" -> id 4, device, friendly name "Wi-Fi"
_INTERFACE_LINE = re.compile(r"^(\d+)\.\s+(.*?)\s*(?:\((.*)\))?$")


def capture_interfaces():
    """TShark's interface list as [{id, name}]. Never raises."""
    try:
        result = subprocess.run(
            [TSHARK_PATH, "-D"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            check=False,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    interfaces = []

    for line in (result.stdout or "").splitlines():
        match = _INTERFACE_LINE.match(line.strip())

        if not match:
            continue

        device = (match.group(2) or "").strip()
        friendly = (match.group(3) or "").strip()

        interfaces.append({
            "id": match.group(1),
            "name": friendly or device,
        })

    return interfaces


def _wifi_networks():
    """{adapter name: details} for Wi-Fi adapters that are joined to a network."""
    if sys.platform != "win32":
        return {}

    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            check=False,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return {}

    # Blocks are separated by blank lines; each block is "Key : value" lines.
    blocks = []
    current = {}

    for line in (result.stdout or "").splitlines():
        text = line.strip()

        if not text:
            if current:
                blocks.append(current)
            current = {}
            continue

        if ":" not in text:
            continue

        key, value = text.split(":", 1)
        current[key.strip()] = value.strip()

    if current:
        blocks.append(current)

    joined = {}

    for details in blocks:
        name = details.get("Name")
        ssid = details.get("SSID")

        if not name or not ssid:
            continue

        if details.get("State", "").lower() != "connected":
            continue

        joined[name] = {
            "ssid": ssid,
            "signal": details.get("Signal"),
            "band": details.get("Band"),
        }

    return joined


def describe_interfaces():
    """Capture interfaces, each with the Wi-Fi network it is joined to."""
    cached = _cache.get("interfaces")
    now = time.monotonic()

    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    result = _describe_interfaces()
    _cache["interfaces"] = (now, result)

    return result


def _describe_interfaces():
    networks = _wifi_networks()
    interfaces = []
    primary = None

    for item in capture_interfaces():
        entry = {"id": item["id"], "name": item["name"]}
        details = networks.get(item["name"])

        if details:
            entry["wifi_name"] = details["ssid"]

            if details.get("signal"):
                entry["signal"] = details["signal"]

            if details.get("band"):
                entry["band"] = details["band"]

            if primary is None:
                primary = entry

        interfaces.append(entry)

    return {
        "interfaces": interfaces,
        "ssid": primary["wifi_name"] if primary else None,
        "interface_id": primary["id"] if primary else None,
        "adapter": primary["name"] if primary else None,
    }
