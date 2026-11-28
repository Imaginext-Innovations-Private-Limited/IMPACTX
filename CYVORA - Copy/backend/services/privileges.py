"""Start the backend with the rights packet capture needs, asking only once.

TShark records through a capture driver that Windows may restrict to
administrators. When it is restricted, every TShark start shows its own UAC
prompt, so capturing one session after another asks the user again and again.
Raising the backend once at start-up means each capture inherits those rights
and Windows asks a single time.
"""

import ctypes
import socket
import subprocess
import sys
from pathlib import Path

ELEVATED_FLAG = "--elevated"
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 5000
LOG_NAME = "backend-server.log"


def is_windows():
    return sys.platform == "win32"


def is_elevated():
    """True when this process already holds administrator rights."""
    if not is_windows():
        return True

    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        # Never block start-up because the check itself was unavailable.
        return True


def port_in_use(host=BACKEND_HOST, port=BACKEND_PORT):
    """True when a server already accepts connections on the backend port."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.settimeout(0.5)

    try:
        return probe.connect_ex((host, port)) == 0
    finally:
        probe.close()


def ensure_standard_streams(log_path=None):
    """Give a windowless interpreter real streams instead of None.

    A windowless interpreter reports ``sys.stdout``/``sys.stderr`` as None, so
    the start-up banner and any traceback would be lost. They are pointed at
    the backend log when one is given, and at the null device otherwise.
    """
    if sys.stdout is not None and sys.stderr is not None:
        return

    stream = None

    if log_path is not None:
        try:
            stream = open(log_path, "a", encoding="utf-8", buffering=1)
        except OSError:
            stream = None

    if stream is None:
        try:
            stream = open(devnull_path(), "w", encoding="utf-8")
        except OSError:
            return

    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, stream)


def devnull_path():
    return "nul" if is_windows() else "/dev/null"


def relaunch_elevated(argv=None):
    """Ask Windows for elevation once and start a privileged copy of this app.

    The privileged copy runs through a hidden command shell so its output is
    written to the usual log file; a windowless interpreter would have no
    stream to print the start-up banner to.

    Returns True when the elevated copy was started, False when the prompt was
    declined or could not be shown, so the caller can carry on unelevated.
    """
    script = Path(sys.argv[0]).resolve()
    project_root = script.parent.parent
    log_path = project_root / LOG_NAME

    command = subprocess.list2cmdline(
        [sys.executable, str(script), *(sys.argv[1:] if argv is None else argv),
         ELEVATED_FLAG]
    )
    parameters = f'/c {command} >> "{log_path}" 2>&1'

    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            "cmd.exe",
            parameters,
            str(script.parent),
            0,  # SW_HIDE: the shell window and its log stay in the background
        )
    except Exception:
        return False

    # ShellExecuteW returns a value above 32 when the process was started.
    return int(result) > 32
