# Component 55 - WS-2/WS-7 Cartesia Skylar Voice Runtime - Implementation Plan

## Inspect

1. [ ] Read the current Voice UI runtime labels in `apps/web/src/components/VoiceAssistantUI.tsx`.
2. [ ] Read current TTS client code in `apps/web/src/lib/tts-client.ts`.
3. [ ] Read current backend TTS endpoint in `services/voice-agent/src/voice_agent/api/v1/tts_synthesize.py`.
4. [ ] Read current settings in `services/voice-agent/src/voice_agent/core/config.py`.
5. [ ] Confirm where Gemini runtime status is displayed and how to hide it from the default flow.

## Runtime Selection

6. [ ] Set the default user-facing voice runtime to ClaimVoice backend + Cartesia TTS.
7. [ ] Keep Gemini Live behind an explicit developer-only opt-in flag.
8. [ ] Remove Gemini from the normal Voice UI runtime card.
9. [ ] Ensure default microphone path uses browser STT unless a future component replaces it.
10. [ ] Keep typed input working regardless of STT provider.

## Backend Cartesia TTS

11. [ ] Add Cartesia Skylar settings:
    - `CARTESIA_API_KEY`
    - `CARTESIA_TTS_MODEL=sonic-3.5`
    - `CARTESIA_VOICE_NAME=Skylar`
    - `CARTESIA_VOICE_ID=db6b0ed5-d5d3-463d-ae85-518a07d3c2b4`
    - `CARTESIA_TTS_LANGUAGE=en`
    - `CARTESIA_TTS_SAMPLE_RATE=44100`
    - `CARTESIA_TTS_CONTAINER=wav`
    - `CARTESIA_TTS_ENCODING=pcm_s16le`
    - `CARTESIA_TTS_SPEED=1`
    - `CARTESIA_TTS_VOLUME=1`
12. [ ] Implement a direct backend HTTP call to `https://api.cartesia.ai/tts/bytes`.
13. [ ] Send `Cartesia-Version: 2026-03-01`.
14. [ ] Send `X-API-Key` only from server-side settings.
15. [ ] Use the exact payload structure from the component spec.
16. [ ] Return `audio/wav` base64 to the web client.
17. [ ] Add request timeout and max transcript length protection.
18. [ ] Return a structured `ok=false` fallback response on missing key, timeout, or non-2xx response.

## Frontend Voice UI

19. [ ] Relabel active TTS as `TTS: Cartesia Skylar`.
20. [ ] Relabel Agent Talk voice row as `Voice: Cartesia Skylar`.
21. [ ] Remove `Google UK English Male` from the primary voice label when Cartesia is configured.
22. [ ] Remove normal `STT: Gemini Live` label from the connections panel.
23. [ ] Remove normal `Voice runtime: Gemini Live configured` card from the member-facing UI.
24. [ ] Keep fallback labels explicit, for example `TTS: Browser fallback`.
25. [ ] Make Preview call the same backend TTS endpoint with a short preview phrase.
26. [ ] Ensure speech playback uses returned WAV audio rather than browser speech synthesis when Cartesia succeeds.

## Failure Handling

27. [ ] Missing `CARTESIA_API_KEY` should show Cartesia unavailable without blocking typed input.
28. [ ] Cartesia 401/403 should show configuration error and fall back cleanly.
29. [ ] Cartesia timeout should return UI to `Ready`.
30. [ ] Playback error should return UI to `Ready`.
31. [ ] User interrupt should stop active audio immediately.
32. [ ] Route change should stop active audio and release resources.

## Observability

33. [ ] Log selected provider, model, voice name, and voice id suffix.
34. [ ] Log TTS latency and returned audio size.
35. [ ] Log fallback reason.
36. [ ] Do not log API keys.
37. [ ] Do not log raw audio bytes.

## Tests

38. [ ] Unit test Cartesia success response.
39. [ ] Unit test missing Cartesia key.
40. [ ] Unit test Cartesia non-2xx response.
41. [ ] Unit test Cartesia timeout.
42. [ ] Unit test frontend provider label mapping.
43. [ ] Manual test Preview button.
44. [ ] Manual test spoken answer after typed question.
45. [ ] Manual test spoken answer after voice question.

## Run

46. [ ] Run voice-agent unit tests.
47. [ ] Run web typecheck.
48. [ ] Start app with `VOICE_AGENT_TTS_PROVIDER=cartesia`.
49. [ ] Verify `/api/v1/tts/synthesize` returns `provider=cartesia`.
50. [ ] Verify UI displays `TTS: Cartesia Skylar` and no default Gemini runtime card.

## Rollback

51. [ ] Allow `VOICE_AGENT_TTS_PROVIDER=browser` to restore browser fallback.
52. [ ] Keep Gemini code untouched unless explicitly removed in a later cleanup component.
