# Component 48 - WS-6 Memory and Member Threading

> **Branch**: feat/ws456-grounded-agent | **Milestone**: M13 | **Workstream**: WS-6

## Goal

Thread the real member id end-to-end and add per-session conversation memory.

- Thread the member id from the HTTP / telephony layers through
  `run_agent_graph` → `AgentState` → tools. Bare graph callers (the unit tests)
  default to `MOCK-MEMBER-001` so graph tests stay deterministic; `agent_respond`
  passes `req.memberId` (defaulting to the demo member `CVX-0042-MT`).
- Add `services/session_memory.py`: an in-process store keyed by `sessionId`
  (`get_history` / `append_turn` / `clear`).
- Add an optional `sessionId` field to `AgentRespondRequest` and a `history`
  field to `AgentState`.
- `agent_respond` loads prior history for the session, threads it into the graph,
  and appends each turn (question + answer) after responding.

## Out of scope

- Redis-backed session store (in-process for now).
- Composer use of the loaded history (history is threaded onto state but the
  composer does not yet consume it).
