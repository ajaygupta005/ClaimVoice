# Component 50 - WS-2/WS-7 Voice Runtime Selector - Implementation Plan

## Inspect

1. [ ] Read `.env.example`.
2. [ ] Read `services/voice-agent/src/voice_agent/core/config.py`.
3. [ ] Read `apps/web/src/components/VoiceAssistantUI.tsx`.
4. [ ] Read `apps/web/src/lib/voice-agent-client.ts`.

## Backend Runtime Metadata

5. [ ] Add server-side config fields for:
   - `CLAIMVOICE_VOICE_RUNTIME`
   - `GEMINI_LIVE_MODEL`
   - `GEMINI_LIVE_VOICE`
6. [ ] Add a safe runtime metadata endpoint or extend an existing status endpoint.
7. [ ] Return only non-secret runtime metadata.
8. [ ] Do not return `GEMINI_API_KEY`.

## Frontend Status

9. [ ] Add runtime status to the voice page.
10. [ ] Show `Gemini Live configured` only when env is present.
11. [ ] Show `Browser fallback` when Gemini is missing or disabled.
12. [ ] Do not route microphone audio to Gemini yet.

## Verification

13. [ ] Test with `CLAIMVOICE_VOICE_RUNTIME=gemini-live` and key present.
14. [ ] Test with `CLAIMVOICE_VOICE_RUNTIME=gemini-live` and key missing.
15. [ ] Test with no Gemini runtime selected.
16. [ ] Confirm voice-agent answers still work through existing path.