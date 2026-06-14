# Component 30 - WS-2 Voice Agent UI Layout

> **Workstream**: WS-2 frontend only  
> **Depends on**: Component 21 - Browser Voice UI

## Goal

Rearrange the Voice tab UI into a better AI telephone-agent demo layout.

This component is only about frontend layout and visual organization. It should not change backend behavior, agent behavior, mock answer logic, database APIs, Twilio, Claude, STT, or TTS.

## Required Layout

Update `/dashboard/voice`.

The page should use the available horizontal space better.

### Top

Show:

- `Voice Assistant`
- short subtitle
- current status pill on the far right:
  - Ready
  - Listening
  - Processing
  - Speaking

### Main Interaction Row

Below the latest answer, show two panels side by side:

#### Left panel: Agent Talk

This is where the user talks to the agent.

Show:

- title: `Agent Talk`
- large push-to-talk button
- mic icon
- waveform or animated dots
- label: `Push to talk`
- typed fallback input under the talk panel

#### Right panel: Transcript

Transcript must be beside Agent Talk, not below it.

Show:

- title: `Transcript`
- message count / simulated label
- member messages on the right
- assistant messages on the left
- readable chat bubbles
- scroll only inside the transcript panel if needed

Agent Talk and Transcript should feel like two parts of the same conversation area.

### Horizontal Agent Pipeline

The agent pipeline must be horizontal, not vertical.

Place it below the Agent Talk + Transcript row.

It should visually span the width of the conversation area.

Pipeline steps:

1. Identify member
2. Understand question
3. Check coverage / formulary / provider
4. Hallucination guard
5. Prepare response

Each step should show:

- small status dot or icon
- title
- short detail
- completed/running/pending visual state

The pipeline should read left-to-right.

### Backend Connections

Backend connections should be much less prominent.

Place them at the extreme right edge of the page/window, as a slim side rail or narrow compact panel.

They should not compete visually with the main demo UI.

Use small LED-style dots:

- green = connected
- gray = demo/mock
- amber = degraded
- red = offline

Rows:

- Voice Agent API
- STT
- TTS
- Hallucination guard
- Telephony bridge

This panel is display-only for now.

## Layout Intent

The user should see this order:

1. Latest answer
2. Agent Talk and Transcript side by side
3. Horizontal pipeline below both
4. Backend connections quietly on the far right

The transcript should not be below Agent Talk.

The pipeline should not be a right-side vertical card.

The backend connections should not be a large prominent card.

## Out of Scope

- No real API calls.
- No real Claude call.
- No real LangGraph.
- No real STT/TTS.
- No Twilio changes.
- No database changes.
- No agent behavior validation yet.
- No mock answer logic changes.

## Acceptance Criteria

- `/dashboard/voice` uses the wide page layout.
- Agent Talk and Transcript are side by side.
- Transcript is not below Agent Talk.
- Agent pipeline is horizontal and below the conversation row.
- Pipeline spans the conversation area left-to-right.
- Backend connections are visible only as a compact far-right status rail/panel.
- Existing mock push-to-talk still works.
- Existing typed input still works.
- Dark mode still works.
- No backend code is changed.