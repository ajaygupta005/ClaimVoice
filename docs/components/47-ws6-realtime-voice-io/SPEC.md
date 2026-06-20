# Component 47 - WS-6 Realtime Voice I/O

> **Branch**: feat/ws456-grounded-agent | **Milestone**: M12 | **Workstream**: WS-6

## Goal

Add real streaming STT/TTS adapters behind the existing `StreamingSTT` /
`StreamingTTS` interfaces, key-gated and mock-by-default.

- `streaming/deepgram_stt.py` — `DeepgramStreamingSTT(StreamingSTT)`: buffer pushed
  PCM16 (24 kHz) and run a prerecorded Deepgram transcription on flush.
- `streaming/cartesia_tts.py` — `CartesiaStreamingTTS(StreamingTTS)`: synthesize
  per text chunk into PCM24k `TtsAudioEvent`s (base64, `isFinal` on the last).
- `streaming/vad.py` — energy VAD plus an optional WebRTC VAD.
- `streaming/factory.py` — `build_stt` / `build_tts` factories that select the real
  adapter vs the mock by mode + key, with mock fallback.
- Wire the factories into `telephony_ws` (replace the hardcoded
  `MockStreamingSTT` / `MockStreamingTTS`).
- Lazy-import the vendor SDKs so the modules load without the packages installed.
- Add `deepgram-sdk` and `cartesia` to `pyproject.toml` dependencies.

## Out of scope

- Barge-in cancellation policy.
- Live key verification — no keys are available in this environment, so the
  adapters are implemented but unverified against the live services.
