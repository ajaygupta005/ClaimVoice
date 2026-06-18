"""Tests for the end-to-end voice eval (deterministic, mock mode)."""

import sys
from pathlib import Path

# Make eval/tasks importable without install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tasks"))

import e2e_voice_eval as m  # noqa: E402


def test_dataset_loads_and_has_cases():
    assert len(m.load_cases()) >= 5


def test_every_case_produces_audio_and_passes():
    """Full voice turn (transcript -> orchestrate -> TTS) for each golden case."""
    for case in m.load_cases():
        turn = m.run_voice_turn(case["question"])
        sr = m.score_voice_turn(case, turn)
        assert sr.passed, f"{case['id']} failed: {sr.failures}"
        assert turn.audio_chunks >= 1
        assert turn.has_final_audio
