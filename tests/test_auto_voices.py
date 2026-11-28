"""Offline contract tests for optional automatic-voice generator."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'tools' / 'generate_voice_pack.py'
spec = importlib.util.spec_from_file_location('scamshield_auto_voices', MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_six_language_high_risk_pack(tmp_path):
    pack = module.jobs_for('high', tuple(module.VOICES), tmp_path)
    assert len(pack) == 6
    assert {j.language for j in pack} == {'en', 'hi', 'bn', 'kn', 'te', 'or'}
    assert all(j.level == 'high' and j.output.name == 'high.mp3' for j in pack)
    assert all(j.text and j.voice.startswith(j.language + '-IN-') for j in pack)


def test_full_pack_30_clips_correct_paths(tmp_path):
    pack = module.jobs_for('all', tuple(module.VOICES), tmp_path)
    assert len(pack) == 30
    assert len({j.output for j in pack}) == 30
    assert tmp_path / 'or' / 'no_clear_signal.mp3' in {j.output for j in pack}


def test_no_external_user_data_in_voice_generator():
    source = MODULE_PATH.read_text(encoding='utf-8')
    assert 'CONTENT[lang]["voice"]' in source
    assert 'scamshield.languages' in source
    assert 'lastResult' not in source
    assert 'request.body' not in source


def test_invalid_selection_rejected(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        module.jobs_for('invalid', ('hi',), tmp_path)
    with pytest.raises(ValueError):
        module.jobs_for('high', ('xx',), tmp_path)


def test_generated_clip_verified_before_publish(tmp_path):
    src = MODULE_PATH.read_text(encoding='utf-8')
    assert '.mp3.part' in src
    assert 'temporary.replace(job.output)' in src
    assert 'header != b"ID3"' in src
