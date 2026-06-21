# Component 55 - WS-2/WS-7 Cartesia Skylar Voice Runtime

> **Workstream**: WS-2 browser voice UI + WS-7 voice-agent runtime  
> **Depends on**: Component 35 - Claude Answer Compose, Component 36 - Voice UI Backend Bridge, Component 54 - Runtime Tests and Fallbacks

## Goal

Remove Gemini from the normal user-facing voice flow and make **Cartesia Skylar** the deployed answer voice.

The voice assistant should use:

```text
browser microphone / typed input
  -> ClaimVoice voice-agent backend
  -> LangGraph / tools / Claude answer composer
  -> hallucination guard
  -> Cartesia Skylar TTS
  -> browser audio playback
```

Gemini Live may remain in the codebase only as an explicitly disabled experimental path. It must not appear as the default runtime, default STT label, or default TTS label in the member-facing voice UI.

## Problem

The current UI still surfaces Gemini in the runtime panel and STT label, which makes the demo confusing:

- The user sees `STT: Gemini Live` even when the desired product path is Cartesia speech.
- Gemini Live is not reliable for reading exact guarded answers because it may delay or paraphrase.
- Browser/macOS voices are not deployable as the primary voice.
- The demo needs one clear production story: Claude answers, Cartesia Skylar speaks.

## Required Behavior

### Runtime

- Default runtime must be ClaimVoice backend + Cartesia Skylar TTS.
- Gemini Live must be disabled unless a developer-only opt-in flag is set.
- The normal Voice UI must not show a `Voice runtime: Gemini Live` card.
- The connections panel should show:
  - `Voice Agent API`
  - `STT: Browser` or `STT: Speech Recognition`
  - `TTS: Cartesia Skylar`
  - `Hallucination guard`
  - `Claude answer`

### Speech-To-Text

- Keep browser speech recognition as the default STT for this component.
- If browser STT is unavailable, show a recoverable error and keep typed input usable.
- Do not route normal browser microphone input through Gemini Live.

### Answering

- Continue using the existing ClaimVoice answer pipeline.
- Claude composes the final answer.
- Tools and grounding checks remain unchanged.
- The hallucination guard must run before TTS.
- Only the final guarded answer text may be sent to Cartesia.

### Text-To-Speech

Use Cartesia's HTTP bytes endpoint from the backend:

```bash
curl -X POST https://api.cartesia.ai/tts/bytes \
  -H "Cartesia-Version: 2026-03-01" \
  -H "X-API-Key: <server-side key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "sonic-3.5",
    "transcript": "is lisinopril in my formulary?",
    "voice": {
      "mode": "id",
      "id": "db6b0ed5-d5d3-463d-ae85-518a07d3c2b4"
    },
    "output_format": {
      "container": "wav",
      "encoding": "pcm_s16le",
      "sample_rate": 44100
    },
    "language": "en",
    "generation_config": {
      "speed": 1,
      "volume": 1
    }
  }' \
  --output cartesia-skylar.wav
```

The backend endpoint should return the generated WAV as base64 to the browser:

```json
{
  "ok": true,
  "provider": "cartesia",
  "voiceName": "Skylar",
  "mimeType": "audio/wav",
  "audioBase64": "..."
}
```

### Environment

Add or use these server-side variables:

```env
VOICE_AGENT_TTS_PROVIDER=cartesia
CARTESIA_API_KEY=
CARTESIA_TTS_MODEL=sonic-3.5
CARTESIA_VOICE_NAME=Skylar
CARTESIA_VOICE_ID=db6b0ed5-d5d3-463d-ae85-518a07d3c2b4
CARTESIA_TTS_LANGUAGE=en
CARTESIA_TTS_SAMPLE_RATE=44100
CARTESIA_TTS_CONTAINER=wav
CARTESIA_TTS_ENCODING=pcm_s16le
CARTESIA_TTS_SPEED=1
CARTESIA_TTS_VOLUME=1
```

Do not expose `CARTESIA_API_KEY` to the browser.

## UI Requirements

- The Agent Talk panel should show `Voice: Cartesia Skylar`.
- The Preview button should call the same backend Cartesia TTS endpoint with a short preview phrase.
- The connection LED should show `TTS: Cartesia Skylar` when Cartesia audio is returned.
- If Cartesia fails, the UI may fall back to browser TTS, but the fallback must be clearly labeled as fallback.
- Do not show Gemini in the normal visible runtime UI.
- Do not show "Google UK English Male" when Cartesia is the configured provider.

## Backend Requirements

- Implement Cartesia TTS through an HTTP client matching the documented curl payload.
- Send `Cartesia-Version: 2026-03-01`.
- Send `X-API-Key` from server settings only.
- Use `sonic-3.5`.
- Use Skylar voice id `db6b0ed5-d5d3-463d-ae85-518a07d3c2b4`.
- Request `wav`, `pcm_s16le`, `44100`.
- Enforce max input length before calling Cartesia.
- Timeout Cartesia calls.
- Return a structured fallback response on failure.
- Never log API keys or full request headers.

## Observability

Log:

- selected TTS provider
- Cartesia model
- Cartesia voice name/id suffix only
- request text length
- synthesis latency
- returned audio byte length
- fallback reason

Do not log:

- full API key
- full member transcript if not needed
- raw audio payloads

## Acceptance Criteria

- Voice UI no longer shows Gemini in the default member-facing flow.
- Runtime panel does not display `Gemini Live configured` by default.
- Connections show `TTS: Cartesia Skylar` after speech playback starts.
- The answer spoken aloud is exactly the final guarded ClaimVoice answer text.
- Cartesia key is used only by the backend.
- A missing or invalid Cartesia key does not freeze the UI.
- Preview voice button plays Cartesia Skylar when configured.
- Browser/macOS TTS is fallback only, not the primary deployed voice.
- Tests cover Cartesia success, missing key, HTTP failure, timeout, and fallback.

## Out of Scope

- Removing Gemini source files entirely.
- Twilio phone-call voice return path changes.
- ElevenLabs or Google Cloud TTS.
- Long-term transcript storage.
- Voice cloning.
