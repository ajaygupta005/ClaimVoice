# Component 54 - WS-2/WS-7 Gemini Runtime Tests and Fallbacks

> **Workstream**: WS-2 browser voice UI + WS-7 voice-agent runtime  
> **Depends on**: Component 53 - WS-7 Claude Answer to Gemini Speech

## Goal

Harden the Gemini Live voice runtime so the demo never gets stuck.

This component adds tests, recovery behavior, and observability around the complete Gemini voice path.

## Required Failure Handling

The app must recover from:

- microphone permission denied
- microphone stream ended unexpectedly
- Gemini bridge connect failure
- Gemini transcript timeout
- agent response timeout
- Gemini speech output timeout
- playback error
- user interrupt
- browser tab close or route change

Every failure should leave the UI in a usable state.

## Required Observability

Add structured logs or UI-visible debug metadata for:

- runtime selected
- Gemini bridge connection status
- transcript start/end
- final transcript text length
- agent response latency
- speech playback start/end
- fallback reason

Do not log:

- API keys
- raw credentials
- full `.env`
- long raw audio payloads

## Acceptance Criteria

- Gemini happy path works end to end.
- Browser fallback still works when Gemini fails.
- UI never remains stuck in `Listening`, `Thinking`, or `Speaking`.
- Status panel accurately reports active/fallback/unavailable services.
- Unit tests cover bridge failures.
- Manual test checklist is documented and repeatable.

## Out of Scope

- New model providers.
- Production metrics dashboards.
- Twilio phone-call Gemini runtime.
- Long-term transcript storage.

