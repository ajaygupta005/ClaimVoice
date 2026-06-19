# Component 47 - WS-6 Realtime Voice I/O - Results

## Checklist

- [x] `streaming/deepgram_stt.py` — `DeepgramStreamingSTT(StreamingSTT)` buffers
      PCM16 and transcribes (prerecorded) on flush.
- [x] `streaming/cartesia_tts.py` — `CartesiaStreamingTTS(StreamingTTS)` synthesizes
      per chunk into PCM24k `TtsAudioEvent`s (base64, `isFinal` on last).
- [x] `streaming/vad.py` — energy VAD + optional WebRTC VAD.
- [x] `streaming/factory.py` — `build_stt` / `build_tts` select real vs mock by
      mode + key, with mock fallback.
- [x] Factories wired into `telephony_ws` (`_handle_start` / `_handle_stop`).
- [x] Vendor SDKs lazy-imported; modules load without the packages.
- [x] `deepgram-sdk` + `cartesia` added to `pyproject.toml`.

## Tests

- `services/voice-agent/tests/unit/test_voice_factory.py`:
  - `test_build_stt_defaults_to_mock_without_key`
  - `test_build_tts_defaults_to_mock_without_key`
  - `test_build_stt_falls_back_to_mock_when_keyed_mode_but_sdk_or_key_missing`
  - `test_real_adapter_modules_import_without_sdk`
  - `test_energy_vad_detects_silence_vs_speech`
  - `test_build_vad_returns_object_with_is_speech`
- Full voice-agent suite green with no keys set (mock default).

## Commit

```
efbeddb feat(ws6): real Deepgram STT + Cartesia TTS + VAD (key-gated)
```

## Notes

- No API keys are available in this environment, so the real adapters are
  implemented but unverified against the live Deepgram/Cartesia services.
- `pyproject.toml` pins `deepgram-sdk>=3.7` and `cartesia>=1.0`; `uv` resolved
  `cartesia 3.2.0` and `deepgram-sdk 7.3.1` (cartesia 3.x / deepgram-sdk 7.x).
- Barge-in cancellation policy is out of scope; the VAD primitives are in place
  for a later component to drive it.
