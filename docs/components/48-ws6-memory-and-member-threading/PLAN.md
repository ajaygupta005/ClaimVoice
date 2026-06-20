# Component 48 - WS-6 Memory and Member Threading - Plan

1. Add `history: list[dict]` to
   `services/voice-agent/src/voice_agent/graph/agent_state.py` (alongside the
   existing `member_id`).
2. Thread the member id through the graph:
   `services/voice-agent/src/voice_agent/graph/state_machine.py`
   `run_agent_graph(..., member_id=...)` seeds `AgentState["member_id"]`,
   defaulting to `MOCK-MEMBER-001` for bare callers; `identify_member` /
   `call_tool` consume it.
3. Add `services/voice-agent/src/voice_agent/services/session_memory.py` with an
   in-process dict store: `get_history(session_id)`, `append_turn(session_id,
   question, answer)` (capped at the last N turns), and `clear(session_id)`.
4. Add an optional `sessionId: str | None` to `AgentRespondRequest` in
   `services/voice-agent/src/voice_agent/schemas/agent_respond.py`.
5. Update `services/voice-agent/src/voice_agent/api/v1/agent_respond.py` (and the
   orchestrator) to pass `req.memberId` into the graph, load prior history for
   `req.sessionId`, thread it onto `AgentState["history"]`, and `append_turn`
   after producing the answer.
6. Add `services/voice-agent/tests/unit/test_memory.py`: store round-trip, member
   threading default vs explicit, history threaded into state, and memory
   accumulating across two sequential endpoint calls.
7. Confirm the full voice-agent suite (including
   `test_member_is_always_verified`) stays green.
