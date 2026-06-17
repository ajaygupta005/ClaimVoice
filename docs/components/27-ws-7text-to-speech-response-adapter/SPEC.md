# Component 27 - WS-7 Text-to-Speech Response Adapter

> **Workstream**: WS-7 / WS-6 integration surface  
> **Depends on**: Component 26 - Grounded Answer Orchestrator

## Goal

Convert grounded answer text into speech-ready audio events.

Component 26 produces an `answer.final` event. This component adds the text-to-speech layer that prepares the answer to be spoken back to the caller.

The first version can use a deterministic mock TTS adapter. The important part is the interface, event shape, and integration point.

## What This Component Does

Add a TTS adapter inside `voice-agent`.

The adapter should:

- accept final answer text
- split long answers into speakable chunks
- generate mock PCM16 24 kHz audio chunks
- emit audio response events
- include call and stream identifiers
- handle empty or unsafe text safely

This prepares the system for later Cartesia, ElevenLabs, OpenAI TTS, or browser/Twilio audio playback integration.

## Input Event

```json
{
  "type": "answer.final",
  "callSid": "CA...",
  "streamSid": "MZ...",
  "answer": "Yes. An in-network MRI is covered, but prior authorization is required.",
  "confidence": 0.88,
  "toolTrace": []
}