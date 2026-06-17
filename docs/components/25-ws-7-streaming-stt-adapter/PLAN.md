# Component 25 - WS-7 Streaming STT Adapter - Implementation Plan

> Add transcript generation after the voice-agent receives telephony audio.

## Inspect

1. [ ] Read `services/voice-agent/src/voice_agent/api/v1/telephony_ws.py`.
2. [ ] Read `services/voice-agent/src/voice_agent/streaming/deepgram_stt.py`.
3. [ ] Read `services/voice-agent/src/voice_agent/schemas/telephony_bridge.py`.
4. [ ] Confirm Component 24 currently receives and counts audio frames.

## Design

5. [ ] Define an STT adapter interface.
6. [ ] Add transcript event schemas.
7. [ ] Create a mock STT implementation first.
8. [ ] Keep the interface compatible with future Deepgram or Whisper streaming.
9. [ ] Emit partial transcript events during audio flow.
10. [ ] Emit final transcript event when the stream stops.

## Implementation

11. [ ] Create `services/voice-agent/src/voice_agent/schemas/transcript.py`.
12. [ ] Create `services/voice-agent/src/voice_agent/streaming/stt_adapter.py`.
13. [ ] Add `MockStreamingSTT` implementation.
14. [ ] Update `telephony_ws.py` to instantiate one STT session per WebSocket.
15. [ ] Send transcript events back over the WebSocket after audio is processed.
16. [ ] On `stop`, flush the final transcript event before closing.

## Tests

17. [ ] Add `services/voice-agent/tests/unit/test_stt_adapter.py`.
18. [ ] Test mock STT accepts PCM bytes.
19. [ ] Test partial transcript generation.
20. [ ] Test final transcript generation.
21. [ ] Test empty audio does not crash.
22. [ ] Update WebSocket tests to verify transcript events can be returned.

## Verify

23. [ ] Run voice-agent tests.
24. [ ] Start services.
25. [ ] Send fake `start`, `audio`, and `stop` events to `/api/v1/ws/telephony`.
26. [ ] Confirm transcript events appear in the WebSocket response.
27. [ ] Confirm logs include `callSid`, `streamSid`, frame count, and transcript state.

## Commit

28. [ ] Stage only Component 25 docs, STT adapter code, schemas, and tests.
29. [ ] Commit with:

```bash
git commit -m "feat(voice-agent): add streaming STT adapter"