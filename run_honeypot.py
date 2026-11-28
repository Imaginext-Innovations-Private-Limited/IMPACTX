#!/usr/bin/env python3

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN_DIR = ROOT / "run"
LOG_DIR = ROOT / "logs"

# Cowrie is managed separately using its own virtual environment.
SSH_SERVICES = {
    "dashboard": "app",
    "ssh_session_bridge": "core.cowrie_session_bridge_worker",
    "ssh_event_adapter": "integrations.cowrie_adapter",
}


SERVICES = {
    "dashboard": "app",
    "ssh_session_bridge": "core.cowrie_session_bridge_worker",
    "ssh_event_adapter": "integrations.cowrie_adapter",
    "alternate_http": "services.web.alternate_http",
    "https": "services.web.https_service",
    "dns": "services.network.dns_service",
    "smtp": "services.email.smtp_service",
    "pop3": "services.email.pop3_service",
    "imap": "services.email.imap_service",
    "ftp": "services.remote_access.ftp_service",
    "telnet": "services.remote_access.telnet_service",
    "mysql": "services.database.mysql_service",
    "postgresql": "services.database.postgres_service",
    "msrpc": "services.windows.msrpc_service",
    "smb": "services.windows.smb_service",
    "rdp": "services.windows.rdp_service",
    "vnc": "services.windows.vnc_service",
}


def pid_file(name):
    return RUN_DIR / f"{name}.pid"


def process_matches(pid, module):
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
        command = cmdline.replace(b"\0", b" ").decode(errors="replace")
        return module in command
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return False


def get_pid(name, module):
    path = pid_file(name)

    # Check the saved PID first.
    if path.exists():
        try:
            pid = int(path.read_text().strip())
            if process_matches(pid, module):
                return pid
        except (ValueError, OSError):
            pass

        path.unlink(missing_ok=True)

    # Recover only an exact Python module process.
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue

        pid = int(entry.name)

        try:
            cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
            args = [arg.decode(errors="replace")
                    for arg in cmdline.split(b"\0") if arg]

            if len(args) >= 3 and args[1] == "-m" and args[2] == module:
                path.write_text(str(pid))
                return pid
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue

    return None

def start_service(name, module):
    existing = get_pid(name, module)

    if existing:
        print(f"[RUNNING] {name} (PID {existing})")
        return

    log_path = LOG_DIR / f"{name}.log"

    with log_path.open("a") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", module],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    pid_file(name).write_text(str(process.pid))

    time.sleep(0.8)

    if process.poll() is not None:
        pid_file(name).unlink(missing_ok=True)
        print(f"[FAILED] {name} — check logs/{name}.log")
    else:
        print(f"[STARTED] {name} (PID {process.pid})")


def stop_service(name, module):
    pid = get_pid(name, module)

    if not pid:
        print(f"[STOPPED] {name} (not running)")
        return

    try:
        os.kill(pid, signal.SIGTERM)

        for _ in range(50):
            if not process_matches(pid, module):
                break
            time.sleep(0.1)

        if process_matches(pid, module):
            os.kill(pid, signal.SIGKILL)

        print(f"[STOPPED] {name} (PID {pid})")

    except ProcessLookupError:
        print(f"[STOPPED] {name} (already exited)")
    except PermissionError:
        print(f"[ERROR] Cannot stop {name}: permission denied")
        return

    pid_file(name).unlink(missing_ok=True)


def show_status():
    print("\n========== HONEYPOT SERVICE STATUS ==========")

    for name, module in SERVICES.items():
        pid = get_pid(name, module)

        if pid:
            print(f"[RUNNING] {name:<16} PID: {pid}")
        else:
            print(f"[STOPPED] {name}")


def main():
    RUN_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)

    if len(sys.argv) != 2 or sys.argv[1] not in {
        "start", "start-ssh", "stop", "status"
    }:
        print("Usage: python run_honeypot.py [start|start-ssh|stop|status]")
        sys.exit(1)

    action = sys.argv[1]

    if action == "start":
        print("Starting Universal AI Honeypot services...\n")

        for name, module in SERVICES.items():
            start_service(name, module)

        print("\nCowrie SSH is managed separately.")
        print("Dashboard: http://127.0.0.1:5000/dashboard")

    elif action == "start-ssh":
        print("Starting SSH-only Universal AI Honeypot services...\\n")
        for name, module in SSH_SERVICES.items():
            start_service(name, module)
        print("\\nCowrie SSH must be started separately.")
        print("Dashboard: http://127.0.0.1:5000/dashboard")

    elif action == "stop":
        print("Stopping Universal AI Honeypot services...\n")

        for name, module in reversed(list(SERVICES.items())):
            stop_service(name, module)

    elif action == "status":
        show_status()


if __name__ == "__main__":
    main()
