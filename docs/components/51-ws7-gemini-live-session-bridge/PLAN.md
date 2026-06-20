# Component 51 - WS-7 Gemini Live Session Bridge - Implementation Plan

## Inspect

1. [ ] Read `services/voice-agent/src/voice_agent/streaming/`.
2. [ ] Read `services/voice-agent/src/voice_agent/api/v1/telephony_ws.py`.
3. [ ] Read `services/voice-agent/src/voice_agent/core/config.py`.
4. [ ] Read existing tests under `services/voice-agent/tests/unit/`.

## Bridge Module

5. [ ] Add a Gemini bridge module under the voice-agent service.
6. [ ] Define normalized event types.
7. [ ] Add a small bridge factory.
8. [ ] Lazy-import the Gemini SDK/client.
9. [ ] Keep the module importable without credentials.

## Session Lifecycle

10. [ ] Implement open session.
11. [ ] Implement send input event.
12. [ ] Implement receive event loop.
13. [ ] Implement close session.
14. [ ] Implement error normalization.
15. [ ] Add safe logging without secrets.

## Tests

16. [ ] Test missing key returns unavailable.
17. [ ] Test session open calls mocked Gemini client.
18. [ ] Test transcript events normalize correctly.
19. [ ] Test audio chunks normalize correctly.
20. [ ] Test close is idempotent.

## Commit

21. [ ] Commit with:

```bash
git commit -m "feat(voice-agent): add Gemini Live session bridge"
```

