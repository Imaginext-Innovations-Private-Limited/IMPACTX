
import csv
import io
import subprocess
import sys

from backend.services.flow_features import extract_all_flows


TSHARK_PATH = r"C:\Program Files\Wireshark\tshark.exe"

# Capture runs from a windowless backend, so TShark must not create a console
# of its own: that window appears in front of the dashboard and takes focus.
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# Wi-Fi adapter identified by TShark -D
DEFAULT_INTERFACE = "4"

FIELDS = [
    "frame.time_epoch",
    "ip.src",
    "ipv6.src",
    "ip.dst",
    "ipv6.dst",
    "tcp.srcport",
    "udp.srcport",
    "tcp.dstport",
    "udp.dstport",
    "frame.len",
    "ip.proto",
    "ipv6.nxt",
    "tcp.flags",
    "dns.qry.name",
    "dns.a",
    "dns.aaaa",
]


def _dns_answers(ipv4_field, ipv6_field):
    """Split TShark's comma-separated answer lists into distinct addresses."""
    answers = []

    for field in (ipv4_field, ipv6_field):
        for value in (field or "").split(","):
            value = value.strip()

            if value and value not in answers:
                answers.append(value)

    return answers


def _kill_capture_tree(process):
    """Stop TShark and the dumpcap child that holds the adapter.

    Killing only the parent leaves dumpcap recording in the background, which
    makes the next capture wait forever for the interface.
    """
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True,
                timeout=15,
                check=False,
                creationflags=CREATE_NO_WINDOW,
            )
            return
        except (OSError, subprocess.SubprocessError):
            pass

    try:
        process.kill()
    except OSError:
        pass


def _run_capture(command, timeout):
    """Run TShark, stopping the whole capture tree if it overruns."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )

    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_capture_tree(process)

        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            pass

        raise RuntimeError(
            "TShark did not finish in time. Close any other capture (Wireshark "
            "or a second CYVORA capture) and try again."
        )

    return process.returncode, stdout, stderr


def capture_packets(interface=DEFAULT_INTERFACE, duration=30):
    """Capture live packets and return structured packet records."""

    command = [
        TSHARK_PATH,
        "-i", str(interface),
        "-a", f"duration:{int(duration)}",
        "-T", "fields",
        "-E", "separator=\t",
        "-E", "quote=d",
        # Keep every DNS answer record, so a name can be matched to any of the
        # addresses a response actually returned.
        "-E", "occurrence=a",
    ]

    for field in FIELDS:
        command.extend(["-e", field])

    # Starting TShark and tearing the capture down costs several seconds on
    # Windows, so the deadline allows well beyond the recording time itself.
    returncode, stdout, stderr = _run_capture(command, int(duration) + 45)

    if returncode != 0:
        raise RuntimeError(stderr.strip() or "TShark capture failed")

    packets = []

    for row in csv.reader(
        io.StringIO(stdout),
        delimiter="\t",
        quotechar='"',
    ):
        if len(row) != len(FIELDS):
            continue

        data = dict(zip(FIELDS, row))

        try:
            timestamp = float(data["frame.time_epoch"])
            length = int(data["frame.len"])
        except (ValueError, TypeError):
            continue

        source = data["ip.src"] or data["ipv6.src"]
        destination = data["ip.dst"] or data["ipv6.dst"]

        if not source or not destination:
            continue

        tcp_src = data["tcp.srcport"]
        udp_src = data["udp.srcport"]
        tcp_dst = data["tcp.dstport"]
        udp_dst = data["udp.dstport"]

        if tcp_src or tcp_dst:
            protocol = "TCP"
            source_port = tcp_src
            destination_port = tcp_dst
        elif udp_src or udp_dst:
            protocol = "UDP"
            source_port = udp_src
            destination_port = udp_dst
        else:
            protocol = (
                data["ip.proto"]
                or data["ipv6.nxt"]
                or "OTHER"
            )
            source_port = None
            destination_port = None

        packets.append({
            "timestamp": timestamp,
            "src_ip": source,
            "dst_ip": destination,
            "src_port": source_port or None,
            "dst_port": destination_port or None,
            "protocol": protocol,
            "length": length,
            "tcp_flags": data["tcp.flags"] or None,
            "dns_query": data["dns.qry.name"] or None,
            # Answer records from the response, so the map can label an
            # observed address with the name the device resolved for it.
            "dns_answers": _dns_answers(data["dns.a"], data["dns.aaaa"]),
        })

    return packets


def capture_and_extract(interface=DEFAULT_INTERFACE, duration=30):
    """Capture packets and extract detector-specific flow features."""

    packets = capture_packets(
        interface=interface,
        duration=duration,
    )

    if not packets:
        return {
            "packet_count": 0,
            "flow_count": 0,
            "flows": [],
        }

    flows = extract_all_flows(packets)

    return {
        "packet_count": len(packets),
        "flow_count": len(flows),
        "flows": flows,
    }
