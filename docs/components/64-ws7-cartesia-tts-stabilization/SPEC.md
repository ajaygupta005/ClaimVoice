# Component 64 - WS-7 Cartesia TTS Stabilization

## Purpose

Make Cartesia the stable WS-7 text-to-speech path for browser demo and prepare it for telephony use, while isolating Gemini Live from the primary product path.

## Current State

Cartesia speech is the strongest working voice output path. Earlier browser speech and Gemini Live experiments caused runtime confusion and inconsistent answer ownership.

## Scope

Stabilize:

- Cartesia provider configuration
- TTS status reporting
- timeout behavior
- cancellation behavior
- retry behavior
- text-first response display
- audio playback error handling
- Gemini isolation/removal from default path

## Required Behavior

- Final text answer appears as soon as it is ready.
- Cartesia audio starts when synthesized audio is available.
- If TTS fails, the text answer remains usable.
- User can ask another question after success, failure, or cancellation.
- Runtime status clearly says Cartesia when Cartesia is selected.
- Gemini is not shown as the active voice path unless explicitly enabled as experimental.

## Non-Goals

- No new answer generation.
- No new tool routing.
- No voice cloning.
- No production STT provider selection.

## Acceptance Criteria

- Cartesia status is visible and accurate.
- Cartesia failures do not block the next turn.
- Gemini is not the default voice path.
- TTS tests cover success, timeout, cancellation, and provider error.

