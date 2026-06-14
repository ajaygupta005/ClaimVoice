# Component 24 - WS-7 Voice-Agent WebSocket Receiver

> **Workstream**: WS-7 / WS-6 integration surface  
> **Depends on**: Component 23 - Telephony to Voice-Agent Bridge

## Goal

Add the receiving side of the telephony bridge inside the `voice-agent` service.

Component 23 sends call stream events from telephony. This component makes `voice-agent` accept those events over WebSocket so the phone-call audio has a real backend entry point.

## What This Component Does

Expose a WebSocket endpoint in `voice-agent`:

```text
/api/v1/ws/telephony