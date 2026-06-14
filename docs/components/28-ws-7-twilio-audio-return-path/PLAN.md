# Component 28 - WS-7 Twilio Audio Return Path - Implementation Plan

> Send generated assistant speech audio back to the Twilio caller.

## Inspect

1. [ ] Read `services/telephony/src/twilio_ws/handler.ts`.
2. [ ] Read `services/telephony/src/twilio_ws/voice_agent_bridge.ts`.
3. [ ] Read `services/telephony/src/audio_codec/index.ts`.
4. [ ] Read Component 27 TTS event schema.
5. [ ] Confirm `pcm16ToTwilioFrame()` already exists or add equivalent helper.

## Design

6. [ ] Define a telephony-side schema for `tts.audio`.
7. [ ] Add a callback from `VoiceAgentBridge` to the active Twilio socket.
8. [ ] Keep inbound caller audio and outbound assistant audio separate.
9. [ ] Update `bytesOut` when audio is sent to Twilio.
10. [ ] Ignore non-audio voice-agent events unless they are needed for logging.

## Implementation

11. [ ] Update `services/telephony/src/twilio_ws/voice_agent_bridge.ts`.
12. [ ] Add support for receiving messages from the voice-agent WebSocket.
13. [ ] Parse `tts.audio` messages.
14. [ ] Decode `pcm24k` from base64.
15. [ ] Pass PCM24k audio to a return-audio callback.
16. [ ] Update `handler.ts` to send returned audio to the Twilio socket.
17. [ ] Use Twilio media frame format:

```json
{
  "event": "media",
  "streamSid": "...",
  "media": {
    "payload": "..."
  }
}