
## PLAN.md

```md
# Component 34 - WS-7 Agent Evaluation Harness - Implementation Plan

## Inspect

1. [ ] Read Component 32 LangGraph runtime.
2. [ ] Read Component 33 runtime tests.
3. [ ] Read `eval/README.md`.
4. [ ] Read `eval/tasks/coverage_qa_eval.py`.
5. [ ] Read `eval/tasks/hallucination_eval.py`.
6. [ ] Read `eval/datasets/golden_qa.json`.
7. [ ] Read `eval/datasets/hallucination_golden.json`.
8. [ ] Read `services/voice-agent/src/voice_agent/services/answer_orchestrator.py`.

## Dataset

9. [ ] Add `eval/datasets/agent_pipeline_cases.json`.
10. [ ] Include case id, question, expected intent, expected tool, required phrases, forbidden phrases, expected grounded flag, and escalation flag.
11. [ ] Cover:
    - MRI coverage
    - MRI prior authorization
    - urgent care copay
    - PCP copay
    - lisinopril formulary
    - provider search
    - claim-denial escalation
    - unclear question
    - hallucination trap
12. [ ] Reuse wording from existing golden datasets where practical.

## Pipeline Adapter

13. [ ] Add an eval adapter that imports the voice-agent orchestrator.
14. [ ] Convert each eval question into a `FinalTranscriptEvent`.
15. [ ] Call `orchestrate()`.
16. [ ] Return a normalized result:
    - answer text
    - intent
    - tool trace
    - grounded flag
    - escalation flag if available

## Deterministic Scorer

17. [ ] Implement deterministic checks.
18. [ ] Check expected intent.
19. [ ] Check expected tool.
20. [ ] Check required phrases.
21. [ ] Check forbidden phrases.
22. [ ] Check grounded flag.
23. [ ] Check escalation behavior.
24. [ ] Produce readable failure reasons.

## Inspect AI Task

25. [ ] Add `eval/tasks/agent_pipeline_eval.py`.
26. [ ] Load `agent_pipeline_cases.json`.
27. [ ] Run each case through the pipeline adapter.
28. [ ] Apply deterministic scorer.
29. [ ] Print or attach useful debug metadata:
    - case id
    - question
    - expected/actual intent
    - expected/actual tool
    - answer
    - failure reason

## Optional LLM Judge

30. [ ] Add optional model judge only if configured.
31. [ ] Judge answer correctness and groundedness.
32. [ ] Keep deterministic scorer as the required local gate.
33. [ ] Document that LLM judge is advisory for this component.

## Docs

34. [ ] Update `eval/README.md`.
35. [ ] Add run command for `agent_pipeline_eval`.
36. [ ] Explain deterministic vs optional LLM scoring.
37. [ ] State that this evaluates the agent pipeline before real Claude runtime integration.

## Verify

38. [ ] Run voice-agent unit tests.
39. [ ] Run Component 33 graph tests.
40. [ ] Run dataset shape tests.
41. [ ] Run `agent_pipeline_eval`.
42. [ ] Run existing `coverage_qa_eval` if configured.
43. [ ] Run existing `hallucination_eval` if configured.

## Commit

44. [ ] Stage only eval harness files.
45. [ ] Commit with:

```bash
git commit -m "test(eval): add LangGraph agent pipeline eval"