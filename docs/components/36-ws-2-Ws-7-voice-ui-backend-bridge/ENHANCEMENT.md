# Component 36 Enhancement - Real Talk Panel UX

## Problem

The Voice tab still feels like a scripted demo.

Current issues:

1. The mic button does not show what the user is saying.
2. The transcript is updated only after recording stops.
3. The text sent to the agent may differ from what the user expected.
4. The Agent Talk panel is filled with demo questions, which makes the “talk” area feel fake.
5. Backend status says some services are live even when they are still mock/demo.
6. Questions like “what can you do?” are escalated instead of answered.

## Goal

Make `/dashboard/voice` feel like an actual voice-agent interaction while still being honest about what is mock vs real.

After this enhancement:

- The left panel should be for live talking, not prefilled demo buttons.
- While the user speaks, the UI should show live/interim recognized text.
- The exact recognized text should be what gets sent to the backend.
- Demo questions should be secondary, hidden, or optional.
- Backend connection labels should accurately say mock/demo/connected.
- Capability/help questions should get a useful answer.

## Required UX Changes

### 1. Replace Demo Question List

Remove the always-visible `Demo Questions` list from the Agent Talk panel.

Do not show six prefilled questions as the primary content.

Instead use one of these:

- a small `Examples` button
- a collapsed examples drawer
- a compact menu near the text input

The default Agent Talk panel should show:

- mic button
- listening state
- live audio waveform
- live transcript preview
- typed fallback input

### 2. Add Live Speech Preview

When the user clicks the mic:

- request microphone permission
- show `Listening...`
- show live waveform activity
- show interim text as the user speaks

Example display:

```text
Listening...
"I need to know if my MRI is covered..."