# Component 32 - WS-7 LangGraph Mock Runtime - Implementation Plan

## Inspect

1. [ ] Read `services/voice-agent/src/voice_agent/services/answer_orchestrator.py`.
2. [ ] Read `services/voice-agent/src/voice_agent/schemas/answer.py`.
3. [ ] Read `services/voice-agent/src/voice_agent/schemas/transcript.py`.
4. [ ] Read `services/voice-agent/src/voice_agent/api/v1/telephony_ws.py`.
5. [ ] Read placeholder files under `services/voice-agent/src/voice_agent/graph/`.
6. [ ] Read placeholder files under `services/voice-agent/src/voice_agent/tools/`.

## Dependency

7. [ ] Add `langgraph` to `services/voice-agent/pyproject.toml`.
8. [ ] Refresh lock/dependency state using the project package manager.

## Graph State

9. [ ] Define a typed graph state model.
10. [ ] Include call/session fields:
    - `call_sid`
    - `stream_sid`
    - `question`
11. [ ] Include member fields:
    - `member_id`
    - `member_verified`
12. [ ] Include orchestration fields:
    - `intent`
    - `tool_name`
    - `tool_args`
    - `tool_result`
    - `answer_text`
    - `grounded`
    - `guard_reason`
    - `tool_trace`
    - `escalate`

## Nodes

13. [ ] Implement `identify_member` node.
14. [ ] Implement `understand_intent` node using deterministic routing.
15. [ ] Implement `call_tool` node.
16. [ ] Implement mock tool functions:
    - `check_coverage`
    - `estimate_cost`
    - `find_provider`
    - `check_formulary`
    - `escalate_to_human`
17. [ ] Implement `compose_answer` node as mock Claude.
18. [ ] Implement `hallucination_guard` node.
19. [ ] Implement `prepare_response` node.

## Graph Assembly

20. [ ] Build the graph in `graph/state_machine.py`.
21. [ ] Use fixed edges:
    - identify member
    - understand intent
    - call tool
    - compose answer
    - hallucination guard
    - prepare response
22. [ ] Compile the graph once and expose a function such as `run_agent_graph()`.
23. [ ] Keep the graph synchronous unless async is clearly needed.

## Orchestrator Compatibility

24. [ ] Update `orchestrate()` to call the LangGraph runtime.
25. [ ] Preserve the current function signature.
26. [ ] Preserve `AnswerFinalEvent` output.
27. [ ] Preserve `tool_trace`.
28. [ ] Avoid changing telephony WebSocket flow unless absolutely required.

## Verification Tests

29. [ ] Update or add unit tests for `orchestrate()`.
30. [ ] Add graph-level tests for:
    - MRI coverage
    - urgent care copay
    - PCP copay
    - lisinopril formulary
    - in-network provider
    - prior authorization
    - unsupported claim question
31. [ ] Assert expected intent.
32. [ ] Assert expected tool.
33. [ ] Assert answer is non-empty.
34. [ ] Assert grounded flag.
35. [ ] Assert escalation path for unsupported question.
36. [ ] Confirm no Anthropic API key is required.

## Non-Goals

37. [ ] Do not implement the LLM eval harness in this component.
38. [ ] Do not call Anthropic.
39. [ ] Do not use real database APIs.
40. [ ] Do not change frontend layout.
41. [ ] Do not change Twilio bridge behavior.

## Run

42. [ ] Run voice-agent unit tests.
43. [ ] Run telephony WebSocket unit tests if available.
44. [ ] Confirm startup still reaches the voice-agent service.

## Commit

45. [ ] Stage only Component 32 voice-agent graph/runtime changes.
46. [ ] Commit with:

```bash
git commit -m "feat(voice-agent): add LangGraph mock runtime"