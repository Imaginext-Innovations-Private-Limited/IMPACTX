import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / "Scripts" / "python.exe"
REQUIREMENTS = ROOT / "requirements.txt"
REQUIREMENTS_STAMP = ROOT / ".careerpilot-requirements.sha256"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
REQUIRED_MODEL = "qwen2.5:3b"
MIN_PYTHON = (3, 11)
MAX_PYTHON = (3, 15)


def run(command, *, cwd=ROOT, env=None):
    print("+ " + subprocess.list2cmdline([str(part) for part in command]), flush=True)
    return subprocess.run(command, cwd=cwd, env=env, check=False).returncode


def python_is_compatible(version):
    return MIN_PYTHON <= version < MAX_PYTHON


def check_python():
    version = sys.version_info[:3]
    if not python_is_compatible(version):
        print(
            "ERROR: CareerPilot AI requires Python 3.11 through 3.14. "
            f"The selected interpreter is {sys.version.split()[0]}.",
            file=sys.stderr,
        )
        return False
    print(f"Python {version[0]}.{version[1]}.{version[2]}: compatible")
    return True


def requirement_names(contents):
    names = set()
    for line in contents.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(("-", ".")):
            continue
        match = re.match(r"([A-Za-z0-9][A-Za-z0-9_.-]*)", line)
        if match:
            names.add(re.sub(r"[-_.]+", "-", match.group(1)).lower())
    return names


def missing_requirements(contents, python):
    names = sorted(requirement_names(contents))
    code = (
        "import importlib.metadata as m, json, sys; "
        "names=json.loads(sys.argv[1]); "
        "missing=[name for name in names if not any("
        "d.metadata['Name'].lower().replace('_','-').replace('.','-') == "
        "name.lower().replace('_','-').replace('.','-') "
        "for d in m.distributions())]; "
        "print(json.dumps(missing))"
    )
    result = subprocess.run(
        [str(python), "-c", code, json.dumps(names)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print("ERROR: Could not inspect installed virtual-environment packages.", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        return names
    return json.loads(result.stdout)


def requirements_digest(contents):
    return hashlib.sha256(contents.encode("utf-8")).hexdigest()


def ensure_virtual_environment():
    if VENV_PYTHON.is_file():
        return True

    if VENV.exists():
        print(
            f"ERROR: {VENV} exists but its Python executable is missing. "
            "Move or rename this broken .venv folder, then run setup_project.bat again.",
            file=sys.stderr,
        )
        return False

    print("Creating the project virtual environment in .venv ...", flush=True)
    result = run([sys.executable, "-m", "venv", str(VENV)])
    if result != 0 or not VENV_PYTHON.is_file():
        print(
            "ERROR: Could not create .venv. Check that Python is installed correctly "
            "and that this folder is writable.",
            file=sys.stderr,
        )
        return False
    return True


def check_venv_python(python):
    result = subprocess.run(
        [str(python), "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        version = tuple(int(part) for part in result.stdout.split())
    except ValueError:
        version = ()
    if result.returncode != 0 or len(version) != 2 or not python_is_compatible(version):
        print(
            "ERROR: The Python interpreter inside .venv is not compatible. "
            "Rename the .venv folder and run setup_project.bat to recreate it with Python 3.11–3.14.",
            file=sys.stderr,
        )
        return False
    return True


def ensure_pip(python):
    result = subprocess.run(
        [str(python), "-c", "import importlib.metadata as m; print(m.version('pip'))"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    version = result.stdout.strip() if result.returncode == 0 else ""
    version_numbers = tuple(int(part) for part in re.findall(r"\d+", version)[:2])

    if not version_numbers:
        if run([str(python), "-m", "ensurepip", "--upgrade"]) != 0:
            print("ERROR: pip is unavailable and Python could not bootstrap it.", file=sys.stderr)
            return False
        version_numbers = (0, 0)

    if version_numbers < (24, 0):
        print("Upgrading the virtual environment's outdated pip ...", flush=True)
        if run([str(python), "-m", "pip", "install", "--upgrade", "pip"]) != 0:
            print("ERROR: pip could not be upgraded.", file=sys.stderr)
            return False
        result = subprocess.run(
            [str(python), "-c", "import importlib.metadata as m; print(m.version('pip'))"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            print("ERROR: pip is still unavailable in .venv.", file=sys.stderr)
            return False
    return True


def install_dependencies(python):
    if not REQUIREMENTS.is_file():
        print(f"ERROR: Required dependency file not found: {REQUIREMENTS}", file=sys.stderr)
        return False

    contents = REQUIREMENTS.read_text(encoding="utf-8")
    digest = requirements_digest(contents)
    missing = missing_requirements(contents, python)
    old_digest = REQUIREMENTS_STAMP.read_text(encoding="ascii").strip() if REQUIREMENTS_STAMP.is_file() else ""

    if digest != old_digest or missing:
        if missing:
            print("Installing dependencies (missing: " + ", ".join(missing) + ") ...", flush=True)
        else:
            print("requirements.txt changed; syncing the virtual environment ...", flush=True)
        if run([
            str(python), "-m", "pip", "install",
            "--disable-pip-version-check", "-r", str(REQUIREMENTS),
        ]) != 0:
            print(
                "ERROR: Dependency installation failed. Check your internet connection, "
                "requirements.txt, and the error above.",
                file=sys.stderr,
            )
            return False
        missing = missing_requirements(contents, python)
        if missing:
            print("ERROR: These dependencies are still missing: " + ", ".join(missing), file=sys.stderr)
            return False
        REQUIREMENTS_STAMP.write_text(digest, encoding="ascii")
    else:
        print("Dependencies are up to date; skipping installation.")

    if run([str(python), "-m", "pip", "check"]) != 0:
        print("ERROR: Installed packages have dependency conflicts; see pip check above.", file=sys.stderr)
        return False
    return True


def prepare_database(python):
    manage_py = ROOT / "manage.py"
    if not manage_py.is_file():
        print(f"ERROR: manage.py was not found in {ROOT}.", file=sys.stderr)
        return False

    print("Applying pending database migrations (existing records are preserved) ...", flush=True)
    if run([str(python), str(manage_py), "migrate", "--noinput"]) != 0:
        print(
            "ERROR: Database migration failed. Review the Django error above and check "
            "the configured database and permissions. No database reset was attempted.",
            file=sys.stderr,
        )
        return False

    print("Running Django system checks ...", flush=True)
    if run([str(python), str(manage_py), "check"]) != 0:
        print("ERROR: Django system checks failed; see the details above.", file=sys.stderr)
        return False
    return True


def prepare():
    if not check_python():
        return False
    if not ensure_virtual_environment():
        return False

    python = VENV_PYTHON
    if not check_venv_python(python):
        return False
    if not ensure_pip(python):
        return False
    if not install_dependencies(python):
        return False

    print("Verifying Django installation ...", flush=True)
    if run([str(python), "-m", "django", "--version"]) != 0:
        print("ERROR: Django could not be imported from .venv.", file=sys.stderr)
        return False
    return prepare_database(python)


def check_ollama():
    ollama_installed = shutil.which("ollama") is not None
    if not ollama_installed:
        print("Ollama: command not found (optional; Django will still start).")
    else:
        print("Ollama: installed.")

    try:
        request = urllib.request.Request(OLLAMA_TAGS_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, UnicodeDecodeError):
        print("Ollama server: not responding at http://localhost:11434 (using the Python fallback).")
        print("  Start Ollama if you want local AI; otherwise continue using CareerPilot normally.")
        return

    models = payload.get("models", []) if isinstance(payload, dict) else []
    names = {
        model.get("name")
        for model in models
        if isinstance(model, dict) and isinstance(model.get("name"), str)
    }
    print("Ollama server: responding at http://localhost:11434.")
    if REQUIRED_MODEL in names:
        print(f"Ollama model: {REQUIRED_MODEL} is installed.")
    else:
        print(f"Ollama model: {REQUIRED_MODEL} is missing (using the Python fallback).")
        print(f"  To install it later, run: ollama pull {REQUIRED_MODEL}")


def port_is_available():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        try:
            server_socket.bind(("127.0.0.1", 8000))
        except OSError:
            return False
    return True


def run_server():
    if not port_is_available():
        print(
            "ERROR: Port 8000 is already in use. Stop the other development server "
            "or close the application using that port, then try again.",
            file=sys.stderr,
        )
        if os.name == "nt":
            print("To inspect it, run: netstat -ano | findstr :8000", file=sys.stderr)
        return 1

    check_ollama()
    print("Starting CareerPilot AI at http://127.0.0.1:8000/ (press Ctrl+C to stop).", flush=True)
    try:
        server = subprocess.Popen(
            [sys.executable, str(ROOT / "manage.py"), "runserver", "127.0.0.1:8000", "--noreload"],
            cwd=ROOT,
        )
    except OSError as exc:
        print(f"ERROR: Django could not be started: {exc}", file=sys.stderr)
        return 1

    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if server.poll() is not None:
                print("ERROR: Django exited during startup. Review the server error above.", file=sys.stderr)
                return server.returncode or 1
            try:
                with socket.create_connection(("127.0.0.1", 8000), timeout=0.5):
                    webbrowser.open("http://127.0.0.1:8000/")
                    return server.wait()
            except OSError:
                time.sleep(0.25)
        print("ERROR: Django did not open port 8000 within 20 seconds.", file=sys.stderr)
        server.terminate()
        return server.wait()
    except KeyboardInterrupt:
        print("\nStopping Django gracefully ...", flush=True)
        server.terminate()
        try:
            return server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            return server.wait()


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in {"prepare", "start"}:
        print("Usage: setup_windows.py prepare | start [--prepared]", file=sys.stderr)
        return 2

    if sys.argv[1] == "prepare":
        if prepare():
            print("\nCareerPilot AI setup is ready.", flush=True)
            return 0
        return 1

    if "--prepared" not in sys.argv and not prepare():
        return 1
    return run_server()


if __name__ == "__main__":
    raise SystemExit(main())
