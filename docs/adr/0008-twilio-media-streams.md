# ADR 0008: Twilio Media Streams with an in-house G.711 codec

## Status

Accepted.

## Context

The telephony service has to carry a live phone call's audio to the voice
agent and back, in real time, low latency. Twilio offers a few ways to get at
call audio: recordings (post-call), `<Gather>`/speech (turn-based), and Media
Streams (a raw bidirectional WebSocket of the call audio).

Twilio Media Streams delivers 8 kHz G.711 mu-law frames. The voice agent works
in PCM16 at 24 kHz. Something has to transcode between the two on every frame.

## Decision

Use **Twilio Media Streams** for the audio path, and a small **in-house G.711
mu-law codec plus linear resampler** (`src/audio_codec/`) for the
8 kHz mu-law <-> 24 kHz PCM16 conversion. No native codec dependency.

## Reasons

- **Media Streams is the only real-time option.** A grounded voice agent needs
  the audio as it happens; recordings and turn-based speech do not fit.
- **The codec is tiny and hot-path-friendly.** mu-law decode is a 256-entry
  table; encode is bit math; resampling is linear interpolation. It runs in a
  few microseconds per second of audio with no native build step, which keeps
  the Docker image small and the deploy simple.
- **Testable.** Pure functions with deterministic output; we pin them with unit
  tests, including G.711 reference values to guard against regressions.

## Consequences

- `twilio_ws/handler.ts` parses Media Streams frames and uses the codec to
  bridge audio both ways through `voice_agent_bridge.ts`.
- Audio quality is bounded by G.711 (telephone quality), which is acceptable —
  the call itself is telephone quality.
- The codec is the single place audio correctness lives; a bug there distorts
  the whole call, so it carries the most direct unit-test coverage.

## Alternatives considered

- **A native codec library** — better quality options exist but add a native
  build, larger images, and platform headaches for a problem G.711 already
  solves.
- **Twilio `<Gather>` speech** — turn-based, higher latency, and gives us
  Twilio's transcription instead of our own STT path.
