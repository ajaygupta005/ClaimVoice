
## PLAN.md

```md
# Component 35 - WS-7 Claude Answer Composer - Implementation Plan

## Inspect

1. [ ] Read Component 32 LangGraph runtime.
2. [ ] Read Component 33 graph tests.
3. [ ] Read Component 34 eval harness.
4. [ ] Read current `compose_answer` node.
5. [ ] Read current hallucination guard node.
6. [ ] Read voice-agent settings/config pattern.
7. [ ] Read service logging pattern.
8. [ ] Read `services/voice-agent/pyproject.toml`.

## Dependency / Config

9. [ ] Ensure Anthropic SDK is available to the voice-agent service.
10. [ ] Add config:
    - `VOICE_AGENT_ANSWER_MODE`
    - `ANTHROPIC_API_KEY`
    - optional `ANTHROPIC_MODEL`
11. [ ] Default answer mode to `mock`.
12. [ ] Keep local startup working without Anthropic.

## Composer Interface

13. [ ] Create an answer composer abstraction.
14. [ ] Define input:
    - question
    - intent
    - tool name
    - tool args
    - tool result
    - member context
15. [ ] Define output:
    - answer text
    - used facts
    - needs escalation
    - confidence
16. [ ] Implement mock composer using existing deterministic behavior.
17. [ ] Implement Claude composer behind the same interface.

## Claude Prompt

18. [ ] Write system prompt for grounded insurance-answer narration.
19. [ ] Write user/context payload from structured tool result.
20. [ ] Require JSON response.
21. [ ] Include strict rules:
    - use only supplied facts
    - escalate when facts are missing
    - brief phone-friendly language
    - no internal implementation details
22. [ ] Keep prompt small and stable.

## Output Validation

23. [ ] Parse Claude JSON.
24. [ ] Validate required fields.
25. [ ] Reject malformed output.
26. [ ] Reject empty answers.
27. [ ] Fall back safely on parse/validation failure.
28. [ ] Record fallback reason.

## Graph Integration

29. [ ] Replace mock composer node internals with composer interface.
30. [ ] Select composer based on config.
31. [ ] Keep graph edges unchanged.
32. [ ] Keep `AnswerFinalEvent` unchanged.
33. [ ] Ensure hallucination guard always runs after compose.

## Guard / Fallback

34. [ ] If guard passes, return Claude answer.
35. [ ] If guard fails, return safe escalation answer.
36. [ ] If Claude call fails, return deterministic fallback or escalation.
37. [ ] Add internal trace/log reason for fallback.

## Tests

38. [ ] Test mock mode without API key.
39. [ ] Test Claude mode with mocked Anthropic client.
40. [ ] Test valid Claude JSON.
41. [ ] Test invalid Claude JSON fallback.
42. [ ] Test Claude hallucination blocked by guard.
43. [ ] Test missing key handling.
44. [ ] Test output shape remains `AnswerFinalEvent`.
45. [ ] Test graph routing still unchanged.

## Eval

46. [ ] Run Component 34 eval in mock mode.
47. [ ] Add optional documentation for running eval in Claude mode.
48. [ ] Do not make Claude mode the default eval gate yet.

## Verify

49. [ ] Run voice-agent unit tests.
50. [ ] Run LangGraph runtime tests.
51. [ ] Run agent eval harness in mock mode.
52. [ ] Confirm startup works without Anthropic key.
53. [ ] Confirm Claude mode requires/configures key clearly.

## Commit

54. [ ] Stage only Component 35 voice-agent files.
55. [ ] Commit with:

```bash
git commit -m "feat(voice-agent): add Claude answer composer"