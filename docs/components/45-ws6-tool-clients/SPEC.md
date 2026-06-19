# Component 45 - WS-6 Typed Tool Clients

> **Branch**: feat/ws456-grounded-agent | **Milestone**: M10 | **Workstream**: WS-6

## Goal

Replace the inline mock tool dispatch in `graph/nodes/call_tool.py` with typed
clients under `tools/*`, one module per tool: `check_coverage`, `estimate_cost`,
`check_formulary`, `find_provider`, `escalate`, `verify_identity`,
`schedule_callback`.

- Add `tools/schemas.py` with a shared `ToolResult{ result, args, ok, facts }`
  dataclass. `result` is the human-readable string the answer composer narrates;
  `facts` are the grounding strings the hallucination guard verifies against; `ok`
  is False only when the tool could not produce a grounded result.
- Each tool exposes `run(question, member_id, mode, base_url) -> ToolResult`.
  - `tool_mode="http"` calls the WS-4 (eligibility) / WS-5 (providers) read APIs
    via `httpx`.
  - `mock` (the default) or any HTTP error returns the verbatim deterministic mock
    string, so every existing graph and scorer test stays green.
- Rewrite `graph/nodes/call_tool.py` to dispatch to the `tools/*` clients (keeping
  the existing `_DISPATCH` keys), thread `member_id` through `AgentState`, and add
  `tool_facts` to `AgentState` for the guard to consume.
- The HTTP path defaults `member_id` to the demo member `CVX-0042-MT` until full
  member threading lands (component 48).

## Out of scope

- The real fact-check hallucination guard (component 46).
- Real STT/TTS streaming adapters (component 47).
