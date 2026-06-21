# Component 53 - WS-7 Claude Answer to Gemini Speech - Implementation Plan

## Inspect

1. [ ] Read Component 51 bridge code.
2. [ ] Read Component 52 browser runtime code.
3. [ ] Read `apps/web/src/lib/tts-client.ts`.
4. [ ] Read existing speak-back/watchdog logic.

## Backend Speech Output

5. [ ] Add bridge method for text-to-speech through Gemini Live.
6. [ ] Accept final answer text only after guard completes.
7. [ ] Return normalized audio events.
8. [ ] Preserve fallback to browser/system TTS.

## Frontend Playback

9. [ ] Play Gemini audio chunks or returned audio.
10. [ ] Mark `Speaking` only after playback begins.
11. [ ] Show `Voice: Gemini Live`.
12. [ ] Show `Answer: Claude`.
13. [ ] Add interruption during playback.
14. [ ] Clean up audio resources on unmount.

## Watchdog

15. [ ] Add playback-start timeout.
16. [ ] Add playback-end timeout.
17. [ ] Return to `Ready` after timeout.
18. [ ] Log a useful runtime reason.

## Tests

19. [ ] Test answer text is passed to speech layer.
20. [ ] Test playback success.
21. [ ] Test playback failure fallback.
22. [ ] Test interrupt while speaking.
23. [ ] Test no duplicate submit after interrupt.