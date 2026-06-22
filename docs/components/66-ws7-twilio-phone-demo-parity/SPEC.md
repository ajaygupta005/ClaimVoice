# Component 66 - WS-7 Twilio Phone Demo Parity

## Purpose

Prove that the telephone AI path reaches the same core agent behavior as the browser voice demo.

## Current State

The browser voice demo is the strongest path. Twilio Media Streams bridge and return-audio path exist, but full parity with the browser voice flow still needs to be verified and hardened.

## Scope

Validate and harden:

- Twilio inbound audio stream
- audio decoding/resampling
- STT path for phone audio
- voice-agent graph invocation
- tool calls
- Claude composition
- guard behavior
- Cartesia or telephony-compatible TTS output
- audio return to Twilio
- call lifecycle logging

## Required Behavior

- A Twilio call can ask the same questions as browser voice.
- The same WS-7 graph handles the turn.
- Tool traces and guard status are logged.
- The caller hears a response.
- Failures end or recover safely.
- Call state does not get stuck after stop, disconnect, or TTS failure.

## Non-Goals

- No production call-center handoff.
- No billing integration.
- No appointment scheduling.
- No new insurance tool scope beyond existing WS-7 tools.

## Acceptance Criteria

- Phone call can complete at least one grounded coverage/cost/formulary/provider turn.
- Audio is returned to the caller.
- Logs include call SID, stream SID, turn ID, tool trace, and guard status.
- Error paths are safe and observable.

