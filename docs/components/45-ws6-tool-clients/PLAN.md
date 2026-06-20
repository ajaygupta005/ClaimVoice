# Component 45 - WS-6 Typed Tool Clients - Plan

1. Add `services/voice-agent/src/voice_agent/tools/schemas.py` with the
   `ToolResult{ result, args, ok, facts }` dataclass.
2. Implement the typed clients under
   `services/voice-agent/src/voice_agent/tools/`, each with a `_mock` helper, an
   `_http` helper, and a `run(question, member_id, mode, base_url)` entry point:
   - `check_coverage.py` → WS-4 `GET /api/v1/coverage`
   - `estimate_cost.py` → WS-4 `POST /api/v1/cost/estimate` (result includes `$`)
   - `check_formulary.py` → WS-4 `GET /api/v1/formulary/lookup`
   - `find_provider.py` → WS-5 `GET /api/v1/providers/near`
   - `escalate.py`, `verify_identity.py`, `schedule_callback.py` (deterministic).
3. Each `run` calls `_http` only when `mode == "http"`, wrapped in try/except that
   falls back to `_mock` on any error.
4. Rewrite `services/voice-agent/src/voice_agent/graph/nodes/call_tool.py` to
   dispatch via `_DISPATCH` to the `tools/*` clients, pick the base URL per tool
   (`providers_base_url` for `find_provider`, else `eligibility_base_url`), thread
   `member_id` (default to `CVX-0042-MT` for the http path), and write
   `tool_args` / `tool_result` / `tool_facts` back onto the state.
5. Add `tool_facts: list[str]` to
   `services/voice-agent/src/voice_agent/graph/agent_state.py`.
6. Add `services/voice-agent/tests/unit/test_tool_clients.py` covering mock-string
   preservation, http request shape + parsing (via monkeypatched `httpx`), and
   fallback-to-mock on HTTP error.
7. (Fix `5837aba`) Broaden the `find_provider` specialty regex to the seeded WS-5
   specialties; add `test_find_provider_extracts_seeded_specialties`.
8. Run the voice-agent unit suite and confirm it stays green.
