
"""Registry of planned and existing honeypot service ports."""

SERVICE_REGISTRY = {
    21: {"name": "FTP", "category": "remote_access", "status": "implemented_tested"},
    22: {"name": "SSH", "category": "remote_access", "status": "existing_cowrie_test_port_2222"},
    23: {"name": "Telnet", "category": "remote_access", "status": "implemented_tested"},
    25: {"name": "SMTP", "category": "email", "status": "implemented_tested"},
    53: {"name": "DNS", "category": "network", "status": "implemented_tested_udp_only"},
    80: {"name": "HTTP", "category": "web", "status": "existing_flask_test_port_5000"},
    110: {"name": "POP3", "category": "email", "status": "implemented_tested"},
    135: {"name": "MS RPC", "category": "windows", "status": "tcp_logger_test_port_1135"},
    139: {"name": "NetBIOS", "category": "windows", "status": "planned"},
    143: {"name": "IMAP", "category": "email", "status": "implemented_tested"},
    443: {"name": "HTTPS", "category": "web", "status": "implemented_tested_test_port_18443"},
    445: {"name": "SMB", "category": "windows", "status": "tcp_logger_test_port_1445"},
    3306: {"name": "MySQL", "category": "databases", "status": "implemented_tested_simulator"},
    3389: {"name": "RDP", "category": "windows", "status": "tcp_logger_test_port_13389"},
    5432: {"name": "PostgreSQL", "category": "databases", "status": "implemented_tested_simulator"},
    5900: {"name": "VNC", "category": "windows", "status": "tcp_logger_test_port_15900"},
    8080: {"name": "Alternate HTTP", "category": "web", "status": "implemented_tested_test_port_18081"},
}


def get_service(port):
    """Return service metadata for a port, or None if unregistered."""
    return SERVICE_REGISTRY.get(int(port))


def list_services():
    """Return a copy of the registered service metadata."""
    return {
        port: details.copy()
        for port, details in SERVICE_REGISTRY.items()
    }
