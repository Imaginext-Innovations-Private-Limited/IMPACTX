"""Find which local process owns each connection or UDP socket.

The map lists the remote locations a capture reached. This module answers the
"which application opened that connection" part by reading the operating
system's live connection table, so the answer comes from the machine itself
rather than being guessed.

Windows only: Get-NetTCPConnection and Get-NetUDPEndpoint report the owning
PID, which is resolved to a process name. Anywhere else, or if the query
fails, no attribution is returned and the UI says so instead of inventing an
application.

A capture is short and many connections are shorter, so the table is sampled
while the capture runs. Closed TCP connections are still listed in their
lingering states (TimeWait and friends), which is what makes short requests
attributable. UDP sockets are recorded by their local port, because that is
the only thing the table knows about them; QUIC traffic is matched that way.
"""

import json
import subprocess
import sys
import threading

TIMEOUT_SECONDS = 12
SAMPLE_INTERVAL_SECONDS = 3.0

# A windowless backend gives every console helper its own window, which flashes
# up mid-capture and steals focus from the dashboard. CREATE_NO_WINDOW keeps the
# query invisible; 0 is a no-op away from Windows.
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# Every TCP state a connection can be in once a handshake has started.
# Listening sockets are excluded: they own a local port without a peer, so
# they cannot describe a captured flow.
TCP_STATES = (
    "Established,SynSent,SynReceived,FinWait1,FinWait2,CloseWait,Closing,"
    "LastAck,TimeWait"
)

# One PowerShell call builds a PID -> process-name table, then emits the TCP
# connections and UDP sockets that own a port, joined against it.
POWERSHELL_SCRIPT = (
    "$procs=@{};"
    "Get-Process | ForEach-Object { $procs[$_.Id]=$_.ProcessName };"
    "& {"
    "Get-NetTCPConnection -State " + TCP_STATES +
    " -ErrorAction SilentlyContinue | ForEach-Object {"
    " [pscustomobject]@{"
    " ip=$_.RemoteAddress;"
    " port=$_.RemotePort;"
    " local_port=$_.LocalPort;"
    " protocol='TCP';"
    " process=$procs[[int]$_.OwningProcess]"
    " }"
    "};"
    "Get-NetUDPEndpoint -ErrorAction SilentlyContinue | ForEach-Object {"
    " [pscustomobject]@{"
    " ip=$null;"
    " port=$null;"
    " local_port=$_.LocalPort;"
    " protocol='UDP';"
    " process=$procs[[int]$_.OwningProcess]"
    " }"
    "}"
    "} | ConvertTo-Json -Compress"
)


def _port(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse(payload):
    if isinstance(payload, dict):
        payload = [payload]

    if not isinstance(payload, list):
        return []

    rows = []

    for item in payload:
        if not isinstance(item, dict):
            continue

        address = item.get("ip")
        process = item.get("process")
        port = _port(item.get("port"))
        local_port = _port(item.get("local_port"))

        if not process or (not address and local_port is None):
            continue

        rows.append({
            "ip": str(address).strip() if address else None,
            "port": port,
            "local_port": local_port,
            "protocol": str(item.get("protocol") or "TCP").strip().upper(),
            "process": str(process).strip(),
        })

    return rows


def lookup_connection_owners():
    """Return one snapshot of the connection table. Never raises.

    Each row is {ip, port, local_port, protocol, process}. UDP rows carry no
    remote address or port, only their local port.
    """
    if sys.platform != "win32":
        return []

    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                POWERSHELL_SCRIPT,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8-sig",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            check=False,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    output = (result.stdout or "").strip()

    if result.returncode != 0 or not output:
        return []

    try:
        return _parse(json.loads(output))
    except ValueError:
        return []


class OwnerSampler:
    """Collects connection-table snapshots while something else runs.

    ``stop()`` returns every row seen, so a connection that opened and closed
    inside the captured window is still attributed to its process.
    """

    def __init__(self, interval=SAMPLE_INTERVAL_SECONDS):
        self._interval = interval
        self._stopped = threading.Event()
        self._rows = []
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._stopped.set()
        self._thread.join(timeout=TIMEOUT_SECONDS + 5)
        return list(self._rows)

    def _run(self):
        while not self._stopped.is_set():
            try:
                self._rows.extend(lookup_connection_owners())
            except Exception:  # A snapshot must never break a capture.
                pass

            self._stopped.wait(self._interval)


def start_owner_sampling(interval=SAMPLE_INTERVAL_SECONDS):
    """Start sampling the connection table in the background."""
    return OwnerSampler(interval).start()
