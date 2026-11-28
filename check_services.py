
import socket
from services.registry import list_services

# Test ports used by your current adapters.
TEST_PORTS = {
    2121: "FTP",
    2323: "Telnet",
    2525: "SMTP",
    1053: "DNS (UDP)",
    5000: "Flask HTTP",
    1110: "POP3",
    1135: "MS RPC logger",
    1143: "IMAP",
    13306: "MySQL simulator",
    13389: "RDP logger",
    1445: "SMB logger",
    15432: "PostgreSQL simulator",
    15900: "VNC logger",
    18081: "Alternate HTTP",
    18443: "HTTPS",
    2222: "Cowrie SSH",
}

def tcp_listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except (OSError, TimeoutError):
        return False

def udp_reachable(port):
    # A UDP service may not respond to an arbitrary probe.
    # Do not interpret silence as proof that it is stopped.
    return "UDP status requires a protocol-specific test"

if __name__ == "__main__":
    print("Registered targets:", len(list_services()))
    print("\nLocal test-port status:")
    for port, name in sorted(TEST_PORTS.items()):
        if port == 1053:
            status = udp_reachable(port)
        else:
            status = "LISTENING" if tcp_listening(port) else "NOT LISTENING"
        print(f"{port:>5} | {name:<22} | {status}")

