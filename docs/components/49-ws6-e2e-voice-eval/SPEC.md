# Component 49 - WS-6 End-to-End Voice Eval

> **Branch**: feat/ws456-grounded-agent | **Milestone**: M14 | **Workstream**: WS-6

## Goal

Implement `eval/tasks/e2e_voice_eval.py` (previously a stub) — a full voice turn
over the agent-pipeline golden cases.

- Per case: transcript (final text) → `orchestrate` (LangGraph) → answer → TTS
  audio. Score on intent and grounded matching the golden case, plus that the
  voice loop actually produces final TTS audio (at least one PCM24k chunk and a
  final chunk).
- Respect `TOOL_MODE`: `mock` (default) for CI — fully deterministic, no
  DB/services/keys; `http` for a live run against WS-4/WS-5 + the seeded DB.
- Expose importable `run_voice_turn` / `score_voice_turn` / `load_cases`, plus an
  Inspect AI task for `inspect eval`.

## Out of scope

- Model-graded judging (needs `ANTHROPIC_API_KEY`); this eval checks
  intent / grounded / TTS audio deterministically, not answer quality via a judge.
