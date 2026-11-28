"""ScamShield v1.5.0: cache natural AI warnings without changing the app."""
import argparse
import getpass
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scamshield import voice
from scamshield.languages import LANGUAGE_NAMES, LEVELS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true', help='Show missing clips; no API calls')
    parser.add_argument('--languages', nargs='+', choices=tuple(LANGUAGE_NAMES), default=list(LANGUAGE_NAMES))
    parser.add_argument('--context-caution', action='store_true', help='Include all 42 additional topic-specific caution warnings')
    args = parser.parse_args()
    rows = [(lang, level, 'generic') for lang in dict.fromkeys(args.languages) for level in LEVELS]
    for lang in dict.fromkeys(args.languages):
        for level in (('high', 'caution') if args.context_caution else ('high',)):
            rows.extend((lang, level, topic) for topic in voice.TOPICS if topic != 'generic')
    missing = [row for row in rows if not voice.cached(*row)]
    chars = sum(len(voice.voice_text(*row)) for row in missing)
    print(f'Total selected: {len(rows)} | Cached: {len(rows)-len(missing)} | Missing: {len(missing)}', flush=True)
    print(f'Missing warning text: {chars:,} Unicode characters (not a billing quote).', flush=True)
    print('Only predefined warning text is sent; clips stay in voice_cache/.', flush=True)
    if args.preview or not missing:
        return 0
    if input('Generate missing warnings using API credits? [y/N]: ').strip().lower() != 'y':
        print('Cancelled. No requests sent.')
        return 0
    if not voice.configured():
        os.environ['SARVAM_API_KEY'] = getpass.getpass('Paste Sarvam API key (hidden): ').strip()
    key = os.environ.get('SARVAM_API_KEY', '').strip()
    if not key.startswith('sk_') or any(ch.isspace() for ch in key):
        print('Unexpected key format. No requests sent.')
        return 2
    completed = 0
    for i, row in enumerate(missing, 1):
        try:
            voice.synthesize(*row)
        except voice.VoiceError as exc:
            print(f'[{i}/{len(missing)}] STOP {"/".join(row)}: {exc}', flush=True)
            print('Existing clips are preserved. Rerun to resume missing clips.')
            return 1
        completed += 1
        print(f'[{i}/{len(missing)}] OK {"/".join(row)}', flush=True)
    print(f'Finished: {completed} newly cached. Refresh the app and listen to verify quality.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
