## Goal

Make the `/dashboard/voice` assistant audibly speak back in the browser using Chrome's built-in Google English voices.

This is a narrow demo reliability component. It does not use Google Cloud Text-to-Speech, Google credentials, or server-side audio synthesis.

## Current Problem

The UI can enter `Speaking`, but the user hears no audio.

The previous working approach used browser `speechSynthesis` with Chrome-provided voices named like:

- `Google UK English Male`
- `Google UK English Female`

The current implementation should restore that simple browser voice path so the demo can be heard locally.

## Required Behavior

### 1. Browser-Only TTS

Use the browser Web Speech API:

```ts
window.speechSynthesis
SpeechSynthesisUtterance
```

Do not require:

- Google Cloud credentials
- `GOOGLE_APPLICATION_CREDENTIALS`
- Google Cloud project id
- backend TTS endpoint
- MP3/audio blob response

### 2. Approved Voices Only

Only use these approved browser voices:

```ts
[
  { name: "Google UK English Male", lang: "en-GB" },
  { name: "Google UK English Female", lang: "en-GB" }
]
```

Do not auto-select random system voices unless explicitly added in a later component.

### 3. Voice Loading

Browser voices may not be available immediately on page load.

The UI must:

- call `window.speechSynthesis.getVoices()`
- listen for the `voiceschanged` event
- refresh the available voice list when voices load
- select `Google UK English Male` by default when available
- fall back to `Google UK English Female` if male is unavailable
- show `Google browser voice unavailable` if neither is present

### 4. Voice Preview

Add a required `Preview voice` button.

When clicked:

- speak a short fixed phrase
- use the selected approved voice
- set status to `Previewing voice`
- return status to `Ready` on end
- show an error if speech is blocked or no approved voice exists

Preview phrase:

```text
ClaimVoice is ready. I will answer using verified plan facts.
```

### 5. Assistant Speak-Back

After the backend returns an assistant answer:

1. append answer to transcript
2. create `SpeechSynthesisUtterance(answer)`
3. assign selected approved Google browser voice
4. tune voice for clarity
5. call `window.speechSynthesis.speak(utterance)`
6. return UI to `Ready` on `onend`

Recommended tuning:

```ts
rate = 0.9
pitch = 0.85 for male
pitch = 0.95 for female
```

### 6. Interrupt and Cleanup

The user must be able to interrupt speech.

If the user taps the mic while speaking:

- call `window.speechSynthesis.cancel()`
- clear TTS timers
- return to listening state

On unmount or reset:

- call `window.speechSynthesis.cancel()`
- remove `voiceschanged` listener
- clear TTS timers

### 7. TTS Watchdog

Browser `speechSynthesis.onend` can be unreliable.

Add a watchdog timeout:

```text
estimatedMs = max(answer.length * 90, 3000) + 5000
```

If the watchdog fires:

- call `speechSynthesis.cancel()`
- mark voice status as timed out
- return UI to `Ready`

### 8. Status Labels

Use honest labels.

Recommended:

- `Voice: Google UK English Male`
- `Voice: Google UK English Female`
- `Voice unavailable`
- `Claude answer`

Avoid:

- `Google Cloud TTS`
- `Claude voice`
- `Claude speaking`

Claude composes the text answer. Chrome's browser voice speaks the text.

## Acceptance Criteria

- UI shows only `Google UK English Male` and `Google UK English Female` as selectable voices.
- `Preview voice` speaks audibly when either approved voice is available.
- Assistant answer is spoken aloud after it appears in transcript.
- UI does not enter `Speaking` if no approved voice exists.
- UI returns to `Ready` after speech ends.
- User can interrupt speech by tapping mic.
- No Google Cloud credentials are required.
- No backend TTS endpoint is required for this component.

## Out of Scope

- Google Cloud Text-to-Speech
- Cartesia / ElevenLabs / OpenAI TTS
- Twilio phone audio return
- Voice cloning
- Streaming audio chunks
- Claude-native voice
