## Implementation Plan

### 1. Separate STT, LLM, and TTS Responsibilities

Make the pipeline explicit in naming and status:

```text
Browser STT -> Voice Agent API / LangGraph -> Claude text answer -> TTS provider -> browser audio playback
```

Claude should be displayed as the text composer only. Voice output should be displayed as Google TTS or browser TTS fallback.

### 2. Add a Voice Turn Controller

Create a small client-side controller for one voice turn.

Responsibilities:

- own the current `turnId`
- own the state machine
- own timers
- own browser recognition instance
- own backend abort controller
- own current audio/speech playback
- provide one cleanup method used by all success and failure paths

The cleanup method must:

- stop speech recognition if active
- abort backend request if pending
- stop browser speech synthesis
- pause/clear audio element if used
- clear all timers
- reset UI to `ready`

### 3. Fix Browser STT Finalization

Update mic behavior:

- on first tap, start recognition and enter `listening`
- update `speechPreview` from interim results
- store final recognition text separately
- on second tap, stop recognition and enter `finalizing_stt`
- on recognition end, submit only the best finalized text

Do not append interim text to transcript as a committed user message until finalization.

### 4. Add STT Watchdogs

Add timers:

- `LISTENING_MAX_MS = 12000`
- `SILENCE_AFTER_SPEECH_MS = 2000`
- `MAX_INTERIM_CHARS = 500`

When limits are reached:

- stop recognition
- submit meaningful text if present
- otherwise show recoverable error and reset

### 5. Add Backend Request Watchdog

When submitting to the voice-agent backend:

- enter `thinking`
- create an `AbortController`
- set `BACKEND_TIMEOUT_MS = 20000`
- abort and recover if timeout is reached
- ensure response from an old `turnId` cannot update the current UI

On success:

- append assistant answer once
- update pipeline/guard/tool status
- move to TTS playback

### 6. Add TTS Provider Abstraction

Implement a frontend speak-back helper with this priority:

1. call backend Google TTS endpoint if configured
2. play returned audio in browser
3. fall back to browser `speechSynthesis`

The frontend should not expose API keys.

Recommended backend endpoint:

```text
POST /api/v1/tts/synthesize
```

Recommended Next.js proxy:

```text
POST /api/voice-agent/tts
```

### 7. Add Google TTS Backend Adapter

Add backend config:

- `VOICE_AGENT_TTS_PROVIDER=browser|google`
- `GOOGLE_TTS_VOICE_NAME`
- `GOOGLE_TTS_LANGUAGE_CODE=en-US`
- `GOOGLE_APPLICATION_CREDENTIALS` or existing project credential mechanism

If Google is not configured:

- return a structured unavailable response
- do not crash the voice-agent service
- let browser fallback speak the answer

### 8. Add TTS Playback Watchdog

When speaking starts:

- enter `speaking`
- mark TTS status as active
- stop any previous playback
- set timeout based on estimated answer duration plus 5 seconds

On playback end, cancel, or error:

- clear TTS timer
- return to `ready`

If user taps mic while speaking:

- stop playback immediately
- start a new listening turn

### 9. Add Recovery Controls

Update UI controls:

- mic button starts listening from `ready`
- mic button stops listening from `listening`
- mic button interrupts TTS from `speaking`
- reset action clears current turn and returns to `ready`
- typed input remains available when not actively submitting

The user should never need to refresh the page to continue.

### 10. Tests

Frontend tests:

- initial state is `ready`
- interim STT text updates preview only
- final STT text appends one user message
- duplicate STT final events do not submit twice
- listening timeout recovers
- backend timeout aborts and recovers
- stale backend response is ignored after a newer turn starts
- TTS success returns to `ready`
- TTS failure returns to `ready`
- mic tap during speaking cancels speech and starts listening

Backend tests:

- TTS endpoint returns unavailable when Google config is missing
- TTS endpoint validates non-empty text
- Google adapter response maps to `audioBase64`, `mimeType`, `provider`, and `voiceName`
- TTS failure does not affect Claude answer generation

Manual demo:

1. Open `/dashboard/voice`.
2. Tap mic and speak a question.
3. Confirm interim text appears while speaking.
4. Stop speaking and confirm one user message is submitted.
5. Confirm Claude answer appears.
6. Confirm answer is spoken aloud.
7. Tap mic during speech and confirm speech stops.
8. Ask a second question without refreshing.
9. Temporarily stop backend and confirm UI recovers.
