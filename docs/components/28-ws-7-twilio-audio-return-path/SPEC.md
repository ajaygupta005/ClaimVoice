# Component 28 - WS-7 Twilio Audio Return Path

> **Workstream**: WS-7 / WS-6 integration surface  
> **Depends on**: Component 27 - Text-to-Speech Response Adapter

## Goal

Send voice-agent speech audio back to the live Twilio caller.

Component 27 produces `tts.audio` events from answer text. This component completes the basic round trip by letting telephony receive those audio events, convert them into Twilio Media Streams format, and send them back over the Twilio WebSocket.

## What This Component Does

Add return-audio handling to the telephony bridge.

The telephony service should:

- listen for outbound audio events from `voice-agent`
- accept `tts.audio` events containing PCM16 24 kHz audio
- decode base64 PCM audio
- resample PCM16 24 kHz to PCM16 8 kHz
- encode PCM16 8 kHz to μ-law
- send Twilio-compatible `media` frames back to the caller
- track bytes sent back to Twilio
- log return-audio state safely

## Input Event From Voice Agent

```json
{
  "type": "tts.audio",
  "callSid": "CA...",
  "streamSid": "MZ...",
  "chunkIndex": 0,
  "isFinal": false,
  "pcm24k": "base64-encoded-pcm16"
}