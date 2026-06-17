# Component 12 - Telephony Service Scaffold + ARCHITECTURE.md - Research

> Alternatives considered, decisions made, references.

## Fastify vs Express
- Fastify is ~3x faster (latency + RPS).
- Native plugin system + better TS types out of the box.
- @fastify/websocket plugin handles upgrade lifecycle cleanly.

## TwiML inline vs Twilio Studio
- TwiML in code is version-controlled, testable, reviewable.
- Studio is a UI tool, harder to version, harder to test.

## Why scaffold telephony now (Day 14)
- WS-6 voice-agent in Phase 3 needs the bridge to dock against.
- Cleaner separation: scaffold first, integrate WebSocket bridge in Component 13+ (Phase 3).

## ARCHITECTURE.md placement
- At repo root so it shows up next to README on GitHub.
- Mermaid renders natively on GitHub.

## References
- Fastify: https://fastify.dev/
- TwiML: https://www.twilio.com/docs/voice/twiml
- Mermaid flowcharts: https://mermaid.js.org/syntax/flowchart.html

