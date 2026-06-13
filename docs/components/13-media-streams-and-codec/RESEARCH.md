# Component 13 - Twilio Media Streams + Audio Codec - Research

## G.711 mu-law

Twilio sends 20 ms frames of 8-bit mu-law at 8 kHz. To run anything modern
through it (Deepgram, Whisper, Cartesia) we need PCM16 at 16 or 24 kHz.

mu-law decode is a 256-entry lookup table. Encode is bit math. Both run in a
handful of microseconds per second of audio.

## Resampling

Three reasonable options:

| Approach | Quality | Speed |
| --- | --- | --- |
| Nearest neighbor | bad (audible artifacts) | fastest |
| Linear interp | good enough for voice | fast |
| Sinc (windowed) | best | slow, more code |

Linear interpolation with a fractional accumulator gives the right quality
for voice without pulling in a DSP library.

## Why @fastify/websocket

Native Fastify plugin. Lifecycle hooks match Fastify's request model. No
need to drop down to raw `ws`.

