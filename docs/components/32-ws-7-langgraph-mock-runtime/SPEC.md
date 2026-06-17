# Component 32 - WS-7 LangGraph Mock Runtime

> **Workstream**: WS-7 voice agent orchestration  
> **Depends on**: Component 31 - WS-2/WS-7 Mocked Agent Pipeline

## Goal

Introduce LangGraph as the voice-agent orchestration runtime, but keep all behavior mocked and deterministic.

This component should convert the current one-function mock answer orchestrator into a fixed graph workflow.

The graph should make the agent structure explicit:

1. identify member
2. understand intent
3. call the correct mock tool
4. compose a grounded answer
5. run hallucination guard
6. prepare the response for TTS

No real Claude, real database, real STT, real TTS, or real Twilio changes should be added in this component.

## Why This Component Exists

The project needs to show a real agent architecture, not only a UI simulation.

LangGraph should be used as the workflow harness:

- state moves through named nodes
- tool calls are explicit
- outputs are inspectable
- later real Claude/tool nodes can replace mock nodes
- tests can verify routing and state transitions

The LLM should not secretly control everything. The application should own the graph, tools, state, validation, and final response contract.

## Scope

Update the voice-agent service.

Primary target:

```text
services/voice-agent/src/voice_agent/graph/