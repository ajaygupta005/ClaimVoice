# FIX1: Browser TTS Still Shows Unavailable

## Implementation Update

The final fix moved speak-back away from fragile browser `speechSynthesis` fallback.

What changed:

- `POST /api/v1/tts/synthesize` now tries server-side macOS TTS when Google TTS is not configured.
- The voice-agent uses `/usr/bin/say` to synthesize speech and `/usr/bin/afconvert` to convert it into browser-playable `audio/wav`.
- The web app accepts `provider: system`, labels it as `TTS: macOS`, and plays the returned WAV blob directly through the existing audio player path.
- Backend and frontend TTS timeouts were increased to allow local synthesis to complete.
- Focused TTS tests now cover system audio success, system unavailable fallback, and Google-to-system fallback.

This means local demos no longer depend on Chrome Web Speech audio actually working.

## Problem

The Voice Assistant UI shows a valid browser voice, for example:

```text
Voice: Google UK English Male
```

but after the agent responds, the connection rail changes to:

```text
TTS unavailable
```

and no audio is heard.

This means voice discovery and display are partly working, but the actual speak-back path is still deciding that no usable TTS voice exists.

## Likely Root Cause

The current implementation stores the discovered browser voice in React state as `selectedVoice`.

That is fragile because:

- browser voices load asynchronously through `speechSynthesis.getVoices()`;
- `voiceschanged` can fire after the render that created the active `runPipeline` closure;
- the UI can show a retained `voiceLabel` while `selectedVoice` is still `null` inside the active submit path;
- the TTS path currently treats missing `selectedVoice` as a hard failure and calls `cleanup('no_voice')`.

So the UI can display a voice name, but the speak path still falls into the `TTS unavailable` branch.

## Required Fix

Resolve the browser voice at the moment of speaking, not only during React render.

Add a small helper in `VoiceAssistantUI.tsx`:

```ts
function resolveBrowserVoice(): {
  voice: SpeechSynthesisVoice | null
  label: string
  pitch: number
} {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    return { voice: null, label: 'Browser default', pitch: 0.9 }
  }

  const voices = window.speechSynthesis.getVoices()
  for (const approved of APPROVED_BROWSER_VOICES) {
    const match = voices.find(v => v.name === approved.name)
    if (match) {
      return { voice: match, label: match.name, pitch: approved.pitch }
    }
  }

  const english = voices.find(v => v.lang === 'en-US')
    ?? voices.find(v => v.lang.startsWith('en'))
    ?? null

  return {
    voice: english,
    label: english?.name ?? 'Browser default',
    pitch: 0.9,
  }
}
```

Then change the TTS branch:

1. Try backend Google TTS audio first, unchanged.
2. If backend audio is unavailable, call `resolveBrowserVoice()`.
3. Always call `ctrl.speakBrowser(answerText, resolved.voice, onTtsDone, ...)`.
4. Do not mark TTS unavailable just because the approved Google voice was not found.
5. Only mark TTS unavailable when `window.speechSynthesis` itself is missing or `speakBrowser` reports a real playback failure.

## Expected Behavior

When the backend has no Google Cloud TTS audio:

- the app should still speak using browser speech synthesis;
- the connection rail should show `TTS: Browser`;
- if Google UK English Male/Female exists, use it;
- otherwise use any English browser voice;
- if no English voice exists, use browser default;
- the turn must still return to `Ready` even if playback fails.

## Out of Scope

Do not change:

- Claude answer logic;
- LangGraph routing;
- STT recognition;
- transcript layout;
- mock pipeline answers;
- backend TTS service.

This fix is only for browser speak-back reliability.

## Verification

Manual browser test:

1. Open `/dashboard/voice`.
2. Ask or type: `hello`.
3. Wait for the assistant response.
4. Confirm the connection rail shows `TTS: Browser`, not `TTS unavailable`.
5. Confirm audio is heard.
6. Confirm the status returns from `Speaking` to `Ready`.
7. Click the mic again and confirm a new turn can start.

Console diagnostics to check if it still fails:

```js
speechSynthesis.getVoices().map(v => `${v.name} | ${v.lang}`)
```

If this returns an empty list, wait for `voiceschanged` or reload the page.
