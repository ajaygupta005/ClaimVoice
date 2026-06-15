## Fix 1: Make the Agent Talk Back and Stop Getting Stuck

## Problem

The current voice assistant proves that browser STT is working, because spoken words appear as live text. The broken parts are after STT:

- the assistant does not reliably talk back
- the UI can remain stuck in a listening/processing/speaking state
- the user can be blocked from asking the next question
- the flow feels weak because the turn is not clearly closed before the next turn starts
- Claude is being treated like a voice provider, but Claude only produces text

This fix makes one complete voice turn reliable before adding more advanced behavior.

## Required Outcome

One user voice turn must work like this:

```text
tap mic
-> browser listens
-> live speech preview appears
-> user stops or silence timeout fires
-> final text is submitted once
-> backend returns answer text
-> answer is shown in transcript
-> answer is spoken aloud
-> playback ends
-> UI returns to Ready
```

After this sequence, the user must be able to immediately ask another question without refreshing the page.

## Priority 1: Speak-Back Must Work

The agent must audibly respond after every successful backend answer.

Implement speak-back in this order:

1. Browser `speechSynthesis` fallback first, because it requires no external credentials.
2. Google Cloud TTS next, behind config, once the local flow is stable.

Do not wait for Google TTS before fixing the demo. Browser TTS is enough for the first working speak-back.

Required behavior:

- call speak-back after assistant answer is appended to transcript
- set UI state to `speaking`
- show TTS status as `Browser fallback` or `Google`
- when speech ends, return to `Ready`
- if speech errors, cancel it and return to `Ready`
- if user taps mic while speaking, stop speech immediately and start listening

Claude should be labeled as `Claude text composer`, not as a voice.

## Priority 2: Add a Hard Turn Watchdog

Every voice turn must have a timeout and cleanup path.

Required timers:

- listening max: 12 seconds
- silence after speech: 2 seconds
- backend response max: 20 seconds
- speak-back max: estimated speech duration plus 5 seconds

Every timer must call the same cleanup/recovery path.

Cleanup must:

- stop speech recognition
- clear STT callbacks for the old turn
- abort the backend request if still pending
- cancel browser speech synthesis
- pause and clear any audio element
- clear all timers
- mark current turn as closed
- return UI to `Ready`

## Priority 3: Prevent Duplicate or Stale Turns

Use a `turnId` for every user interaction.

Rules:

- only the current `turnId` can update UI state
- old STT callbacks must be ignored
- old backend responses must be ignored
- old TTS callbacks must be ignored
- one finalized STT result must create only one user transcript message

This prevents the UI from responding to stale browser events after the user has already moved on.

## Priority 4: Fix STT Finalization

STT should show interim text while listening, but should not submit every interim update.

Required behavior:

- interim text appears only in the Agent Talk preview
- transcript gets a user message only after finalization
- finalization happens when:
  - user taps stop
  - browser recognition emits final result and ends
  - silence timeout fires
  - max listening timeout fires

If no meaningful text is captured:

- show a small recoverable message like “I did not catch that.”
- return to `Ready`
- do not call backend

## Priority 5: Stronger User Controls

The user must always have a way out.

Required controls:

- mic button in `Ready`: start listening
- mic button in `Listening`: stop and finalize
- mic button in `Speaking`: stop speech and start new listening turn
- reset button: cancel everything and return to `Ready`
- typed input: available whenever no backend request is actively submitting

The app must never require a browser refresh to recover.

## Priority 6: Connection Status Should Reflect Reality

Use honest labels:

- `Voice Agent API`: green when backend responds
- `STT: Browser`: green while browser STT is available/listening
- `TTS: Browser fallback`: yellow when using browser speech synthesis
- `TTS: Google`: green only when Google TTS is configured and used
- `Guard`: green/yellow/red based on current answer
- `Claude`: green only when backend response says `composer_mode=claude`

Do not show STT/TTS as fully connected cloud services unless they are actually configured.

## Priority 7: Make the Flow Feel Stronger

The user should understand what is happening.

During one turn, show short status text:

- `Listening...`
- `Finalizing speech...`
- `Checking plan...`
- `Composing answer...`
- `Speaking answer...`
- `Ready`

The horizontal pipeline should update with these stages and not stay frozen.

## Acceptance Criteria

- User speaks and sees live text.
- User stops speaking and exactly one user message is submitted.
- Backend answer appears in transcript.
- Assistant audibly speaks the answer.
- UI returns to `Ready` after speech completes.
- User can ask a second voice question without refreshing.
- User can interrupt speech by tapping mic.
- Long-running STT is stopped by watchdog.
- Hung backend request is aborted.
- Failed TTS does not block the next turn.
- Reset button always recovers the UI.

## Out of Scope for Fix 1

- Production Twilio audio return
- Full Google TTS rollout if browser TTS is not stable yet
- Claude choosing tools dynamically
- New insurance reasoning logic
- Appointment scheduling
- Claims processing

## Demo Script

1. Open `/dashboard/voice`.
2. Tap mic.
3. Say: “What is my urgent care copay?”
4. Confirm live speech preview appears.
5. Stop speaking.
6. Confirm the question is submitted once.
7. Confirm answer appears.
8. Confirm answer is spoken aloud.
9. While answer is speaking, tap mic again.
10. Confirm speech stops and new listening starts.
11. Ask a second question.
12. Confirm no refresh is needed.
