# Component 22 - WS-2 Call History + Tutorial

> **Branch**: `feat/ws2-call-history-and-tutorial` | **Day(s)**: 22 | **Workstream**: WS-2 / WS-7 integration surface

## Goal

Replace the Calls tab placeholder with a frontend call history screen and add a simple tutorial/onboarding flow.

This is a frontend-only component. Real call recording playback and real telephony data are not required yet. The UI should show how past calls and guided onboarding will work once WS-7 is connected.

## Source Data

Use these repo files as reference:

- `docs/components/15-call-flows/SPEC.md`
- `services/telephony/src/api/v1/call.ts`
- `eval/datasets/golden_qa.json`
- `docs/PROJECT_DEEPDIVE.md`

## Scope

Build the Calls tab at:

- `/dashboard/calls`

Also connect the sidebar Tutorial button to a frontend tutorial flow.

The screen should show:

- Mock call history list
- Selected call details
- Transcript preview
- Playback placeholder
- Call status
- Consent / recording status
- Duration and timestamp

The tutorial should explain the basic ClaimVoice workflow in simple language.

## Calls UI

Each mock call should include:

- Call ID
- Caller/member
- Date and time
- Duration
- Status
- Main question
- Assistant summary
- Consent status
- Recording status

The selected call detail panel should show:

- Call summary
- Transcript messages
- Playback placeholder
- Tool/safety outcome if available

## Tutorial UI

The tutorial should be easy for a non-technical user.

Suggested steps:

1. Upload your insurance card.
2. Check the extracted details.
3. Review your plan.
4. Find in-network providers.
5. Ask a question using voice.
6. Review previous calls.

The tutorial can be a modal, drawer, or inline guided panel.

## Out of Scope

- Real Twilio call history API.
- Real recording playback.
- Real encrypted recording decryption.
- Real transcript storage.
- Backend changes.
- Auth or user-specific history.

## Acceptance Criteria

- Calls tab no longer shows a placeholder.
- Mock call history is visible.
- User can select a call.
- Selected call details are visible.
- Transcript preview is visible.
- Playback placeholder is visible.
- Consent/recording status is shown.
- Sidebar Tutorial button opens a tutorial flow.
- Tutorial language is simple and user-friendly.
- UI matches the dashboard shell and previous WS-2 screens.