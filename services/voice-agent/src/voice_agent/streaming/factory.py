"""Factories that pick the real (key-gated) or mock STT/TTS adapter.

Selection is driven by settings: a real adapter is built only when its mode is enabled
AND the API key is present AND the SDK imports; any failure falls back to the mock so the
service always runs (tests, no keys, missing SDK).
"""

from __future__ import annotations

from voice_agent.core.config import settings
from voice_agent.streaming.stt_adapter import MockStreamingSTT, StreamingSTT
from voice_agent.streaming.tts_adapter import MockStreamingTTS, StreamingTTS


def build_stt(call_sid: str, stream_sid: str) -> StreamingSTT:
    if settings.stt_mode == "deepgram" and settings.deepgram_api_key:
        try:
            from voice_agent.streaming.deepgram_stt import DeepgramStreamingSTT

            return DeepgramStreamingSTT(call_sid, stream_sid, settings.deepgram_api_key)
        except Exception:
            pass
    return MockStreamingSTT(call_sid=call_sid, stream_sid=stream_sid)


def build_tts() -> StreamingTTS:
    if settings.tts_mode == "cartesia" and settings.cartesia_api_key:
        try:
            from voice_agent.streaming.cartesia_tts import CartesiaStreamingTTS

            return CartesiaStreamingTTS(settings.cartesia_api_key)  # type: ignore[return-value]
        except Exception:
            pass
    return MockStreamingTTS()
