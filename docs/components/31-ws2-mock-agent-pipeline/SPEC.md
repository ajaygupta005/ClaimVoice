# Component 31 - WS-2/WS-7 Mocked Agent Pipeline

> **Workstream**: WS-2 + WS-7 demo integration  
> **Depends on**: Component 30 - Voice Agent UI Layout

## Goal

Make the Voice tab run through a realistic end-to-end AI telephone-agent flow using mocked integrations.

This component should make the demo feel like the real ClaimVoice system is running:

- Twilio receives/starts a call
- STT creates transcript
- agent identifies member
- tools query insurance data
- Claude produces a grounded answer
- hallucination guard verifies it
- TTS prepares audio response
- transcript and pipeline update in the UI

All of this should use mock adapters and mock data. Do not call real Claude, Deepgram, Cartesia, Twilio, or production database yet.

## Scope

Update `/dashboard/voice`.

Add a mocked agent pipeline that the UI can trigger from:

- push-to-talk simulation
- typed question input

The mock pipeline should return:

- transcript turns
- latest answer
- pipeline steps
- backend connection/call statuses
- mocked tool results
- hallucination guard result

## Mocked Integrations

### Mock Twilio

Represent the phone-call/session layer.

Mock fields:

- `callSid`
- `streamSid`
- caller phone number
- call status
- media stream status

Example:

```json
{
  "provider": "twilio",
  "status": "mock",
  "callSid": "CA-demo-001",
  "streamSid": "MZ-demo-001"
}