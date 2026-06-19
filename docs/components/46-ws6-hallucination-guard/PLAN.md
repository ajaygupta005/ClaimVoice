# Component 46 - WS-6 Hallucination Guard - Plan

1. Implement `services/voice-agent/src/voice_agent/guards/hallucination.py`:
   - `check_in_process(answer, facts) -> (grounded, ungrounded)`: match dollar
     amounts (`\$[\d,]+(?:\.\d{2})?`), tiers (`[Tt]ier \d+`), and coverage
     booleans ("not covered", "prior authorization required") against the facts.
   - `fact_check(answer, facts, mode, base_url) -> (grounded, reason)`: when
     `mode == "http"`, POST `{answer, facts}` to `{base_url}/api/v1/fact_check`
     and read `grounded` / `guardReason`; on any error, fall back to
     `check_in_process`. Reason always contains `grounded` or `ungrounded`.
2. Rewire `services/voice-agent/src/voice_agent/graph/nodes/hallucination_guard.py`
   to call `guards.hallucination.fact_check` over `state["tool_facts"]`, falling
   back to `[state["tool_result"]]` when no facts are present, and to pass through
   escalation (grounded, reason containing `escalat`).
3. Use `settings.tool_mode` for the mode and `settings.eligibility_base_url` (WS-4)
   for the fact_check base URL.
4. Add `services/voice-agent/tests/unit/test_hallucination_guard.py`:
   ungrounded `$` amount, ungrounded `Tier N`, grounded pass-through, and
   escalation still passing.
5. Confirm the graph grounded tests still pass in fallback mode and the full
   voice-agent suite stays green.
