# Component 55 - Cartesia Skylar Voice Runtime: Results

## What was implemented

- Cartesia Skylar is now the preferred high-quality answer speakback path.
- The backend voice-agent service calls Cartesia `/tts/bytes` directly over HTTP.
- Cartesia uses `sonic-3.5`, WAV output, `pcm_s16le`, 44.1 kHz, and the Skylar voice id.
- `CARTESIA_API_KEY` stays server-side and is never returned to the browser.
- The web UI labels the active voice as Skylar when Cartesia is configured.
- The UI shows the answer text immediately, then prepares and plays the Cartesia audio.
- Gemini Live is no longer the default member-facing voice path; it remains opt-in for experiments.
- Browser STT remains the default microphone path for local demo stability.

## Reliability behavior

- Missing Cartesia key does not crash the TTS endpoint.
- Cartesia HTTP errors, timeouts, and request errors return a safe fallback path.
- Playback watchdogs return the UI to `Ready` if audio fails to start or finish.
- User interruption stops active playback and releases audio resources.

## Verification

- Voice-agent focused TTS/runtime tests pass.
- Web typecheck passes.
- Manual browser demo now speaks back using Cartesia Skylar when configured.

## Remaining follow-up

- Move to streaming Cartesia TTS if latency is still noticeable.
- Add browser automation around configured/unconfigured TTS states.
- Decide whether to delete Gemini runtime code after the Cartesia path is stable.
