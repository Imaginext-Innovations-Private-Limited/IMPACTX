"""Generate fixed, non-personal ScamShield warnings as playable MP3 clips.

Demo helper only: uses the unofficial edge-tts Python package with an online
service; availability/licensing/quotas are not guaranteed. For a deployed
product, use an officially supported TTS provider with appropriate credentials.
Never send message transcripts, OCR content or user data to this generator.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scamshield.languages import CONTENT, LANGUAGE_NAMES, LEVELS  # noqa: E402

# Verified against documented Microsoft standard neural TTS voice names.
VOICES = {
    "en": "en-IN-NeerjaNeural",
    "hi": "hi-IN-SwaraNeural",
    "bn": "bn-IN-TanishaaNeural",
    "kn": "kn-IN-SapnaNeural",
    "te": "te-IN-ShrutiNeural",
    "or": "or-IN-SubhasiniNeural",
}


@dataclass(frozen=True)
class VoiceJob:
    language: str
    level: str
    voice: str
    text: str
    output: Path


def jobs_for(risk: str, langs: tuple[str, ...], destination: Path = ROOT / "static" / "voices") -> list[VoiceJob]:
    """Choose from five strictly prewritten warnings, never user-supplied text."""
    if risk not in ("high", "all"):
        raise ValueError("risk must be high or all")
    levels = LEVELS if risk == "all" else ("high",)
    jobs = []
    for lang in langs:
        if lang not in VOICES:
            raise ValueError(f"unsupported language: {lang}")
        for level in levels:
            warning = CONTENT[lang]["voice"][LEVELS.index(level)]
            jobs.append(VoiceJob(lang, level, VOICES[lang], warning, destination / lang / f"{level}.mp3"))
    return jobs


async def generate_one(job: VoiceJob, edge_tts, overwrite: bool = False) -> bool:
    if job.output.exists() and job.output.stat().st_size > 200 and not overwrite:
        print(f"SKIP {job.language}/{job.level}: already generated", flush=True)
        return True
    # Do not replace user-recorded audio; it remains preferred by the UI.
    human_clip = job.output.with_suffix(".webm")
    if human_clip.exists() and human_clip.stat().st_size > 200 and not overwrite:
        print(f"SKIP {job.language}/{job.level}: human clip exists", flush=True)
        return True
    job.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = job.output.with_suffix(".mp3.part")
    try:
        speech = edge_tts.Communicate(text=job.text, voice=job.voice, rate="-8%")
        await speech.save(str(temporary))
        if not temporary.exists() or temporary.stat().st_size < 200:
            raise RuntimeError("The speech provider returned no usable audio")
        with temporary.open("rb") as handle:
            header = handle.read(3)
        if header != b"ID3" and not (len(header) >= 2 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0):
            raise RuntimeError("The response did not look like MP3 audio")
        temporary.replace(job.output)
        print(f"OK   {job.language}/{job.level}: {job.output.relative_to(ROOT)}", flush=True)
        return True
    except Exception as exc:
        print(f"FAIL {job.language}/{job.level}: {type(exc).__name__}: {exc}", flush=True)
        return False
    finally:
        temporary.unlink(missing_ok=True)


async def generate_all(selected_jobs: list[VoiceJob], overwrite: bool = False) -> int:
    try:
        import edge_tts
    except ImportError:
        print('Missing edge-tts. Install with "python -m pip install edge-tts".')
        return 2
    completed = 0
    for i, job in enumerate(selected_jobs, 1):
        print(f"[{i}/{len(selected_jobs)}] {LANGUAGE_NAMES[job.language][0]} — {job.level}", flush=True)
        completed += bool(await generate_one(job, edge_tts, overwrite))
    print(f"\nAudio results: {completed}/{len(selected_jobs)} available. Refresh ScamShield in your browser (Ctrl + F5).")
    if completed != len(selected_jobs):
        print("Some languages failed; check your internet connection. Run again to retry only missing files.")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Create ScamShield's predefined spoken safety warnings")
    parser.add_argument("--risk", choices=("high", "all"), default="high", help="High-risk demo only (default), or all 5 risk types")
    parser.add_argument("--languages", nargs="+", choices=tuple(VOICES), default=list(VOICES), help="Languages to synthesize")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate existing MP3s and ignore existing human clip preference")
    args = parser.parse_args()
    print("Online speech generation for fixed, prewritten warnings ONLY. No scanned messages or personal data are sent.")
    print("Requires internet. The unofficial provider may be unavailable; existing browser/human voices remain fallback.\n")
    return asyncio.run(generate_all(jobs_for(args.risk, tuple(args.languages)), args.overwrite))


if __name__ == "__main__":
    raise SystemExit(main())
