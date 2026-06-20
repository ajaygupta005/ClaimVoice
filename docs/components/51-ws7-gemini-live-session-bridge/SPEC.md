# Component 51 - WS-7 Gemini Live Session Bridge

> **Workstream**: WS-7 voice-agent runtime  
> **Depends on**: Component 50 - WS-2/WS-7 Voice Runtime Selector

## Goal

Add the first server-side Gemini Live bridge.

This component is backend-only.

It should create and manage a Gemini Live session using the server-side `GEMINI_API_KEY`, but it should not yet replace the browser UI voice flow.

## Required Behavior

The voice-agent service should provide a bridge abstraction that can:

- open a Gemini Live session
- send audio/text input events
- receive transcript events
- receive audio output events
- close the session safely
- report connection errors without crashing the service

## Agent Boundary

Gemini Live is only a voice runtime.

Gemini must not:

- answer insurance questions directly
- choose ClaimVoice tools
- call Eligibility APIs
- call Providers APIs
- bypass Claude
- bypass hallucination guard

Final insurance answers remain owned by the existing ClaimVoice agent flow.

## Runtime Contract

The bridge should emit normalized internal events:

- `session.opened`
- `session.closed`
- `transcript.partial`
- `transcript.final`
- `audio.chunk`
- `error`

The exact Gemini vendor response shape should stay inside the bridge.

## Acceptance Criteria

- Bridge can be instantiated only when `GEMINI_API_KEY` is present.
- Missing key returns a clear unavailable state.
- Bridge can open and close without affecting existing agent API.
- Vendor-specific details are isolated from UI code.
- Unit tests can mock the Gemini client.

## Out of Scope

- Browser microphone streaming.
- UI integration.
- Speaking final Claude answers.
- Twilio integration.
- Replacing Deepgram or Cartesia adapters.

