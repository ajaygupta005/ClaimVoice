# Component 45 - WS-6 Typed Tool Clients - Results

## Checklist

- [x] `tools/schemas.py` with `ToolResult{ result, args, ok, facts }`.
- [x] Typed clients for `check_coverage`, `estimate_cost`, `check_formulary`,
      `find_provider`, `escalate`, `verify_identity`, `schedule_callback`.
- [x] `tool_mode="http"` calls WS-4/WS-5 via `httpx`; `mock` (default) or any HTTP
      error returns the verbatim deterministic mock string.
- [x] `graph/nodes/call_tool.py` dispatches to `tools/*`, threads `member_id`
      (default `CVX-0042-MT` on the http path), and writes `tool_facts` to state.
- [x] `tool_facts` added to `AgentState`.
- [x] (fix `5837aba`) `find_provider` specialty extraction broadened to the seeded
      WS-5 specialties.

## Tests

- `services/voice-agent/tests/unit/test_tool_clients.py`:
  - `test_coverage_mock_preserved`, `test_cost_mock_preserved`
  - `test_coverage_http_parses`, `test_cost_http_parses`,
    `test_formulary_http_parses`, `test_provider_http_parses`
    (via monkeypatched `httpx`)
  - `test_find_provider_extracts_seeded_specialties`
  - `test_coverage_http_falls_back_to_mock`
- Full voice-agent suite green: 236 passed (offline, mock mode).

## Commit

```
7fc9c6a feat(ws6): real typed tool clients calling WS-4/WS-5 (mock fallback)
5837aba fix(ws6): broaden find_provider specialty extraction
```

## Notes

- The existing graph/scorer assertions (`$` in cost answers; "deductible" /
  "lisinopril" / "cardiolog" present; per-intent grounded flags) are unchanged
  because mock mode is the default and the fallback returns the same strings.
- `member_id` on the http path is the seeded demo member `CVX-0042-MT`; full
  request-level threading lands in component 48 (M13).
- `find_provider._http` derives the specialty by reusing `_mock(...).args` and
  defaults the geo to Midtown Manhattan until member context is threaded.
