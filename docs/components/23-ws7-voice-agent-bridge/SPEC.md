# Component 23 - WS-7 Telephony to Voice-Agent Bridge

> **Branch**: `feat/ws7-voice-agent-bridge` | **Day(s)**: 23 | **Workstream**: WS-7 / WS-6 integration surface

## Goal

Connect the telephony media stream layer to the voice-agent service.

Earlier WS-7 components handle Twilio webhooks, Media Streams, audio codec, consent, and call flow. This component defines the missing bridge from decoded Twilio audio into the voice-agent runtime.

## Scope

Add the bridge layer between:

- Twilio Media Streams WebSocket
- Telephony audio codec
- Voice-agent WebSocket or local stub

The bridge should handle:

- callSid and streamSid tracking
- start event forwarding
- decoded PCM audio forwarding
- stop event forwarding
- voice-agent connection lifecycle
- voice-agent unavailable fallback
- structured logs for bridge state

## Expected Behavior

When Twilio sends a `start` event:

- Store callSid and streamSid.
- Open a voice-agent bridge session.
- Send call/session metadata to the voice-agent side.

When Twilio sends a `media` event:

- Decode μ-law audio.
- Resample if needed.
- Forward PCM audio frames to the voice-agent bridge.

When Twilio sends a `stop` event:

- Close the voice-agent bridge.
- Mark the call session as ended.
- Flush logs/metrics.

If the voice-agent service is unavailable:

- Do not crash the telephony WebSocket.
- Log the failure with callSid/streamSid.
- Return or play a safe fallback path where possible.
- Close the bridge cleanly.

## Out of Scope

- Full LangGraph implementation.
- Claude tool calling.
- Speech-to-text implementation.
- Text-to-speech implementation.
- Real hallucination guard logic.
- Production-scale retry queue.

Those belong mainly to WS-6.

## Acceptance Criteria

- Telephony can create a bridge session for a Twilio stream.
- Start/media/stop events are forwarded in the expected shape.
- Audio frames are decoded before forwarding.
- Voice-agent unavailable case is handled safely.
- Logs include callSid, streamSid, and bridge status.
- Unit tests or integration tests cover a fake voice-agent WebSocket.