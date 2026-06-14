
## PLAN.md

```md
# Component 33 - WS-7 LangGraph Runtime Tests - Implementation Plan

## Inspect

1. [ ] Read Component 32 implementation.
2. [ ] Read `services/voice-agent/src/voice_agent/graph/state_machine.py`.
3. [ ] Read graph node files.
4. [ ] Read `services/voice-agent/src/voice_agent/services/answer_orchestrator.py`.
5. [ ] Read `services/voice-agent/tests/unit/test_answer_orchestrator.py`.
6. [ ] Read `services/voice-agent/tests/unit/test_telephony_ws.py`.

## Test Fixtures

7. [ ] Add helper to create `FinalTranscriptEvent`.
8. [ ] Add reusable sample call SID and stream SID.
9. [ ] Add scenario table with:
   - question
   - expected intent
   - expected tool
   - expected answer fragments
   - expected grounded/escalation state

## Graph Runtime Tests

10. [ ] Add tests for MRI coverage.
11. [ ] Add tests for urgent care copay.
12. [ ] Add tests for primary care copay.
13. [ ] Add tests for lisinopril formulary lookup.
14. [ ] Add tests for provider search.
15. [ ] Add tests for prior authorization.
16. [ ] Add tests for claim-denial escalation.
17. [ ] Add tests for empty/unclear question.

## Assertions

18. [ ] Assert `orchestrate()` returns `AnswerFinalEvent`.
19. [ ] Assert final intent matches expected.
20. [ ] Assert expected tool appears in `tool_trace`.
21. [ ] Assert answer text is non-empty.
22. [ ] Assert required answer fragments appear.
23. [ ] Assert unsupported facts do not appear.
24. [ ] Assert grounded flag matches expected behavior.
25. [ ] Assert escalation questions do not invent claim facts.

## Graph Trace

26. [ ] If available, assert graph visited expected nodes.
27. [ ] If not available, add test-only/internal trace support.
28. [ ] Verify expected fixed flow:
   - identify member
   - understand intent
   - call tool
   - compose answer
   - hallucination guard
   - prepare response

## WebSocket Compatibility

29. [ ] Run existing telephony WebSocket tests.
30. [ ] Confirm the WebSocket still emits:
   - transcript final
   - answer final
   - TTS audio events
31. [ ] Do not change the WebSocket protocol.

## Verify

32. [ ] Run voice-agent unit tests.
33. [ ] Confirm no test requires Anthropic.
34. [ ] Confirm no test requires database services.
35. [ ] Confirm all previous Component 25-28 tests still pass where applicable.

## Commit

36. [ ] Stage only Component 33 test/support files.
37. [ ] Commit with:

```bash
git commit -m "test(voice-agent): cover LangGraph mock runtime"