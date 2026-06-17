## Implementation Plan

### 1. Add Browser Voice Discovery

In the voice UI, load approved browser voices from `window.speechSynthesis.getVoices()`.

Approved voices:

```ts
const APPROVED_BROWSER_VOICES = [
  { name: "Google UK English Male", lang: "en-GB" },
  { name: "Google UK English Female", lang: "en-GB" },
] as const
```

Add a `voiceschanged` listener so Chrome can populate voices after initial render.

### 2. Add Selected Voice State

Track:

- `availableApprovedVoices`
- `selectedVoiceName`
- `voiceStatus`

Default selection:

1. `Google UK English Male`
2. `Google UK English Female`
3. unavailable state

If neither approved voice exists, disable speak-back and show a visible unavailable message.

### 3. Add Preview Voice Control

Add a `Preview voice` button near the voice controls.

The button should:

- be disabled when no approved voice exists
- speak the fixed preview phrase
- show success/failure status
- return the UI to `Ready` after playback

Preview phrase:

```text
ClaimVoice is ready. I will answer using verified plan facts.
```

### 4. Replace Current Browser Fallback Selection

Update the existing browser `speechSynthesis` fallback so it does not choose arbitrary voices.

It must:

- use the selected approved Google browser voice
- refuse to speak if no approved voice exists
- show `Voice unavailable` instead of pretending to speak

### 5. Speak Assistant Answers

After an assistant answer is appended to transcript:

- create `SpeechSynthesisUtterance(answer)`
- assign selected approved voice
- set `rate = 0.9`
- set male `pitch = 0.85`
- set female `pitch = 0.95`
- call `window.speechSynthesis.speak(utterance)`

Do not call this `Claude voice`. The label should be the browser voice name.

### 6. Add Interrupt and Watchdog

When speaking starts:

- set state to `speaking`
- store a TTS timer
- cancel any previous speech first

When speaking ends:

- clear timer
- return to `Ready`

When user taps mic during speech:

- call `window.speechSynthesis.cancel()`
- clear timer
- start listening

Watchdog:

```ts
const estimatedMs = Math.max(answer.length * 90, 3000) + 5000
```

If watchdog fires:

- cancel speech
- mark voice status as timed out
- return to `Ready`

### 7. Cleanup

On page unmount or reset:

- cancel speech synthesis
- remove `voiceschanged` listener
- clear TTS timers

### 8. Tests

Manual checks:

1. Open `/dashboard/voice` in Chrome.
2. Confirm approved voices are detected.
3. Click `Preview voice`.
4. Hear audio.
5. Ask: `What is my urgent care copay?`
6. Confirm answer appears in transcript.
7. Confirm answer is spoken aloud.
8. Tap mic during speech.
9. Confirm speech stops and listening starts.

Failure checks:

- If no approved voice exists, preview is disabled.
- If speech errors, UI returns to `Ready`.
- If speech never ends, watchdog returns UI to `Ready`.
