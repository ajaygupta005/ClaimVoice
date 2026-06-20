"""Tests for STT/TTS factory selection and that real adapters import lazily."""

from __future__ import annotations

from voice_agent.streaming.factory import build_stt, build_tts
from voice_agent.streaming.stt_adapter import MockStreamingSTT
from voice_agent.streaming.tts_adapter import MockStreamingTTS
from voice_agent.streaming.vad import EnergyVAD, build_vad


def test_build_stt_defaults_to_mock_without_key():
    # Default settings: stt_mode="mock", no key.
    assert isinstance(build_stt("CA", "SM"), MockStreamingSTT)


def test_build_tts_defaults_to_mock_without_key():
    assert isinstance(build_tts(), MockStreamingTTS)


def test_build_stt_falls_back_to_mock_when_keyed_mode_but_sdk_or_key_missing(monkeypatch):
    import voice_agent.streaming.factory as f

    monkeypatch.setattr(f.settings, "stt_mode", "deepgram", raising=False)
    monkeypatch.setattr(f.settings, "deepgram_api_key", "", raising=False)  # no key -> mock
    assert isinstance(build_stt("CA", "SM"), MockStreamingSTT)


def test_real_adapter_modules_import_without_sdk():
    # Importing the real adapters must not require the vendor SDK (lazy import inside methods).
    import voice_agent.streaming.cartesia_tts as c
    import voice_agent.streaming.deepgram_stt as d

    assert hasattr(d, "DeepgramStreamingSTT")
    assert hasattr(c, "CartesiaStreamingTTS")


def test_energy_vad_detects_silence_vs_speech():
    vad = EnergyVAD()
    assert vad.is_speech(b"\x00\x00" * 100) is False
    loud = b"\xff\x7f" * 100  # max-amplitude int16
    assert vad.is_speech(loud) is True


def test_build_vad_returns_object_with_is_speech():
    v = build_vad()
    assert hasattr(v, "is_speech")
