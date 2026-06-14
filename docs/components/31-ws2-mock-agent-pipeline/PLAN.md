# Component 31 - WS-2/WS-7 Mocked Agent Pipeline - Implementation Plan

## Inspect

1. [ ] Read `apps/web/src/components/VoiceAssistantUI.tsx`.
2. [ ] Read `apps/web/src/lib/mock-data.ts`.
3. [ ] Read `docs/PROJECT_DEEPDIVE.md`.
4. [ ] Read `eval/datasets/golden_qa.json`.
5. [ ] Confirm Component 30 layout is implemented.

## Mock Pipeline Model

6. [ ] Define a mocked agent pipeline result type.
7. [ ] Include:
   - call/session metadata
   - STT result
   - selected intent
   - tool call results
   - mock Claude answer
   - hallucination guard result
   - TTS result
   - transcript turns
   - backend statuses
   - pipeline steps
8. [ ] Keep this model frontend-local for now.

## Mock Integrations

9. [ ] Add mock Twilio session data:
   - `callSid`
   - `streamSid`
   - call status
   - media stream status
10. [ ] Add mock STT adapter:
   - input: simulated voice or typed text
   - output: transcript text + confidence
11. [ ] Add mock insurance tool adapter:
   - `verify_identity`
   - `check_coverage`
   - `estimate_cost`
   - `find_provider`
   - `check_formulary`
   - `escalate_to_human`
12. [ ] Add mock Claude adapter:
   - input: tool result
   - output: natural language answer
13. [ ] Add mock hallucination guard:
   - input: answer + tool facts
   - output: pass/fail + reason
14. [ ] Add mock TTS adapter:
   - input: final answer
   - output: audio prepared status

## Routing Logic

15. [ ] Route MRI / covered questions to `check_coverage`.
16. [ ] Route copay / cost / deductible questions to `estimate_cost`.
17. [ ] Route lisinopril / drug / formulary questions to `check_formulary`.
18. [ ] Route cardiologist / provider / near me questions to `find_provider`.
19. [ ] Route prior auth / authorization questions to `check_coverage`.
20. [ ] Route claim denied / appeal / unsupported questions to `escalate_to_human`.
21. [ ] Unknown questions should safely escalate.

## Mock Scenario Data

22. [ ] Add scenarios for:
   - MRI coverage
   - urgent care copay
   - lisinopril formulary
   - cardiologist search
   - MRI prior authorization
   - claim denial escalation
23. [ ] Base wording on `PROJECT_DEEPDIVE.md` and `golden_qa.json`.
24. [ ] Keep answer text short enough for demo.

## UI Wiring

25. [ ] Keep Component 30 layout unchanged.
26. [ ] On typed input, run the mocked pipeline.
27. [ ] On push-to-talk, run the mocked pipeline using a predefined voice question.
28. [ ] Update latest answer from mock Claude output.
29. [ ] Update transcript from pipeline result.
30. [ ] Update horizontal pipeline steps from pipeline result.
31. [ ] Update backend LEDs/status panel from pipeline result.
32. [ ] Show processing states briefly so the pipeline feels active.

## Safety Behavior

33. [ ] For normal supported questions, hallucination guard should pass.
34. [ ] For claim denial / unsupported questions, route to escalation.
35. [ ] Do not invent claim-specific details.
36. [ ] Make clear that unsupported cases need a human specialist.

## Tests

37. [ ] Add unit tests for mock routing.
38. [ ] Test MRI coverage routes to `check_coverage`.
39. [ ] Test urgent care copay routes to `estimate_cost`.
40. [ ] Test lisinopril routes to `check_formulary`.
41. [ ] Test cardiologist routes to `find_provider`.
42. [ ] Test claim denial routes to `escalate_to_human`.
43. [ ] Test mock Claude answer is based on tool facts.
44. [ ] Test hallucination guard passes supported scenarios.
45. [ ] Test unsupported scenario escalates.

## Verify

46. [ ] Run web typecheck.
47. [ ] Open `/dashboard/voice`.
48. [ ] Try each demo question.
49. [ ] Confirm transcript updates.
50. [ ] Confirm latest answer updates.
51. [ ] Confirm horizontal pipeline updates.
52. [ ] Confirm backend statuses update.
53. [ ] Confirm no real backend is required.

## Commit

54. [ ] Stage only frontend mock pipeline, tests, and Component 31 docs.
55. [ ] Commit with:

```bash
git commit -m "feat(web): add mocked voice agent pipeline"