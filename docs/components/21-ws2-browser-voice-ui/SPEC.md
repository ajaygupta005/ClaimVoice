# Component 21 - WS-2 Browser Voice UI

## Goal

Replace the Voice tab placeholder with a browser voice assistant UI.

This is a frontend component. It does not need the full WS-6 voice agent yet. The goal is to show the voice interaction surface clearly: push-to-talk, transcript, latest answer, and tool/safety stages.

## Source Data

Use these repo files as reference:

- `docs/PROJECT_DEEPDIVE.md`
- `eval/datasets/golden_qa.json`
- `docs/components/16-halluc-and-coverage-eval/SPEC.md`
- `apps/web/src/components/VoiceChat.tsx`

## Scope

Build the Voice tab at:

- `/dashboard/voice`

The screen should show:

- Browser voice control panel
- Push-to-talk button
- Typed fallback input
- Latest answer card
- Conversation transcript
- Tool-call / safety-check stages
- Voice of google gemini
- Voice/STT/TTS status indicators

## Out of Scope

- Real streaming STT.
- Real Cartesia/Deepgram integration.
- Real Claude/LangGraph orchestration.
- Real hallucination guard API call.
- Backend changes.

## Acceptance Criteria

- Voice tab no longer shows a placeholder.
- Push-to-talk UI is visible.
- Typed fallback input is visible.
- Mock transcript is readable.
- Latest answer is easy to see.
- Tool/safety stages are shown clearly.
- UI states are labelled as mock/demo where needed.
- UI matches dashboard shell and previous WS-2 styling.