import re
from urllib.parse import unquote, unquote_plus


def analyze_event(event):
    details = event.get("details") or {}
    domain = str(event.get("domain", "")).lower()
    event_type = str(event.get("event_type", "")).lower()
    service = str(details.get("service", "")).lower()

    score = 0
    indicators = []
    detected_categories = set()

    def add(points, message, category):
        nonlocal score

        if category not in detected_categories:
            score += points
            indicators.append(message)
            detected_categories.add(category)

    def decode(value):
        value = str(value or "")

        for _ in range(2):
            decoded = unquote_plus(value)
            if decoded == value:
                break
            value = decoded

        return value.lower()

    def text_value(key):
        return decode(details.get(key, ""))

    def contains_pattern(text, patterns):
        return any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in patterns
        )

    # Collect request and protocol content.
    query_values = details.get("query_values", [])

    if isinstance(query_values, (list, tuple)):
        query_text = " ".join(decode(v) for v in query_values)
    else:
        query_text = decode(query_values)

    inspected = " ".join([
        text_value("path"),
        text_value("query_string"),
        query_text,
        text_value("payload"),
        text_value("message"),
        text_value("argument"),
        text_value("command"),
    ])

    # --------------------------------------------------
    # WEB DETECTION
    # --------------------------------------------------
    if domain == "web":

        # Path traversal
        if contains_pattern(inspected, [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e",
        ]):
            add(60, "Path traversal pattern", "path_traversal")

        # SQL injection
        sql_patterns = [
            r"\bunion\s+(?:all\s+)?select\b",
            r"\bselect\b.+\bfrom\b",
            r"\bdrop\s+table\b",
            r"\binformation_schema\b",
            r"\bor\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+",
            r"\band\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+",
            r"\bsleep\s*\(",
            r"\bbenchmark\s*\(",
            r"'\s*or\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+",
            r"admin['\"]?\s*--",
        ]

        if contains_pattern(inspected, sql_patterns):
            add(70, "Potential SQL injection detected", "sql_injection")

        # Command injection
        command_patterns = [
            r";\s*(?:cat|id|whoami|uname|wget|curl)\b",
            r"\|\s*(?:cat|id|whoami|bash|sh)\b",
            r"`[^`]+`",
            r"\$\([^)]*\)",
            r"\b(?:nc|netcat)\s+-e\b",
            r"\bbash\s+-i\b",
            r"\bcmd\.exe\b",
            r"\bpowershell(?:\.exe)?\b",
        ]

        if contains_pattern(inspected, command_patterns):
            add(80, "Potential command injection detected", "command_injection")

        # XSS
        xss_patterns = [
            r"<\s*script\b",
            r"javascript\s*:",
            r"onerror\s*=",
            r"onload\s*=",
            r"<\s*iframe\b",
            r"<\s*svg\b",
        ]

        if contains_pattern(inspected, xss_patterns):
            add(60, "Potential cross-site scripting pattern", "xss")

        # Sensitive file discovery
        sensitive_patterns = [
            r"/\.env(?:\b|/)",
            r"/\.git(?:/|$)",
            r"/etc/passwd",
            r"/etc/shadow",
            r"/\.ssh/",
            r"wp-config\.php",
            r"config\.php",
            r"\.bak(?:\b|$)",
        ]

        if contains_pattern(inspected, sensitive_patterns):
            add(40, "Sensitive file discovery attempt", "sensitive_file")

                # Common reconnaissance paths
        path = text_value("path").split("?")[0].rstrip("/") or "/"

        recon_paths = (
            "/wp-admin",
            "/phpmyadmin",
            "/administrator",
            "/.well-known",
            "/server-status",
        )

        if any(
            path == target or path.startswith(target + "/")
            for target in recon_paths
        ):
            add(
                30,
                "Web application reconnaissance",
                "web_recon"
            )
        # Suspicious query parameter names
        suspicious_keys = {
            "cmd", "exec", "command", "file",
            "redirect", "url", "shell",
        }

        keys = details.get("query_keys", [])

        if isinstance(keys, (list, tuple)):
            matched = sorted(
                str(key).lower() for key in keys
                if str(key).lower() in suspicious_keys
            )

            if matched:
                add(
                    20,
                    "Suspicious query keys: " + ", ".join(matched),
                    "suspicious_keys",
                )

    # --------------------------------------------------
    # SSH DETECTION
    # --------------------------------------------------
    elif domain == "ssh":

        command = text_value("command")

        if event_type == "cowrie.login.failed":
            add(30, "Failed SSH login attempt", "ssh_auth_failure")

        elif event_type == "cowrie.login.success":
            add(5, "Simulated SSH login succeeded", "ssh_login")

        ssh_patterns = [
            r"cat\s+/etc/(?:passwd|shadow)",
            r"cat\s+.*\.ssh/",
            r"\bwget\s+https?://",
            r"\bcurl\s+https?://",
            r"\bchmod\s+\+s\b",
            r"\bbash\s+-i\b",
            r"\bnc\s+-e\b",
            r"\bnetcat\s+-e\b",
            r"\buseradd\b",
            r"\bpasswd\b",
            r"\bcrontab\b",
        ]

        suspicious_commands = {
            "read_sensitive_file",
            "download_attempt",
            "network_request",
            "privilege_modification",
            "interactive_shell",
            "reverse_shell_attempt",
        }

        if (
            command in suspicious_commands
            or contains_pattern(command, ssh_patterns)
        ):
            add(60, "Suspicious SSH command or activity", "ssh_command")

    # --------------------------------------------------
    # NETWORK / SERVICE DETECTION
    # --------------------------------------------------
    elif domain == "network":

        command = text_value("command").strip().upper()
        argument = text_value("argument")

        # Authentication failures
        authentication_events = {
            "telnet_authentication_failed": "Telnet",
            "pop3_authentication_failed": "POP3",
            "imap_authentication_failed": "IMAP",
            "mysql_authentication_attempt": "MySQL",
            "postgres_authentication_attempt": "PostgreSQL",
        }

        if event_type in authentication_events:
            protocol = authentication_events[event_type]
            add(40, f"{protocol} authentication failure", "auth_failure")

        elif details.get("authentication_failed"):
            add(40, "Network authentication failure", "auth_failure")

        # FTP
        if service == "ftp_test" or event_type == "ftp_command":

            if command in {"RETR", "STOR", "APPE", "DELE"}:
                if contains_pattern(argument, [
                    r"\.\./",
                    r"/etc/passwd",
                    r"/etc/shadow",
                    r"\.ssh",
                    r"\.env",
                ]):
                    add(60, "FTP sensitive file operation", "ftp_file")

            if command in {"SITE", "EXEC"}:
                add(60, "Potentially dangerous FTP command", "ftp_exec")

        # SMTP
        if service == "smtp_test" or event_type == "smtp_command":

            if command in {"VRFY", "EXPN"}:
                add(30, "SMTP user enumeration", "smtp_enum")

            if command == "RCPT" and "@" not in argument:
                add(15, "Unusual SMTP recipient format", "smtp_recipient")

        # DNS
        if event_type == "dns_query" or service == "dns_test":

            query_name = text_value("query_name").strip(".")
            labels = query_name.split(".") if query_name else []

            if len(query_name) > 100:
                add(30, "Unusually long DNS query name", "dns_long")

            if len(labels) > 5:
                add(30, "Deep DNS subdomain structure", "dns_depth")

            if any(
                len(label) >= 45
                and len(set(label)) >= 10
                and sum(ch.isdigit() for ch in label) / len(label) < 0.8
                for label in labels
            ):
                add(30, "Potential DNS tunneling pattern", "dns_tunnel")

        # Database protocol
        if event_type == "postgres_protocol_rejected":
            add(40, "Unrecognized PostgreSQL protocol version", "postgres_protocol")

        sql_patterns = [
            r"\bunion\s+(?:all\s+)?select\b",
            r"\bdrop\s+table\b",
            r"\binformation_schema\b",
            r"\bor\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+",
            r"\bsleep\s*\(",
            r"\bbenchmark\s*\(",
        ]

        if (
            service in {"mysql_test", "postgres_test"}
            and contains_pattern(inspected, sql_patterns)
        ):
            add(70, "Potential database injection or reconnaissance", "db_injection")

        # Windows protocol simulators
        windows_events = {
            "smb_data_received": "SMB",
            "rdp_data_received": "RDP",
            "vnc_data_received": "VNC",
            "msrpc_data_received": "MS RPC",
        }

        if event_type in windows_events:
            protocol = windows_events[event_type]
            indicators.append(
                f"{protocol} data received; payload not inspected"
            )

        # Generic payload inspection
        generic_patterns = [
            r"\.\./",
            r"/etc/passwd",
            r"/etc/shadow",
            r"union\s+select",
            r"<\s*script\b",
            r"cmd\.exe",
            r"powershell",
        ]

        if (
            contains_pattern(inspected, generic_patterns)
            and not detected_categories
        ):
            add(50, "Suspicious network payload pattern", "network_payload")

        if event_type == "connection_attempt" and not indicators:
            indicators.append("Network service connection observed")

    else:
        return {
            "risk_score": 0,
            "risk_level": "unassessed",
            "indicators": ["No rules configured for this event domain"],
        }

    # --------------------------------------------------
    # FINAL RISK CLASSIFICATION
    # --------------------------------------------------
    score = min(score, 100)

    if score >= 60:
        level = "high"
    elif score >= 30:
        level = "medium"
    else:
        level = "low"

    return {
        "risk_score": score,
        "risk_level": level,
        "indicators": indicators or [
            "No configured suspicious pattern matched"
        ],
    }
