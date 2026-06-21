# Component 67 - WS-7 Production Hardening Roadmap

## Purpose

Turn the current WS-7 voice-agent demo into a reliable, data-backed, observable insurance assistant that can be used from both the browser UI and the Twilio phone path.

This component is a roadmap and execution plan. It does not replace Components 62-66; it ties the remaining WS-7 gaps into a practical sequence.

## Current State

- Browser voice flow can send typed and spoken questions.
- Claude answer composition is available when configured.
- Cartesia voice output can speak responses in the browser.
- Seeded local data now exists for plans, members, benefits, formulary, and providers.
- WS-2 can render agent status, transcript, pipeline, and connection indicators.

The system is  still not production-like because real tool mode, guard behavior, event contracts, phone parity, STT, observability, eval gates, and stuck-session cleanup are not hardened end to end.

## Workstreams

### 1. Real DB-Backed Tool Mode

Goal: make real mode depend on seeded/live data instead of silent frontend or backend demo fallbacks.

Tasks:

- Require seeded DB readiness before enabling real WS-7 tool mode.
- Validate that `members`, `plans`, `plan_benefits`, `formulary_drug`, `providers`, and `in_network` have usable rows.
- Add a startup or health preflight that reports missing tables, empty tables, and missing canonical demo member.
- Ensure tool calls use Eligibility and Providers HTTP APIs as source of truth.
- Return explicit tool errors when data is missing instead of falling back silently.

Acceptance:

- In real mode, a missing member returns a clarification or error state.
- In demo mode, `CVX-0042-MT` is allowed only when explicitly configured.
- The agent response metadata includes `toolMode`, `dataSource`, `memberSource`, and `fallbackReason`.

### 2. Remove Silent Demo-Member Fallback

Goal: stop confusing behavior where the UI or backend quietly answers for the wrong member.

Tasks:

- Audit all uses of `CVX-0042-MT`, `Demo Member`, and `Maya Thompson`.
- Separate `demoMemberId` from real authenticated/current member context.
- Add a visible UI/runtime indicator when the member is demo seeded data.
- In real mode, require a member ID from session, upload, or selected profile.
- Make fallback paths explicit and test-covered.

Acceptance:

- Real mode never silently substitutes `CVX-0042-MT`.
- Demo mode clearly labels the member and data source.
- WS-2 and WS-7 use the same displayed member identity.

### 3. Guard False Positive Reduction

Goal: keep hallucination protection without over-escalating valid insurance answers.

Tasks:

- Compare guard inputs against tool facts for coverage, cost, formulary, provider, and escalation cases.
- Add structured fact fields instead of relying only on answer text.
- Tune guard logic for common insurance wording:
  - covered vs not covered
  - deductible applies
  - copay amount
  - coinsurance amount
  - prior authorization required
  - formulary tier
  - provider availability
- Log guard reason codes.
- Add tests for valid answers currently flagged incorrectly.

Acceptance:

- Correct grounded answers pass.
- Unsupported dollar amounts, coverage claims, or provider claims fail.
- Guard failures include a concrete reason code and the unsupported claim.

### 4. Pipeline Event Contract

Goal: standardize the WS-7 event contract so WS-2 and phone logging do not infer state from text.

Tasks:

- Define one response schema for:
  - `turnId`
  - `input`
  - `inputSource`
  - `intent`
  - `member`
  - `pipelineStages`
  - `toolCalls`
  - `guard`
  - `answer`
  - `voiceRuntime`
  - `fallback`
  - `errors`
- Use stable stage names:
  - `identify`
  - `understand`
  - `retrieve`
  - `guard`
  - `respond`
- Represent errors, timeouts, and escalations as normal stage outcomes.
- Align browser response, Twilio bridge logs, and eval output around the same contract.

Acceptance:

- Every turn returns the same top-level schema.
- UI pipeline renders from structured stages only.
- Phone and browser paths produce comparable traces.

### 5. Twilio Phone Demo Parity

Goal: prove an actual call can complete the same ask-answer-speak loop as the browser demo.

Tasks:

- Verify Twilio inbound media stream reaches telephony service.
- Verify telephony forwards audio frames to voice-agent.
- Verify STT transcript is created for phone audio.
- Verify Claude/tool response returns to telephony.
- Verify TTS audio is converted to Twilio-compatible audio and sent back.
- Add a manual call demo checklist with logs to inspect.

Acceptance:

- A real phone call can ask:
  - "Is lisinopril on my formulary?"
  - "What is my urgent care copay?"
  - "Is an MRI covered?"
- Caller hears the response.
- Logs show one complete turn ID across telephony and voice-agent.

### 6. Production STT

Goal: replace browser-only or demo STT with a reliable production path for browser and phone.

Tasks:

- Decide STT provider for production:
  - Deepgram for streaming browser and Twilio audio, or
  - provider-specific browser STT only for demo.
- Normalize transcripts from browser and phone into the same `input` event.
- Add interim transcript handling only if it improves UX.
- Add silence timeout, max utterance duration, and cancel behavior.
- Surface STT failures in UI and logs.

Acceptance:

- Browser voice and phone voice both produce transcript events.
- Stuck listening state clears automatically.
- STT errors do not block the next turn.

### 7. Cartesia Streaming TTS

Goal: reduce perceived latency and make speech output more reliable.

Tasks:

- Move from full-file TTS response to streaming when feasible.
- Start playback after the first valid audio chunk.
- Keep full-file fallback for simple local development.
- Track TTS timing:
  - request start
  - first byte
  - playback start
  - playback end
- Add watchdog behavior for missing, stalled, or failed audio.

Acceptance:

- Short answers start speaking quickly.
- Long answers do not stop mid-sentence.
- UI unlocks after success, failure, cancel, or timeout.

### 8. Langfuse and Turn Observability

Goal: make every turn debuggable without reading scattered logs.

Tasks:

- Create one trace per agent turn.
- Attach:
  - input transcript
  - member context
  - selected intent
  - tool calls
  - tool results summary
  - Claude prompt metadata
  - guard decision
  - TTS runtime
  - error/fallback reason
- Ensure sensitive values and API keys are never logged.
- Add trace IDs to API responses and UI debug metadata.

Acceptance:

- One turn can be followed from UI to voice-agent to tool calls.
- Failed turns show where they failed.
- Demo readiness can be inspected from trace history.

### 9. Real/Claude Evaluation Gate

Goal: evaluate the actual configured agent, not only deterministic mocks.

Tasks:

- Add eval scenarios that run against Claude mode with real seeded tools.
- Cover:
  - coverage
  - cost
  - formulary
  - provider search
  - denied claim / escalation
  - out-of-scope questions
  - ambiguous member or missing data
- Check required tool use and required facts.
- Fail on ungrounded claims, wrong amounts, wrong tier, wrong prior-auth status, or wrong escalation.
- Save results with timestamps.

Acceptance:

- A single command reports pass/fail for WS-7 demo readiness.
- Failures identify intent, tool, guard, or answer composition as the cause.
- Claude mode can be regression-tested before demos.

### 10. Stuck-Session Cleanup and Turn Watchdogs

Goal: prevent the user from getting stuck in listening, processing, speaking, or streaming states.

Tasks:

- Add state-specific watchdogs:
  - listening timeout
  - STT timeout
  - agent API timeout
  - TTS timeout
  - playback timeout
  - WebSocket close timeout
- Make cancel/stop idempotent.
- Clear pending timers on every terminal state.
- Add visible recovery actions:
  - reset turn
  - retry last question
  - fall back to typed input
- Add tests for stuck states.

Acceptance:

- No user action can leave the UI permanently locked.
- Pressing stop always returns to a usable state.
- Failed turns can be retried cleanly.

### 11. Gemini Normal-Path Removal Decision

Goal: simplify the runtime path if Gemini Live is no longer part of the target demo.

Tasks:

- Decide whether Gemini remains as:
  - experimental provider behind a flag, or
  - removed from normal WS-7 runtime.
- If disabled, remove Gemini from default UI labels and startup preflight.
- Keep provider interfaces generic enough to support future voice runtimes.
- Update docs and env examples.

Acceptance:

- Normal demo path is Claude answer + Cartesia voice.
- Gemini does not appear in UI unless explicitly enabled.
- Runtime status accurately reflects the active provider.

## Suggested Sequence

1. Real data and member identity hardening.
2. Guard false positive reduction.
3. Pipeline event contract.
4. Stuck-session watchdogs.
5. Cartesia streaming or low-latency TTS improvements.
6. Real/Claude eval gate.
7. Langfuse trace per turn.
8. Twilio phone parity.
9. Production STT finalization.
10. Gemini normal-path cleanup.

## Suggested Files

- `services/voice-agent/src/voice_agent/core/config.py`
- `services/voice-agent/src/voice_agent/api/v1/agent.py`
- `services/voice-agent/src/voice_agent/graph/*`
- `services/voice-agent/src/voice_agent/tools/*`
- `services/voice-agent/src/voice_agent/guards/*`
- `services/voice-agent/src/voice_agent/observability/*`
- `services/voice-agent/tests/unit/*`
- `services/voice-agent/tests/integration/*`
- `services/telephony/src/twilio_ws/*`
- `apps/web/src/components/VoiceAssistantUI.tsx`
- `apps/web/src/lib/voice-turn-controller.ts`
- `apps/web/src/lib/tts-client.ts`
- `docs/components/62-ws7-agent-real-tool-mode-hardening/*`
- `docs/components/63-ws7-pipeline-event-contract/*`
- `docs/components/64-ws7-cartesia-tts-stabilization/*`
- `docs/components/65-ws7-evaluation-observability-gate/*`
- `docs/components/66-ws7-twilio-phone-demo-parity/*`

## Validation Commands

```bash
python scripts/start.py
curl http://localhost:8004/health
curl http://localhost:8004/api/v1/runtime/status
curl -X POST http://localhost:8004/api/v1/agent/respond \
  -H "Content-Type: application/json" \
  -d '{"question":"Is lisinopril on my formulary?","memberId":"CVX-0042-MT","source":"typed"}'
```

Add or standardize these later:

```bash
python -m pytest services/voice-agent/tests/unit
python -m pytest services/voice-agent/tests/integration
python services/voice-agent/scripts/run_eval.py --mode claude --tools real
pnpm --filter @claimvoice/web test
pnpm --filter @claimvoice/web typecheck
```

## Risks

- Tightening real mode will expose missing seed and member-context issues.
- Guard tuning can accidentally allow unsupported claims if tests are too weak.
- Streaming TTS and Twilio return audio can introduce timing bugs.
- Langfuse traces must avoid leaking PHI, secrets, and raw API keys.
- Removing Gemini from the normal path can break code that still assumes it exists.

## Done When

- WS-7 answers only from real tool facts in real mode.
- Demo fallback is explicit and visible.
- Claude answers are evaluated against seeded data.
- Guard false positives are reduced without losing safety.
- UI and phone share a stable pipeline contract.
- Cartesia speech is reliable and low-latency.
- Stuck turns recover automatically.
- Each turn has one trace ID and useful debugging metadata.
- Twilio phone demo works end to end.
- Gemini is either removed from normal path or clearly marked experimental.
