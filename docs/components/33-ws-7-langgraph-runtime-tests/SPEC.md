# Component 33 - WS-7 LangGraph Runtime Tests

> **Workstream**: WS-7 voice agent reliability  
> **Depends on**: Component 32 - WS-7 LangGraph Mock Runtime

## Goal

Add strong tests for the LangGraph mock runtime before adding broad evals or real Claude calls.

This component proves that the graph workflow behaves correctly for known member questions.

It should test:

- graph node order
- intent routing
- tool selection
- tool trace output
- grounded answer behavior
- escalation behavior
- compatibility with the existing telephony WebSocket response shape

This is not the full LLM eval harness yet.

## Scope

Test the LangGraph runtime added in Component 32.

Target behavior:

```text
FinalTranscriptEvent
  -> LangGraph runtime
  -> AnswerFinalEvent