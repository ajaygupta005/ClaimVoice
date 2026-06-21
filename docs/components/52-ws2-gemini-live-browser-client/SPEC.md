# Component 52 - WS-2 Gemini Live Browser Client

> **Workstream**: WS-2 browser voice UI  
> **Depends on**: Component 51 - WS-7 Gemini Live Session Bridge

## Goal

Connect the `/dashboard/voice` browser UI to the ClaimVoice Gemini Live bridge for speech input.

This component focuses on STT and transcript behavior only.

It should not implement Gemini speak-back yet.

## Required Behavior

When Gemini runtime is active:

1. user taps mic
2. browser requests microphone permission
3. audio is streamed to the ClaimVoice backend bridge
4. UI shows interim transcript while the user speaks
5. UI adds a final user transcript only when Gemini emits final text
6. final text is sent to the existing ClaimVoice agent endpoint

The final transcript must use what the user actually said.

It must not replace speech with a demo question.

## UI States

Required states:

- `Ready`
- `Listening`
- `Transcribing`
- `Thinking`
- `Error`

Do not enter `Speaking` in this component.

## Fallback

If Gemini bridge fails:

- stop the Gemini session
- fall back to existing browser STT if available
- show a visible fallback status

## Acceptance Criteria

- Mic input reaches backend Gemini bridge.
- Interim transcript appears while speaking.
- Final transcript appears as the user message.
- Final transcript is sent to `/api/v1/agent/respond`.
- Existing typed input still works.
- No Gemini answer or Gemini TTS is used in this component.

## Out of Scope

- Gemini audio speak-back.
- Server-side answer composition changes.
- Tool routing changes.
- Twilio phone audio.

