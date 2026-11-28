"""Privacy-preserving SSH command classification."""

import re


def classify_ssh_command(raw_command):
    """Convert raw SSH input into a safe, fixed behavior category."""

    command = str(raw_command or "").lower().strip()

    if not command:
        return None

    # Already-classified safe labels
    safe_labels = {
        "read_sensitive_file",
        "download_attempt",
        "network_request",
        "privilege_modification",
        "interactive_shell",
        "reverse_shell_attempt",
        "identity_check",
        "directory_check",
        "session_exit",
        "other_command",
    }

    if command in safe_labels:
        return command

    # Sensitive file access
    if re.search(
        r"\b(?:cat|less|more|head|tail|grep)\b.*"
        r"(?:/etc/passwd|/etc/shadow|\.ssh/)",
        command,
    ):
        return "read_sensitive_file"

    # Download attempts
    if re.search(r"\b(?:wget|curl)\b", command):
        return "download_attempt" if command.startswith("wget ") else "network_request"

    # Privilege modification
    if re.search(r"\b(?:chmod|chown|useradd|usermod|passwd|sudo)\b", command):
        return "privilege_modification"

    # Shell and reverse-shell behavior
    if re.search(r"\bbash\s+-i\b", command):
        return "interactive_shell"

    if re.search(r"\b(?:nc|netcat)\b.*(?:-e|-c)", command):
        return "reverse_shell_attempt"

    # Reconnaissance / identity
    first_token = command.split()[0].split("/")[-1]

    if first_token in {"whoami", "id"}:
        return "identity_check"

    if first_token in {"pwd", "ls", "find", "tree"}:
        return "directory_check"

    if first_token in {"exit", "logout"}:
        return "session_exit"

    return "other_command"
