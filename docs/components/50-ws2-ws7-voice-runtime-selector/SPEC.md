# Component 50 - WS-2/WS-7 Voice Runtime Selector

> **Workstream**: WS-2 browser voice UI + WS-7 voice-agent runtime  
> **Depends on**: Component 36 - WS-2/WS-7 Voice UI Backend Bridge, Component 37 - WS-2/WS-7 Real Agent Strengthening

## Goal

Add a small runtime selection layer that can honestly decide which browser voice path is active.

This component does not connect to Gemini yet.

It only makes the current `.env` values visible to the application in a safe, inspectable way so later components can use:

```env
GEMINI_API_KEY=<server-side only>
GEMINI_LIVE_MODEL=gemini-3.1-flash-live-preview
GEMINI_LIVE_VOICE=Zephyr
CLAIMVOICE_VOICE_RUNTIME=gemini-live
```

## Required Behavior

The app should classify voice runtime as one of:

- `browser`
- `gemini-live-configured`
- `gemini-live-unavailable`
- `fallback`

When `CLAIMVOICE_VOICE_RUNTIME=gemini-live` and `GEMINI_API_KEY` is present, the UI may show:

```text
Gemini Live configured
```

It must not show:

```text
Gemini Live connected
```

until a real bridge is implemented and connected.

## Security

`GEMINI_API_KEY` must never be exposed through:

- `NEXT_PUBLIC_*`
- browser bundles
- client-side logs
- API responses
- frontend status dumps

The browser may only receive safe metadata:

- selected runtime name
- configured model name
- configured voice name
- runtime availability status

## Acceptance Criteria

- Runtime status correctly reflects `.env`.
- UI does not pretend Gemini is active before a bridge exists.
- Missing Gemini key falls back to browser voice path.
- Existing Claude/tool/fact-check behavior is unchanged.
- No Gemini API calls are added in this component.

## Out of Scope

- Gemini Live WebSocket/session bridge.
- Audio streaming.
- Gemini STT.
- Gemini TTS.
- Replacing Claude answer composition.

