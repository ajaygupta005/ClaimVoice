# Component 68 - WS-6 Live Voice: Claude Grounding & Robustness - Plan

1. `graph/nodes/answer_composer.py`: add `tool_facts` to `ComposerInput`; the ClaudeComposer
   includes it in the user payload; the system prompt says "use tool_result + tool_facts".
   `graph/nodes/compose_answer.py`: pass `tool_facts=state['tool_facts']`. Leave the
   MockComposer untouched -- its hard-coded figures match the demo plan.
2. `tools/estimate_cost.py`: match the `\bdeduc` stem (deductible / deduction) in both
   `_cost_type` and `_mock`, so STT mis-transcriptions still resolve `costType=deductible`.
3. `tools/check_coverage.py`: raise the httpx timeout 5s -> 20s (the SBC-enriched
   `/coverage` legitimately takes a few seconds).
4. Verify: run the agent graph in `TOOL_MODE=http` + `VOICE_AGENT_ANSWER_MODE=claude` for
   the three intents; run the deterministic eval gate.
