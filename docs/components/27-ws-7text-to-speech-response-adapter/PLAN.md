# Component 27 - WS-7 Text-to-Speech Response Adapter - Implementation Plan

> Convert final answer text into speech-ready audio events.

## Inspect

1. [ ] Read `services/voice-agent/src/voice_agent/streaming/cartesia_tts.py`.
2. [ ] Read Component 26 answer schemas.
3. [ ] Read Component 24 WebSocket response flow.
4. [ ] Confirm where `answer.final` is emitted.

## Design

5. [ ] Define TTS audio event schema.
6. [ ] Define TTS adapter interface.
7. [ ] Implement a mock TTS adapter first.
8. [ ] Keep interface compatible with future Cartesia or other streaming TTS providers.
9. [ ] Decide maximum text chunk length for speech chunks.
10. [ ] Return base64 PCM16 24 kHz audio chunks.

## Implementation

11. [ ] Create `services/voice-agent/src/voice_agent/schemas/tts.py`.
12. [ ] Create `services/voice-agent/src/voice_agent/streaming/tts_adapter.py`.
13. [ ] Implement `MockStreamingTTS`.
14. [ ] Add text chunking helper.
15. [ ] Update the WebSocket flow to call TTS after `answer.final`.
16. [ ] Send `tts.audio` events over the WebSocket.
17. [ ] Mark the last audio chunk with `isFinal: true`.

## Tests

18. [ ] Add `services/voice-agent/tests/unit/test_tts_adapter.py`.
19. [ ] Test single short answer creates one audio chunk.
20. [ ] Test long answer creates multiple chunks.
21. [ ] Test final chunk has `isFinal: true`.
22. [ ] Test empty answer returns a safe error.
23. [ ] Test generated `pcm24k` is valid base64.
24. [ ] Update WebSocket flow test to verify TTS events after answer generation.

## Verify

25. [ ] Run voice-agent tests.
26. [ ] Send fake transcript final event through the WebSocket.
27. [ ] Confirm answer event is produced.
28. [ ] Confirm one or more `tts.audio` events are produced.
29. [ ] Confirm logs include TTS chunk count and final status.

## Commit

30. [ ] Stage only Component 27 docs, TTS schemas, adapter code, and tests.
31. [ ] Commit with:

```bash
git commit -m "feat(voice-agent): add text-to-speech response adapter"WS-7 Twilio Audio Return Path