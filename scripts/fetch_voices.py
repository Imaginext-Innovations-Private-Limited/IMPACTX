"""Download the offline neural voices once (English, Hindi, Gujarati), for demos without internet.

    pip install -r requirements.txt
    python scripts/fetch_voices.py

Voices come from the sherpa-onnx GitHub releases and are stored in ~/.cache/kharcha-kavach/tts
(or KK_TTS_DIR). Licences: see MODEL_CARD / README in each folder; the Hindi voice is
CC BY-NC-SA 4.0 (non-commercial use). Tamil, Telugu and Kannada have no offline neural voice
there: `pip install edge-tts` gives them natural online voices (on by default; KK_TTS_ONLINE=0 turns
it off), phones also speak them with their own voice, or set up Bhashini.

Certificates: some networks and antivirus tools re-sign HTTPS traffic with their own certificate,
which Python's own list does not know ("CERTIFICATE_VERIFY_FAILED"). The script then retries with
the operating system's certificate store (the `truststore` package, which Windows and macOS keep up
to date), then with the `certifi` bundle. Verification is never switched off.
"""

import ssl
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kk.voice.tts import NEURAL, NEURAL_URL, VOICE_DIR  # noqa: E402


def contexts():
    """SSL contexts to try, all with certificate verification on."""
    yield "Python default", ssl.create_default_context()
    try:
        import truststore
        yield "system certificate store", truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        pass
    try:
        import certifi
        yield "certifi bundle", ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass


def download(url: str, dest: Path) -> None:
    last = None
    for label, ctx in contexts():
        try:
            with urllib.request.urlopen(url, context=ctx, timeout=60) as r, open(dest, "wb") as out:
                total = int(r.headers.get("Content-Length") or 0)
                done, shown = 0, -10
                while chunk := r.read(1 << 16):
                    out.write(chunk)
                    done += len(chunk)
                    pct = done * 100 // total if total else 0
                    if total and pct >= shown + 10:
                        shown = pct - pct % 10
                        print(f"   {shown:3d}%  ({done >> 20} of {total >> 20} MB)", flush=True)
            print(f"   done ({label})")
            return
        except urllib.error.URLError as e:
            if not isinstance(getattr(e, "reason", None), ssl.SSLError):
                raise
            last = e
            print(f"   certificate check failed with the {label}; trying the next one")
    raise SystemExit(
        "\nCould not verify GitHub's certificate on this network.\n"
        "Fixes: run  pip install truststore  and try again; or switch off 'HTTPS scanning' in your antivirus;\n"
        "or use another network (a phone hotspot). The app works without these voices: the browser's\n"
        f"own voice is used instead.\nLast error: {last}")


def extract(archive: Path, into: Path) -> None:
    with tarfile.open(archive) as t:
        try:
            t.extractall(into, filter="data")
        except TypeError:          # Python versions before the 'filter' argument
            for m in t.getmembers():
                p = (into / m.name).resolve()
                if not str(p).startswith(str(into.resolve())):
                    raise SystemExit(f"unsafe path in archive: {m.name}")
            t.extractall(into)


VOICE_DIR.mkdir(parents=True, exist_ok=True)
for lang, (name, model) in NEURAL.items():
    if (VOICE_DIR / name / model).exists():
        print(f"{lang}: {name} already present")
        continue
    url = NEURAL_URL.format(name=name)
    tmp = VOICE_DIR / f"{name}.tar.bz2"
    print(f"{lang}: downloading {url}")
    download(url, tmp)
    extract(tmp, VOICE_DIR)
    tmp.unlink()
    print(f"{lang}: ready")
print(f"Voices are in {VOICE_DIR}")
