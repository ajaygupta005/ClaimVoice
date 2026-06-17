
# Component 26 - WS-7 Grounded Answer Orchestrator

> **Workstream**: WS-7 / WS-6 integration surface  
> **Depends on**: Component 25 - Streaming STT Adapter

## Goal

Turn final transcript text into a grounded insurance answer.

Component 25 produces transcript events from telephony audio. This component adds the answer orchestration layer: take the final transcript, identify the member context, call the correct insurance tools, and return a structured answer with a trace.

## What This Component Does

Add a lightweight answer orchestrator inside `voice-agent`.

The orchestrator should:

- accept a final transcript
- attach call and member context
- classify the user intent
- call mocked or existing tools
- produce a safe answer
- produce a tool-call trace
- return a response event that later TTS can speak

For now, this can use deterministic routing and mocked tool results. The important part is the orchestration interface and grounded response shape.

## Input Event

```json
{
  "type": "transcript.final",
  "callSid": "CA...",
  "streamSid": "MZ...",
  "text": "Is an MRI covered under my plan?",
  "confidence": 0.91
}