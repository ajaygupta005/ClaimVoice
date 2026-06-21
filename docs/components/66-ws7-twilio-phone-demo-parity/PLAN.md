# Component 66 - WS-7 Twilio Phone Demo Parity Plan

## Implementation Steps

1. Review current telephony bridge.
   - Twilio WebSocket handler.
   - Voice-agent bridge.
   - Audio codec/resampling.
   - Return-audio path.

2. Define phone demo script.
   - Greeting.
   - Member verification.
   - Coverage question.
   - Cost question.
   - Provider question.
   - Safe escalation.

3. Validate inbound audio path.
   - Twilio media frames arrive.
   - Audio converts correctly.
   - STT receives usable audio.
   - Transcripts reach the agent graph.

4. Validate agent path.
   - Same graph as browser voice.
   - Same tool mode.
   - Same guard behavior.
   - Same answer composer.

5. Validate outbound audio path.
   - Cartesia or telephony-compatible TTS produces audio.
   - Audio converts to Twilio format.
   - Media frames are sent back.
   - Caller hears the answer.

6. Add observability.
   - Call SID.
   - Stream SID.
   - Turn ID.
   - bytes in/out.
   - STT status.
   - TTS status.
   - tool trace.
   - guard result.

7. Add tests.
   - Twilio inbound frame handling.
   - Bridge open/close.
   - Return-audio conversion.
   - Failure recovery.

## Suggested Files

- `services/telephony/src/twilio_ws/*`
- `services/voice-agent/src/voice_agent/api/v1/ws.py`
- `services/voice-agent/src/voice_agent/streaming/*`
- `services/telephony/tests/*`
- `services/voice-agent/tests/*`

## Validation

- Telephony unit tests.
- Voice-agent unit tests.
- Manual Twilio test call.
- Logs reviewed for call and turn trace.

## Risks

- Browser voice and phone audio have different latency and format constraints.
- TTS output may need telephony-specific sample rate conversion.
- STT for phone audio may need a provider beyond browser STT.

## Done When

- The phone path can demonstrate the same insurance agent behavior as the browser path.
- Call failures are observable and recoverable.
- The team can run a repeatable phone demo without guessing from logs.

