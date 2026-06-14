# Component 26 - WS-7 Grounded Answer Orchestrator - Implementation Plan

> Convert final transcript text into a grounded answer event.

## Inspect

1. [ ] Read `services/voice-agent/src/voice_agent/tools/`.
2. [ ] Read `services/voice-agent/src/voice_agent/graph/`.
3. [ ] Read `services/voice-agent/src/voice_agent/guards/hallucination.py`.
4. [ ] Read `eval/datasets/golden_qa.json`.
5. [ ] Read Component 25 transcript event schema.

## Design

6. [ ] Define an answer request schema.
7. [ ] Define an answer response schema.
8. [ ] Define a tool trace schema.
9. [ ] Add a deterministic intent router.
10. [ ] Use mock tool outputs first.
11. [ ] Keep the interface compatible with later Claude/LangGraph integration.

## Implementation

12. [ ] Create `services/voice-agent/src/voice_agent/schemas/answer.py`.
13. [ ] Create `services/voice-agent/src/voice_agent/services/answer_orchestrator.py`.
14. [ ] Implement intent routing for coverage, cost, provider, formulary, and escalation.
15. [ ] Add mocked tool trace generation.
16. [ ] Update the telephony WebSocket flow to call the orchestrator after `transcript.final`.
17. [ ] Send `answer.final` event back over the WebSocket.

## Tests

18. [ ] Add `services/voice-agent/tests/unit/test_answer_orchestrator.py`.
19. [ ] Test MRI coverage question.
20. [ ] Test copay/cost question.
21. [ ] Test provider search question.
22. [ ] Test formulary question.
23. [ ] Test unknown question returns escalation-safe response.
24. [ ] Test answer response always includes a tool trace.

## Verify

25. [ ] Run voice-agent tests.
26. [ ] Send fake transcript final event through the WebSocket flow.
27. [ ] Confirm `answer.final` is returned.
28. [ ] Confirm logs include intent, tool trace, and answer status.
29. [ ] Confirm no answer is returned without transcript text.

## Commit

30. [ ] Stage only Component 26 docs, schemas, orchestrator code, and tests.
31. [ ] Commit with:

```bash
git commit -m "feat(voice-agent): add grounded answer orchestrator"