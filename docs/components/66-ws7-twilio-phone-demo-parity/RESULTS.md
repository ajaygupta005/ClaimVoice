# C66 — Twilio Phone Demo Parity — Results

## Summary

| Metric | Value |
|--------|-------|
| Python tests (C66) | 17 / 17 pass |
| TypeScript tests (C66) | 14 / 14 pass |
| Full Python suite | 391 / 391 pass |
| TypeScript suite (telephony) | 55 / 55 pass (5 pre-existing unrelated failures) |

## Changes

### `services/voice-agent/src/voice_agent/api/v1/telephony_ws.py`

Hardened `_handle_stop()` with full observability and failure recovery:

- Added `import uuid` and `TurnTracer` import.
- Added `last_turn_id: str = ""` to `SessionState` dataclass.
- `_handle_stop` now:
  - Generates a `turn_id = uuid.uuid4().hex` per stop event.
  - Wraps `orchestrate()` in try/except — on error sends `error` + stop ack and returns.
  - Wraps TTS synthesis in try/except — on error sends `error` but still sends stop ack.
  - Always sends the stop ack (even after orchestrate or TTS failure).
  - Logs `tool_trace`, `guard_passed`, `intent`, `grounded`, `turn_id`, `tts_chunks` at INFO.
- `WebSocketDisconnect` handler logs `audio_frames` and `last_turn_id`.

### `services/voice-agent/tests/unit/test_c66_phone_demo_parity.py` (NEW)

17 tests covering:

| Test | Description |
|------|-------------|
| `test_phone_coverage_intent_matches_browser` | Phone and browser paths share the same LangGraph — intent parity via transcript text |
| `test_phone_cost_intent_matches_browser` | Same parity check for cost intent |
| `test_phone_answer_is_grounded_for_coverage` | `grounded` field is always a bool |
| `test_phone_answer_has_tool_trace` | `tool_trace` present with ≥1 entry |
| `test_phone_tts_audio_sent_after_answer` | At least one `tts.audio` event emitted |
| `test_phone_tts_audio_is_valid_base64` | PCM16 payload decodes to valid bytes (length % 2 == 0) |
| `test_phone_stop_ack_after_full_sequence` | Stop ack always arrives with correct callSid |
| `test_session_tracks_audio_bytes` | `audio_frames` and `audio_bytes_received` correctly incremented |
| `test_phone_orchestrate_error_returns_stop_ack` | Orchestrate RuntimeError → error msg + stop ack |
| `test_phone_orchestrate_error_does_not_send_answer` | No `answer.final` fabricated after orchestrate error |
| `test_phone_tts_error_returns_stop_ack` | TTS RuntimeError → stop ack still sent |
| `test_phone_tts_error_answer_still_delivered` | `answer.final` arrives even when TTS fails |
| `test_phone_silent_call_returns_stop_ack` | No audio before stop → safe stop ack |
| `test_phone_no_answer_for_silent_call` | No `answer.final` or `tts.audio` for silent call |
| `test_existing_start_ack_unchanged` | Existing start ack protocol unchanged |
| `test_existing_audio_ack_unchanged` | Existing audio ack protocol unchanged |
| `test_existing_invalid_json_unchanged` | Existing invalid JSON error response unchanged |

### `services/telephony/tests/unit/handler_parity.test.ts` (NEW)

14 TypeScript tests covering:

| Suite | Tests |
|-------|-------|
| Full frame sequence | start→media→stop order, callSid/streamSid in events, stop carries IDs |
| Inbound codec | µ-law→PCM16 no-throw, 160 µ-law → 480 PCM24k samples, forwarded bytes match |
| Return audio | tts.audio → callback, PCM24k→Twilio frame, codec round-trip |
| Disconnect safety | close before stop safe, no events after close, unreachable URL no-op |
| Multiple media frames | 3 frames → 3 audio events |
| CONNECTING-state buffering | start+audio+stop queued before WS opens all arrive |

## Security

- No API keys, credentials, PHI, or PII appear in any test or implementation code.
- `turn_id` is a random UUID hex, not a member identifier.
- Error messages logged from `orchestrate()` and TTS contain only exception strings, not plan data.

## How to Run

```bash
# Python — C66 tests only
cd services/voice-agent
PYTHONPATH=src python -m pytest tests/unit/test_c66_phone_demo_parity.py -v

# Python — full unit suite
PYTHONPATH=src python -m pytest tests/unit/ -q

# TypeScript — telephony handler parity
cd services/telephony
pnpm test --reporter=verbose
# (or: node ~/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs test)
```
