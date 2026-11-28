"""Explicit, one-time download of multilingual local speech weights."""
import os
from pathlib import Path
from huggingface_hub import snapshot_download
root=Path(os.environ.get('WELFARE_DATA',Path(__file__).resolve().parent/'local_data'))
target=Path(os.environ.get('WELFARE_WHISPER_DIR',root/'speech-model'))
if __name__=='__main__':
    required = ('model.bin','config.json','tokenizer.json','vocabulary.txt')
    if not all((target / name).is_file() for name in required):
        snapshot_download(repo_id='Systran/faster-whisper-small', local_dir=str(target))
    from navigator.media import _load_speech
    import numpy as np
    segments, _ = _load_speech(str(target)).transcribe(np.zeros(16000,dtype=np.float32), language='en', beam_size=1)
    list(segments)  # Exercise native inference before reporting a successful install.
    print('Local speech model available at',target)
