# Component 46 - WS-6 Hallucination Guard - Results

## Checklist

- [x] `guards/hallucination.py` implemented: `check_in_process` matcher +
      `fact_check(answer, facts, mode, base_url)` client.
- [x] `tool_mode="http"` POSTs `{answer, facts}` to WS-4 `POST /api/v1/fact_check`
      and reads `grounded` / `guardReason`.
- [x] `mock` (default) or any HTTP error runs the in-process matcher mirroring
      WS-4's mock: dollar amounts, formulary tiers, coverage booleans.
- [x] `graph/nodes/hallucination_guard.py` rewired to use the guard over
      `tool_facts`, falling back to `[tool_result]`.
- [x] Escalation still passes; reason strings preserve
      `grounded` / `ungrounded` / `escalat`.

## Tests

- `services/voice-agent/tests/unit/test_hallucination_guard.py`:
  - `test_grounded_amount`, `test_ungrounded_amount`
  - `test_grounded_tier`, `test_ungrounded_tier`
  - `test_prior_auth_ungrounded_when_facts_silent`
  - `test_fact_check_http`, `test_fact_check_http_falls_back`
    (via monkeypatched `httpx`)
  - `test_node_escalate_passes`
- Graph grounded tests pass in fallback mode; full voice-agent suite green.

## Commit

```
acd1970 feat(ws6): real hallucination guard via WS-4 /fact_check (mock fallback)
```

## Notes

- The in-process matcher and WS-4's mock fact_check share the same logic, so the
  http and fallback paths agree by construction.
- The guard verifies against `tool_facts` (component 45) and falls back to
  `[tool_result]` only when a tool publishes no explicit facts.
- SBC-RAG grounding is out of scope; WS-4 remains the single source of grounding
  truth that production can extend.
