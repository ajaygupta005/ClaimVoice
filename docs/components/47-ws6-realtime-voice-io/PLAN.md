# Component 47 - WS-6 Realtime Voice I/O - Plan

1. Add `deepgram-sdk` and `cartesia` to
   `services/voice-agent/pyproject.toml` (optional `webrtcvad`); re-resolve with
   `uv sync`.
2. Implement `services/voice-agent/src/voice_agent/streaming/deepgram_stt.py`:
   `DeepgramStreamingSTT(StreamingSTT)` that buffers pushed PCM16 (24 kHz) and runs
   a Deepgram prerecorded transcription on flush. Lazy-import the SDK in the
   constructor.
3. Implement `services/voice-agent/src/voice_agent/streaming/cartesia_tts.py`:
   `CartesiaStreamingTTS(StreamingTTS)` that synthesizes per text chunk into
   PCM24k `TtsAudioEvent`s (base64, `isFinal` on the last), reusing the existing
   `_chunk_text` helper. Lazy-import the SDK.
4. Implement `services/voice-agent/src/voice_agent/streaming/vad.py`: an energy VAD
   and an optional WebRTC VAD, with a `build_vad` selector.
5. Add `services/voice-agent/src/voice_agent/streaming/factory.py` with
   `build_stt(call_sid, stream_sid)` and `build_tts()` that select real vs mock by
   mode + key and fall back to the mock on any failure.
6. Wire the factories into
   `services/voice-agent/src/voice_agent/streaming/telephony_ws.py`
   (`_handle_start` / `_handle_stop`), replacing the hardcoded mock adapters.
7. Add `services/voice-agent/tests/unit/test_voice_factory.py`: factory defaults to
   mock without a key, falls back to mock when keyed-mode but SDK/key missing, the
   real adapter modules import without the SDK, and the VAD basics.
8. Confirm the full voice-agent suite stays green with no keys set.
