# Component 48 - WS-6 Memory and Member Threading - Research

## Why preserve the MOCK-MEMBER-001 default
The graph unit tests assert deterministic behavior including
`test_member_is_always_verified`, which depends on a stable default member when no
id is threaded. If the bare `run_agent_graph` caller suddenly required a real id
(or defaulted to a DB-backed member) those tests would either break or start
hitting the network. So bare callers keep defaulting to the sentinel
`MOCK-MEMBER-001`; only the real entry points (`agent_respond`, telephony) pass a
concrete id. `call_tool` already maps both "no id" and `MOCK-MEMBER-001` to the
seeded demo member `CVX-0042-MT` for any http lookup, so mock determinism and live
correctness coexist.

## Why an in-process session store keyed by sessionId
Conversation memory needs to survive across HTTP turns within a session but does
not need to be durable for the demo. A module-level dict keyed by `sessionId`
(`get_history` / `append_turn` / `clear`, capped at the last N turns) is the
smallest thing that lets two sequential `/agent/respond` calls with the same
session carry context. It has no external dependency, so the offline test suite
exercises real multi-turn behavior without a running Redis.

## Trade-off vs Redis
An in-process dict is single-instance only: memory is lost on restart and is not
shared across replicas. Redis (already a project dependency) is the production
answer for durability and horizontal scale. The store is intentionally kept behind
the three small functions (`get_history` / `append_turn` / `clear`) so a
Redis-backed implementation can drop in behind the same interface without touching
`agent_respond`. That swap is deferred to keep this component dependency-free and
the tests offline.
