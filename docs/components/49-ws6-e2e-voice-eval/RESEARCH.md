# Component 49 - WS-6 End-to-End Voice Eval - Research

## Why a distinct e2e-voice eval
`agent_pipeline_eval` already exercises intent → tool → compose → guard and scores
intent/grounded over the golden cases. The e2e-voice eval adds the missing
dimension: the actual voice loop, transcript → orchestrate → TTS audio. It reuses
the same golden cases and the same intent/grounded checks, then additionally
asserts the loop produces final TTS audio (`audio_chunks >= 1` and a final chunk).
That catches regressions where orchestration is correct but the speak-back path is
broken — which `agent_pipeline_eval` would not notice. Keeping it on the shared
golden set means the two evals stay aligned.

## Why mode-agnostic
The same eval must run in CI (deterministic, offline) and against a live stack.
Driving it off `TOOL_MODE` lets one task serve both: `mock` (default) gives a fast
deterministic gate with no DB/services/keys, and `http` runs the identical turn
against live WS-4/WS-5 with the seeded DB so the golden values are DB-sourced.
Because the tools and guard already fall back to mock on any error (components 45,
46), the eval is safe to run in either mode without code changes — only the env
toggles which backends are exercised.
