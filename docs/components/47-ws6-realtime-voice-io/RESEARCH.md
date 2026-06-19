# Component 47 - WS-6 Realtime Voice I/O - Research

## Why buffer + prerecorded for STT behind a sync push/flush interface
The existing `StreamingSTT` interface is a simple synchronous push/flush contract
(`MockStreamingSTT` accumulates pushed PCM and emits a transcript on flush). Rather
than rework the telephony bridge around Deepgram's live websocket, the real adapter
keeps the same contract: it buffers the pushed PCM16 (24 kHz) and runs a single
Deepgram prerecorded transcription on flush, emitting a final transcript event.
This drops in behind the same interface, keeps the bridge code unchanged, and is
enough for a turn-based voice loop. Live-websocket streaming with partial results
is a later refinement.

## Why lazy SDK imports + factory fallback
The ~236-test suite must run offline, and `deepgram-sdk` / `cartesia` may not be
installed in every environment. So the real adapter modules import their vendor
SDKs lazily (inside the constructor / call), which means the modules themselves
import cleanly even when the packages are absent. The `build_stt` / `build_tts`
factories build a real adapter only when the mode is enabled AND the key is
present AND the SDK imports; any failure falls back to the mock. The result: with
no keys (the default) every test path uses the mock, and a missing SDK is safe.

## Why key-gating the mode
`stt_mode` / `tts_mode` plus the respective API keys gate the real path. A mode of
`deepgram` / `cartesia` is necessary but not sufficient — the key must also be set,
otherwise the factory returns the mock. This keeps CI and local dev deterministic
(mock) while letting a properly configured deployment opt into the real services
without code changes.
