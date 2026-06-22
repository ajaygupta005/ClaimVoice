# Component 64 - WS-7 Cartesia TTS Stabilization Plan

## Implementation Steps

1. Review current TTS paths.
   - Cartesia backend synthesize path.
   - Browser playback path.
   - Gemini-related runtime indicators.
   - macOS/browser fallback labels.

2. Define Cartesia as primary TTS.
   - Ensure config names are clear.
   - Ensure startup preflight reports Cartesia.
   - Ensure runtime status reports Cartesia.

3. Improve turn lifecycle.
   - Show answer text immediately.
   - Start TTS as a follow-up async step.
   - Release UI turn lock on success, timeout, or failure.
   - Allow user cancellation.

4. Add TTS failure handling.
   - API timeout.
   - API error.
   - invalid audio.
   - playback blocked.
   - user stop.

5. Isolate Gemini.
   - Hide Gemini runtime from normal UI path.
   - Keep behind explicit experimental flag if retained.
   - Avoid mixed labels such as Claude answer plus Gemini voice unless intentional.

6. Add tests.
   - Cartesia success.
   - Cartesia failure.
   - timeout.
   - cancellation.
   - next-turn recovery.

## Suggested Files

- `services/voice-agent/src/voice_agent/tts/*`
- `services/voice-agent/src/voice_agent/api/v1/tts.py`
- `services/voice-agent/src/voice_agent/api/v1/runtime.py`
- `apps/web/src/components/VoiceAssistantUI.tsx`
- `apps/web/src/lib/voice-turn-controller.ts`
- TTS tests

## Validation

- Voice-agent TTS unit tests.
- Web typecheck/build.
- Manual voice demo with Cartesia key.
- Manual failure test with missing/invalid Cartesia key.

## Risks

- Cartesia latency may feel slow if text is not shown first.
- Browser autoplay restrictions may still affect playback.
- Mixing browser fallback and Cartesia can confuse status badges.

## Done When

- Cartesia is the obvious and stable voice path.
- TTS never traps the UI in a stuck speaking state.
- Gemini is not part of the normal demo path.

