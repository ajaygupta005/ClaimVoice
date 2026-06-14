# Component 23 - WS-7 Telephony to Voice-Agent Bridge - Implementation Plan

> Step-by-step. Check off as you go.

### Inspect
1. [ ] Read `services/telephony/src/twilio_ws/handler.ts`.
2. [ ] Read `services/telephony/src/audio_codec/`.
3. [ ] Read `services/telephony/src/server.ts`.
4. [ ] Read `services/voice-agent/src/voice_agent/main.py`.
5. [ ] Read existing WS-7 component docs 13 and 15.

### Bridge design
6. [ ] Define a small voice-agent bridge module.
7. [ ] Decide the bridge event shape for `start`, `audio`, and `stop`.
8. [ ] Include callSid and streamSid on every bridge event.
9. [ ] Make the voice-agent URL configurable from environment.
10. [ ] Add safe no-op/fallback behavior when voice-agent URL is missing.

### Implementation
11. [ ] Open a bridge session when Twilio sends `start`.
12. [ ] Forward decoded PCM audio when Twilio sends `media`.
13. [ ] Close the bridge when Twilio sends `stop`.
14. [ ] Log bridge open/close/failure events.
15. [ ] Do not crash Twilio WebSocket if the bridge fails.

### Tests
16. [ ] Add a fake voice-agent WebSocket test.
17. [ ] Test `start` event forwarding.
18. [ ] Test audio frame forwarding.
19. [ ] Test `stop` event closes the bridge.
20. [ ] Test voice-agent unavailable fallback.

### Verify
21. [ ] Run telephony tests.
22. [ ] Start telephony service.
23. [ ] Simulate Twilio start/media/stop events.
24. [ ] Confirm logs show bridge state.

### Commit
25. [ ] Stage only telephony bridge files, tests, and this component docs.
26. [ ] Commit with:

```bash
git commit -m "feat(telephony): bridge media streams to voice agent"