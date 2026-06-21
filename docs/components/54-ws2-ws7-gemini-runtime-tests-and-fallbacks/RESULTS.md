# Component 54 — Gemini Runtime Tests and Fallbacks: Results

## Automated tests

| Suite | Location | Count | Result |
|---|---|---|---|
| Gemini runtime fallbacks (C54) | `tests/unit/test_gemini_runtime_fallbacks.py` | 19 | ✅ pass |
| Gemini Live bridge (C51) | `tests/unit/test_gemini_live_bridge.py` | 12 | ✅ pass |
| Gemini speak (C53) | `tests/unit/test_gemini_live_speak.py` | 9 | ✅ pass |
| Runtime status (C50) | `tests/unit/test_runtime_status.py` | 5 | ✅ pass |
| Full unit suite | `tests/unit/` | 282 | ✅ pass |
| TypeScript typecheck | `apps/web` | — | ✅ clean |

## What was implemented

### Backend (voice-agent service)

**`tests/unit/test_gemini_runtime_fallbacks.py`** — 19 tests:
- Missing key + wrong runtime → `_UnavailableBridge`, `is_available()=False`
- Status endpoint never contains `gemini_api_key` / `api_key` / `GEMINI`
- `_UnavailableSession.events()` yields exactly one `BridgeErrorEvent(code="unavailable")`
- `_UnavailableBridge.open_session()` yields `_UnavailableSession`
- Real bridge with missing SDK falls back to `_UnavailableSession` (lazy-import mocked)
- `_normalize()` → `TranscriptPartialEvent` for `finished=False`
- `_normalize()` → `TranscriptFinalEvent` for `finished=True`
- `_normalize()` → `None` for unknown server content
- `_normalize()` → `AudioChunkEvent` with `is_final=True/False` based on `turn_complete`
- `close()` idempotent on `_RealGeminiLiveSession`, `MockGeminiLiveSession`, `_UnavailableSession`
- Speak endpoint never returns `api_key` in any form
- Speak endpoint exception → `ok=False` (not 500)
- `MockGeminiLiveBridge.is_available()=True`
- `MockGeminiLiveSession.send_audio()` enqueues `SessionOpenedEvent`
- `MockGeminiLiveSession.send_text()` produces `TranscriptFinalEvent` with matching text

**`gemini_live_bridge.py`** — added structured logs:
- `gemini_live.speak_text_start` with `text_len`
- `gemini_live.speak_text_done` with `pcm_bytes`

### Frontend (`apps/web`)

**`gemini-live-client.ts`** — hardened:
- Timeout constants centralized: `DEFAULT_MIC_PERMISSION_TIMEOUT_MS`, `DEFAULT_NO_TRANSCRIPT_TIMEOUT_MS`, `WS_CONNECT_TIMEOUT_MS`
- `cvDebug()` helper — logs only when `localStorage.CLAIMVOICE_DEBUG=1` or `?cv_debug=1` in URL; never logs credentials or raw audio
- `_startAudioCapture()` registers `track.onended` — fires `onError('mic_stream_ended', ...)` if the OS revokes the mic mid-session
- Debug logs at: mic-permission request, mic granted + WS URL, WS connected, transcript partial/final (length only), session closed, bridge error, no-transcript timeout

**`VoiceAssistantUI.tsx`** — hardened:
- `NotAllowedError` / `PermissionDeniedError` caught separately in `startGeminiMic()` — sets `error_recoverable` without attempting browser STT fallback (permission is denied at OS level)
- `cvDebug` imported and called at: pipeline start (source, question length), agent response received (latency ms, answer length), Gemini TTS attempt, speech playback start (provider, voice label), speech playback ended, fallback reasons logged on Gemini TTS failure
- `console.warn` narrowed to `[ClaimVoice:GeminiLive]` prefix for easy filtering

## Manual test checklist

### Setup
- [ ] `python scripts/start.py` or per-service startup per `Plan/HANDOFF.md`
- [ ] Open `http://localhost:3000` in Chrome

### Mic permission denied
1. Chrome → Settings → site permissions → block microphone for localhost
2. Click mic button → status stays `Error - retry`, does not hang in `Listening`
3. Re-allow mic, retry → works normally

### Short question (Gemini runtime=browser, no key)
1. `CLAIMVOICE_VOICE_RUNTIME=browser` (default)
2. Click mic, say "Is an MRI covered?" → status: Listening → Finalizing → Thinking → Speaking → Ready

### Interrupt during listening
1. Click mic → status: Listening
2. Click mic again immediately → session tears down, status returns to Ready

### Interrupt during speaking
1. Start a voice turn, wait for speaking state
2. Click mic → speaking stops, new listening session starts

### Gemini unavailable fallback
1. `CLAIMVOICE_VOICE_RUNTIME=gemini-live`, no `GEMINI_API_KEY` set
2. Status panel should show runtime as `gemini-live-unavailable` or `fallback`
3. Mic click falls back to browser STT seamlessly

### Debug log visibility
1. In browser console: `localStorage.setItem('CLAIMVOICE_DEBUG', '1')`
2. Reload, click mic → `[ClaimVoice:GeminiLive]` prefixed lines appear
3. No API keys, no raw audio hex dumps in any log line

### Route change cleanup
1. Start a voice turn (listening or speaking)
2. Navigate to another page → mic released, WebSocket closed, no orphan processes

## Known limitations

- `ScriptProcessorNode` is deprecated; an AudioWorklet replacement can be dropped in without changing the WebSocket protocol
- The `_RealGeminiLiveSession.speak_text()` does not enforce a per-chunk timeout — a stalled Gemini response waits indefinitely; an outer per-request timeout is handled by the `gemini-speak` API route (30 s `AbortSignal.timeout`)
- No automated browser-side tests (jsdom doesn't support `AudioContext`/`WebSocket` natively); the manual checklist above covers these cases
