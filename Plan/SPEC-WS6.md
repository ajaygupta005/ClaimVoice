# SPEC — WS-6 Voice Agent (LangGraph + Tools)

> Service: `services/voice-agent` (FastAPI + LangGraph, port 8004). Milestones M10–M14.
> Orchestrates the grounded answer: intent → tool calls (WS-4/WS-5) → Claude narration →
> hallucination guard (WS-4 `/fact_check`) → spoken response. STT→Claude→TTS with real
> Deepgram/Cartesia (key-gated, mock fallback).

## Current state (baseline)

- Real 6-node linear LangGraph (`graph/state_machine.py`):
  `identify_member → understand_intent → call_tool → compose_answer → hallucination_guard → prepare_response`.
- Tools are **mock inline** in `graph/nodes/call_tool.py` (the `tools/*.py` files are stubs).
- `guards/hallucination.py` is a stub; active guard `graph/nodes/hallucination_guard.py` is regex
  dollar-matching.
- `answer_composer.py`: real `ClaudeComposer` (gated `VOICE_AGENT_ANSWER_MODE=claude` + key,
  model `claude-sonnet-4-6`) + `MockComposer`.
- `streaming/`: real `MockStreamingSTT`/`MockStreamingTTS` behind `StreamingSTT`/`StreamingTTS`
  interfaces; `deepgram_stt.py`/`cartesia_tts.py`/`vad.py` are stubs (SDKs not installed).
- HTTP `POST /api/v1/agent/respond` (`schemas/agent_respond.py` — fields are **snake_case**:
  `guard_reason`, `tool_trace`, `composer_mode`, `backend_statuses`; default
  `memberId="CVX-0042-MT"`). WS `/api/v1/ws/telephony` bridges Twilio audio.
- Strong tests: `eval/tasks/agent_pipeline_eval.py` (+ `agent_pipeline_cases.json`, importable
  `run_case`/`score_case`/`load_cases`) + 10 unit test files.

## Invariants to preserve (or tests regress)

- The 6-node graph edges and node names; `run_agent_graph`/`orchestrate` signatures.
- `AgentRespondResponse` snake_case field names; `ToolTraceItem{tool,args,result,ok}`; exactly one
  tool-trace entry per turn; `ok == grounded` where asserted.
- Mock-mode determinism: `$` present in cost answers; "deductible"/"lisinopril"/"cardiolog" present;
  grounded flags per `test_agent_graph.py` + `test_agent_pipeline_scorer.py`.
- The `/ws/telephony` event protocol the Node bridge speaks (PCM16 24 kHz base64).

## Config (M1)

`core/config.py`: `eligibility_base_url`, `providers_base_url`,
`tool_mode: Literal["mock","http"]="mock"`, `deepgram_api_key=""`, `cartesia_api_key=""`,
`stt_mode: Literal["mock","deepgram"]="mock"`, `tts_mode: Literal["mock","cartesia","browser","system"]="mock"`.

## Deliverables & milestones

### M10 — real typed tool clients → WS-4/WS-5 (mock fallback)
- Replace stubs `tools/{check_coverage,estimate_cost,check_formulary,find_provider,escalate,
  verify_identity,schedule_callback}.py` with typed fns; add `tools/schemas.py`.
- Each returns `ToolResult{ result:str, args:dict, ok:bool, facts:list[str] }`.
  `tool_mode="http"` → call WS-4/WS-5 via `httpx`; on `mock` or any HTTP error → return the existing
  deterministic mock string (preserves green tests). Default `member_id="CVX-0042-MT"`.
  - `check_coverage(member_id, service)` → `GET /coverage`
  - `estimate_cost(member_id, cost_type, service)` → `POST /cost/estimate` (result_str includes `$` amounts)
  - `check_formulary(member_id, drug)` → `GET /formulary/lookup`
  - `find_provider(member_id, specialty, lat, lng, plan_id)` → `GET /providers/near`
- Rewrite `graph/nodes/call_tool.py` to dispatch to `tools/*` (keep `_TOOL_DISPATCH` keys); thread
  `member_id` through `AgentState`.
- **Done:** mock mode → all existing graph/scorer tests green; `test_tool_clients.py` (mock httpx)
  verifies request shape + parsing; integration `test_tools_live.py` (WS-4/WS-5 + DB up).

### M11 — real hallucination guard via WS-4 `/fact_check` (mock fallback)
- Implement `guards/hallucination.py` (shared fact-check client). Update
  `graph/nodes/hallucination_guard.py`: when http/keyed, POST `{answer, facts}` to `/fact_check`
  and set `grounded`/`guard_reason` from the response; else the in-process check, extended from
  dollar-only to **tiers + coverage booleans**.
- **Done:** `test_hallucination_guard.py` (ungrounded `$` + ungrounded tier); graph grounded tests
  green in fallback; integration vs live `/fact_check`.

### M12 — real Deepgram STT + Cartesia TTS + VAD (key-gated)
- `pyproject.toml`: add `deepgram-sdk`, `cartesia` (optional `webrtcvad`).
- Implement `streaming/deepgram_stt.py` (`DeepgramStreamingSTT(StreamingSTT)`, PCM16 24 kHz),
  `streaming/cartesia_tts.py` (`CartesiaStreamingTTS(StreamingTTS)` → `TtsAudioEvent` chunks, base64
  PCM24k, `isFinal` on last; reuse `_chunk_text`), `streaming/vad.py` (or reuse `stt_adapter` energy VAD).
- Add `build_stt`/`build_tts` factories (select real vs mock by mode+key); wire into
  `telephony_ws._handle_start`/`_handle_stop` (replace hardcoded `MockStreamingSTT`/`MockStreamingTTS`).
- **Done:** keys unset → STT/TTS/`test_telephony_ws.py` pass via mock; key-gated integration (skipped without keys).

### M13 — conversation memory + member threading
- `graph/agent_state.py` (`history`, ensure `member_id`); `state_machine.run_agent_graph(... member_id=)`;
  `graph/nodes/identify_member.py` (use real `member_id`, optionally verify via WS-4
  `/members/{id}/summary`); thread `req.memberId` through `services/answer_orchestrator.py` +
  `api/v1/agent_respond.py`; populate composer `member_context` from the member summary. Optional
  Redis session store keyed by `call_sid` (`redis` already a dep).
- **Done:** `test_agent_respond.py` green; two sequential `/agent/respond` with same `callSid` carry
  context; answer reflects `CVX-0042-MT` ($1,500 deductible).

### M14 — end-to-end evals
- Implement `eval/tasks/e2e_voice_eval.py` (run the graph in `tool_mode=http` against live WS-4/WS-5
  + DB); ensure `agent_pipeline_eval.py` passes in both mock and http modes (golden values now
  DB-sourced via M2).
- **Overall done:** fast gate green (mock); `pytest -m integration` green (DB + services up);
  `inspect eval agent_pipeline_eval.py` + `provider_lookup_eval.py` pass; coverage_qa / hallucination
  / e2e_voice run (model-graded, need keys).

## Cross-workstream touches (this scope)

- WS-2 web: **no change** (existing proxy `app/api/voice-agent/respond/route.ts`; member via `memberId`).
- WS-7 telephony: **no Node change**; only `telephony_ws.py` swaps mock STT/TTS for `build_stt`/`build_tts` (M12).
