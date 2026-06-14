# Component 24 - WS-7 Voice-Agent WebSocket Receiver - Implementation Plan

> Build the receiving side for Component 23.

## Inspect

1. [ ] Read `services/voice-agent/src/voice_agent/main.py`.
2. [ ] Read `services/voice-agent/src/voice_agent/api/v1/__init__.py`.
3. [ ] Read `services/telephony/src/twilio_ws/voice_agent_bridge.ts`.
4. [ ] Confirm the bridge event shape from Component 23.

## Design

5. [ ] Add Pydantic schemas for bridge events.
6. [ ] Support three event types: `start`, `audio`, and `stop`.
7. [ ] Track session state in memory for one WebSocket connection.
8. [ ] Use `callSid` and `streamSid` as session identifiers.
9. [ ] Return small JSON acknowledgements for every valid event.
10. [ ] Return safe JSON errors for invalid events.

## Implementation

11. [ ] Create `services/voice-agent/src/voice_agent/schemas/telephony_bridge.py`.
12. [ ] Create `services/voice-agent/src/voice_agent/api/v1/telephony_ws.py`.
13. [ ] Register the WebSocket router from `api/v1/__init__.py`.
14. [ ] Add endpoint:

```text
/api/v1/ws/telephony