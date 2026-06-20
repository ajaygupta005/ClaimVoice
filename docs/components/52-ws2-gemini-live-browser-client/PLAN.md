# Component 52 - WS-2 Gemini Live Browser Client - Implementation Plan

## Inspect

1. [ ] Read `apps/web/src/components/VoiceAssistantUI.tsx`.
2. [ ] Read existing browser STT logic.
3. [ ] Read `apps/web/src/lib/voice-agent-client.ts`.
4. [ ] Read Component 51 bridge contract.

## Browser Session Client

5. [ ] Add a browser-side Gemini runtime client that talks only to ClaimVoice backend.
6. [ ] Do not send `GEMINI_API_KEY` to the browser.
7. [ ] Stream microphone audio or supported frames to backend.
8. [ ] Receive normalized transcript events from backend.

## UI Wiring

9. [ ] Add Gemini runtime branch behind `CLAIMVOICE_VOICE_RUNTIME=gemini-live`.
10. [ ] Show interim transcript in speech preview.
11. [ ] Add final transcript to chat only after final event.
12. [ ] Send final text to the existing voice-agent respond API.
13. [ ] Keep typed input path unchanged.

## Recovery

14. [ ] Add permission timeout.
15. [ ] Add no-transcript timeout.
16. [ ] Add bridge-disconnect handling.
17. [ ] Fall back to browser STT when safe.

## Tests

18. [ ] Manual test with short phrase.
19. [ ] Manual test with longer coverage question.
20. [ ] Manual test interrupting during listening.
21. [ ] Manual test Gemini unavailable fallback.