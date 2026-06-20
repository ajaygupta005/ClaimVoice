# Component 48 - WS-6 Memory and Member Threading - Results

## Checklist

- [x] Member id threaded from HTTP/telephony through `run_agent_graph` →
      `AgentState` → tools; bare callers default to `MOCK-MEMBER-001`.
- [x] `agent_respond` passes `req.memberId` (default `CVX-0042-MT`).
- [x] `services/session_memory.py` in-process store keyed by `sessionId`
      (`get_history` / `append_turn` / `clear`).
- [x] Optional `sessionId` added to `AgentRespondRequest`; `history` added to
      `AgentState`.
- [x] `agent_respond` loads prior history and appends each turn.

## Tests

- `services/voice-agent/tests/unit/test_memory.py`:
  - `test_session_memory_store`
  - `test_member_threading_default_is_mock`
  - `test_member_threading_explicit`
  - `test_history_threaded_into_state`
  - `test_agent_respond_memory_accumulates_across_turns`
- `test_member_is_always_verified` and the full voice-agent suite stay green.

## Commit

```
737b697 feat(ws6): conversation memory + member threading
```

## Notes

- The `MOCK-MEMBER-001` default keeps the graph unit tests deterministic; the http
  tool path maps both "no id" and `MOCK-MEMBER-001` to the seeded demo member
  `CVX-0042-MT` (see component 45).
- The session store is in-process (module-level dict, last N turns) — single
  instance only. A Redis-backed store can replace it behind the same three
  functions; that swap is out of scope here.
- History is threaded onto `AgentState` but the composer does not yet consume it.
