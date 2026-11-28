"""Launch local demo with keys in process memory, never written to disk."""
import getpass
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def main():
    for key, label in [('GROQ_API_KEY', 'Groq'), ('SARVAM_API_KEY', 'Sarvam (optional)')]:
        if not os.environ.get(key, '').strip():
            os.environ[key] = getpass.getpass(f'{label} API key (hidden; Enter to skip): ').strip()
    print('Open http://127.0.0.1:8000. Enable Use online AI to opt in to Groq.')
    import uvicorn
    uvicorn.run('scamshield.main:app', host='127.0.0.1', port=8000)

if __name__ == '__main__':
    main()
