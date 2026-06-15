## Goal

Make the browser voice assistant reliable during real demo use.

This component focuses on the voice-session lifecycle:

- browser STT is allowed to stream interim text while the user speaks
- each voice turn must finalize, submit, speak back, or recover cleanly
- the user must never get stuck in `listening`, `processing`, or `speaking`
- assistant responses must be spoken aloud using a real TTS layer
- Claude remains the text-answer composer, not the voice provider

## Current Problem

The current UI can recognize speech, but the session lifecycle is fragile:

- STT can keep producing a long running interim transcript.
- The UI can get stuck while listening or after submitting a turn.
- The user may be blocked from asking the next question.
- Assistant text is shown, but not reliably spoken back.
- Connection status is confusing because Claude is shown as connected, but Claude is not a voice.
- There is no watchdog to recover from browser STT, backend, or TTS failures.

## Required Behavior

### 1. Voice Turn State Machine

The browser UI must manage exactly one active voice turn at a time.

Required states:

- `ready`
- `listening`
- `finalizing_stt`
- `thinking`
- `speaking`
- `error_recoverable`

Allowed transitions:

```text
ready -> listening
listening -> finalizing_stt
finalizing_stt -> thinking
thinking -> speaking
speaking -> ready
error_recoverable -> ready
```

If any unexpected condition occurs, the UI must clean up resources and return to `ready`.

### 2. Browser STT Handling

STT is currently browser-based.

When the user taps the mic:

- start browser speech recognition
- show interim text in the Agent Talk panel
- keep interim text visually distinct from submitted transcript text
- allow the user to tap again to stop listening
- finalize only one user message per voice turn

Do not immediately treat every interim result as a submitted question.

### 3. STT Watchdog

The UI must protect itself from browser STT hanging.

Required limits:

- max listening duration: 12 seconds
- silence timeout after speech starts: 2 seconds
- max interim transcript length: 500 characters

When a limit is hit:

- stop recognition
- use the latest final/interim text if it is meaningful
- otherwise show a recoverable error
- always return the mic to a usable state

### 4. Backend Request Watchdog

When the finalized question is submitted:

- call the existing voice-agent backend endpoint
- use an abort controller
- apply a 20 second timeout
- show `thinking` while waiting
- prevent duplicate submissions for the same finalized STT turn

If the backend times out or fails:

- append a short assistant error message
- show retry/reset affordance
- return UI state to `ready`

### 5. Speak-Back TTS

Assistant answers must be spoken aloud after they appear in the transcript.

Preferred TTS provider:

- Google Cloud Text-to-Speech

Fallback:

- browser `speechSynthesis`

Claude must not be labeled as a voice provider. Claude composes the text answer; TTS speaks it.

### 6. Google TTS Contract

Add a backend TTS abstraction that can synthesize answer text.

Required request shape:

```json
{
  "text": "Your in-network urgent care copay is $75 per visit.",
  "voice": "default",
  "format": "mp3"
}
```

Required response shape:

```json
{
  "audioBase64": "...",
  "mimeType": "audio/mpeg",
  "provider": "google",
  "voiceName": "en-US-Chirp3-HD-*"
}
```

If Google TTS is not configured, the API may return a clear unavailable response and the browser must fall back to `speechSynthesis`.

### 7. TTS Watchdog

TTS playback must never block the next turn.

Required behavior:

- set state to `speaking` while audio is playing
- stop playback if user taps mic
- stop playback if user submits typed text
- recover to `ready` if playback errors
- recover to `ready` if playback exceeds expected duration plus 5 seconds

### 8. User Controls

The UI must provide:

- mic button: start listening when ready
- stop button behavior: stop listening or stop speaking depending on state
- reset voice session action when stuck
- typed input always available unless a backend request is actively submitting

The user must always have a visible way out of a stuck state.

### 9. Connection Status

Connection labels must be honest.

Recommended labels:

- `Voice Agent API`
- `STT: Browser`
- `TTS: Google`
- `TTS: Browser fallback`
- `Guard`
- `Claude`

Status meanings:

- green: active and available
- yellow: degraded/fallback
- gray: inactive/not configured
- red: failed for current turn

### 10. Observability

Add lightweight client-side turn diagnostics.

Each voice turn should track:

- turn id
- state transitions
- STT start/end/error
- backend request start/end/error
- TTS provider
- TTS start/end/error
- cleanup reason

This can be shown in the browser console or an internal debug object. It does not need to be a prominent user-facing panel.

## Acceptance Criteria

- User can tap mic, speak, and see live interim STT text.
- Interim STT text is not submitted repeatedly.
- A finalized utterance is submitted exactly once.
- UI returns to `ready` after successful answer playback.
- User can interrupt speaking by tapping mic again.
- User can ask a second question without refreshing the page.
- If STT hangs, the watchdog stops it and recovers.
- If backend hangs, the request aborts and UI recovers.
- If TTS hangs or fails, playback stops and UI recovers.
- Claude is shown as the text composer, not as the voice provider.
- TTS status shows Google when configured, browser fallback when Google is unavailable.

## Out of Scope

- Real Twilio phone-call speak-back
- Production streaming STT provider integration
- Replacing LangGraph
- Letting Claude control tools
- Appointment scheduling
- Claims adjudication