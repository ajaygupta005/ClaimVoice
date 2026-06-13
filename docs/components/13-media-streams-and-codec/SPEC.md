# Component 13 - Twilio Media Streams + Audio Codec

> **Branch**: `feat/telephony-media-streams` | **Day(s)**: 15-16 | **Workstream**: WS-7

## Goal

Bidirectional audio bridge between Twilio and our voice agent.

- WebSocket endpoint at `/media-stream` that Twilio Media Streams connects to.
- Parse Twilio's `start`, `media`, `stop` frames.
- mu-law (8 kHz) <-> PCM16 (24 kHz) codec.

## Out of scope

- Forwarding to the voice-agent WS (that's later when the voice-agent service exists).
- Recording (component 14).

