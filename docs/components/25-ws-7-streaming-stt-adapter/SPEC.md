# Component 25 - WS-7 Streaming STT Adapter

> **Workstream**: WS-7 / WS-6 integration surface  
> **Depends on**: Component 24 - Voice-Agent WebSocket Receiver

## Goal

Convert received telephony audio frames into transcript events.

Component 24 receives validated `start`, `audio`, and `stop` events from telephony. This component adds the next layer: an STT adapter that accepts PCM audio frames and emits transcript chunks that later components can use for answer generation.

## What This Component Does

Add a small speech-to-text adapter inside `voice-agent`.

For now, this can be implemented as a deterministic mock adapter. The important part is the interface and event flow, not a production STT provider.

The adapter should:

- accept PCM16 24 kHz audio frames
- track per-call transcript state
- emit partial transcript events
- emit final transcript events
- handle silence or empty audio safely
- expose a clean interface for later Deepgram / Whisper integration

## STT Event Shape

### Partial Transcript

```json
{
  "type": "transcript.partial",
  "callSid": "CA...",
  "streamSid": "MZ...",
  "text": "is an MRI",
  "confidence": 0.82
}