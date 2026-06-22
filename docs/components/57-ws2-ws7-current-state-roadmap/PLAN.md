# Component 57 - WS-2 / WS-7 Current State and Roadmap Plan

## Goal

Create a clear implementation roadmap for WS-2 and WS-7 based on the current codebase state.

This is a documentation-only component. It should guide future work without changing runtime behavior.

## Current State Decision

The next product direction should be:

- Keep Claude as the answer composer.
- Keep LangGraph as the deterministic agent pipeline.
- Keep Eligibility and Providers as the first real tool backends.
- Keep Document AI as the real card-OCR backend once model runners are available.
- Keep Cartesia Skylar/Amber-style voices as the TTS path.
- Treat Gemini Live as experimental and not part of the primary demo path.
- Treat browser STT as acceptable for local demo, but not as the final deployed STT architecture.

## Proposed Next Components

### Component 58 - WS-2 Shared API Client and Service Status

Scope:

- Add a typed web API client layer for Eligibility, Providers, Document AI, and Voice Agent.
- Centralize base URLs and request error handling.
- Expose service status to UI components.
- Add explicit mode labels: real, demo, unavailable.

Why first:

- WS-2 currently has multiple UI pages that can use real APIs, but they need one consistent client and error contract before wiring individual screens.

Acceptance:

- Web code has one documented API client layer.
- UI can distinguish real data from demo fallback.
- Typecheck passes.

### Component 59 - WS-2 Card Upload to Document AI

Scope:

- Wire Card Upload to `POST /api/v1/card_ocr`.
- Wire payor classification to `POST /api/v1/payor_classify`.
- Display extracted fields, confidence, low-confidence warnings, and model version.
- Fall back visibly when Document AI model artifacts are unavailable.

Why:

- This turns the card upload page from a mock flow into a real data capture workflow.

Acceptance:

- Uploading a card image calls Document AI.
- OCR output appears in the existing review UI.
- 503/model-unavailable states are handled clearly.
- Mock fallback is labeled as demo data.

### Component 60 - WS-2 Plan Details from Eligibility APIs

Scope:

- Replace mock plan details with `GET /api/v1/members/{member_id}/summary`.
- Load benefits from `GET /api/v1/plans/{plan_id}/benefits`.
- Show loading, error, empty, and retry states.
- Preserve demo member fallback only when explicit demo mode is enabled.

Why:

- Plan details are the main source of truth for voice and dashboard user trust.

Acceptance:

- Plan page renders real member and plan data when services are available.
- Mock data is not silently mixed with real data.
- Errors are visible and recoverable.

### Component 61 - WS-2 Provider Search from Providers APIs

Scope:

- Replace mock provider filtering with Providers API calls.
- Support specialty, location/state, distance, accepting-new-patients, and plan filters as available.
- Show provider detail cards from real API data.
- Keep map as optional or placeholder until geospatial data is reliable.

Why:

- Provider search is one of the highest-value user flows and is already supported by backend APIs.

Acceptance:

- Provider page can fetch real provider results.
- Empty and error states are clear.
- API results match voice-agent provider tool behavior.

### Component 62 - WS-7 Agent Real Tool Mode Hardening

Scope:

- Make HTTP tool mode the default real local-demo path when Eligibility and Providers are healthy.
- Require member context in real mode.
- Allow the demo member fallback only under explicit demo configuration.
- Normalize tool errors into safe agent responses.

Why:

- The voice assistant should not appear real while silently answering from fixed demo data.

Acceptance:

- Real mode uses service APIs for coverage, cost, formulary, and provider intents.
- Demo fallback is explicit and observable.
- Tool failures do not produce hallucinated answers.

### Component 63 - WS-7 Pipeline Event Contract for WS-2

Scope:

- Define a stable response/pipeline event schema for WS-2.
- Include stage, status, detail, tool calls, guard result, answer source, and voice runtime.
- Ensure WS-2 can render the pipeline without guessing from ad hoc fields.

Why:

- The UI currently displays pipeline state, but the contract should be made durable before more real services are wired.

Acceptance:

- Agent response schema is documented and tested.
- WS-2 can render pipeline and backend badges from backend-provided metadata.
- No hidden UI-only inference is needed for core agent state.

### Component 64 - WS-7 Cartesia TTS Stabilization

Scope:

- Keep Cartesia as the main TTS provider.
- Remove Gemini Live from the primary voice path.
- Add timeout, cancellation, retry, and stuck-state handling.
- Support faster perceived response by showing text answer immediately and playing audio when ready.
- Add Cartesia health diagnostics to startup and runtime status.

Why:

- The current best working voice path is Claude answer plus Cartesia speech. It should be hardened instead of mixing runtimes.

Acceptance:

- Text answer is shown as soon as available.
- Audio playback starts reliably or fails visibly.
- User can ask the next question after success, timeout, or cancellation.

### Component 65 - WS-7 Evaluation and Observability Gate

Scope:

- Promote scenario evals into a repeatable gate.
- Include coverage, cost, formulary, provider, escalation, denial, and out-of-scope questions.
- Track hallucination guard outcomes.
- Emit Langfuse-compatible traces for each turn when configured.

Why:

- The agent needs evidence that it behaves correctly, not just a polished UI.

Acceptance:

- A single command runs the agent eval suite.
- Results show pass/fail and reasons.
- Guard false positives and false negatives are visible.

### Component 66 - WS-7 Twilio Phone Demo Parity

Scope:

- Validate Twilio Media Streams input path against the same agent graph used by browser voice.
- Validate Cartesia or telephony-compatible audio return path.
- Log call lifecycle, bytes in/out, transcript, answer, and guard status.
- Add a safe demo script for phone-call testing.

Why:

- The project is a telephone AI agent. Browser voice is the proving ground, but Twilio parity is required for the actual phone demo.

Acceptance:

- A phone call can reach the same agent behavior as the browser voice page.
- Audio is returned to the caller.
- Failures are visible in logs and do not leave a stuck call state.

## WS-2 Priority Order

1. Shared API client and service status.
2. Plan details from Eligibility APIs.
3. Provider search from Providers APIs.
4. Card upload to Document AI.
5. Call history from real telephony/session data.
6. Playwright dashboard regression tests.
7. Responsive polish and final demo copy.

Reasoning:

- Plan and provider APIs appear more immediately usable than Document AI because Document AI depends on model artifacts being loaded.
- Voice demo already works well enough to be refined in parallel through WS-7.

## WS-7 Priority Order

1. Lock product path to Claude + LangGraph + tools + Cartesia.
2. Remove or isolate Gemini from the main path.
3. Harden real tool mode and member context.
4. Standardize pipeline events.
5. Stabilize Cartesia TTS and stuck-turn recovery.
6. Add eval and observability gate.
7. Prove Twilio parity.

Reasoning:

- Runtime confusion has caused the most instability. The next step should simplify, not add another voice path.
- A deterministic pipeline with a premium voice provider is more demo-ready than a partially integrated realtime model stack.

## Testing Strategy

For WS-2:

- `pnpm --filter web typecheck`
- `pnpm --filter web build`
- Playwright coverage for:
  - card upload success and model-unavailable fallback
  - plan details real API success and error
  - provider search results and empty state
  - voice typed input
  - voice spoken input where browser STT is available

For WS-7:

- Voice-agent unit tests.
- Agent integration tests with mock tools.
- Agent integration tests with HTTP tools.
- Cartesia TTS success, timeout, and error tests with network calls mocked.
- Hallucination guard positive and negative tests.
- Twilio bridge tests for media receive and audio return.

For startup:

- Verify `scripts/start.py` reports:
  - Claude answer mode
  - Cartesia key/provider availability
  - HTTP tool mode
  - Document AI model availability when known
  - Gemini disabled or experimental, if still present

## Risks and Mitigations

### Risk: UI silently mixes mock and real data

Mitigation:

- Add explicit mode labels and shared API client responses that include data source.

### Risk: Document AI models are unavailable locally

Mitigation:

- Treat Document AI unavailable as a first-class UI state.
- Keep mock extraction only under demo mode.

### Risk: Voice runtime becomes confusing again

Mitigation:

- Choose one product voice path: Cartesia.
- Hide Gemini behind an experimental flag or remove it from default UI.

### Risk: Claude answers without enough grounding

Mitigation:

- Keep LangGraph tool-first.
- Require guard checks before final answer.
- Surface escalation when facts are missing.

### Risk: Browser STT differs from deployed behavior

Mitigation:

- Use browser STT only for local demo.
- Plan production STT separately before deployment.

### Risk: Twilio behavior diverges from browser demo

Mitigation:

- Reuse the same voice-agent graph.
- Add parity tests and call lifecycle logs.

## Definition of Done for This Component

- `SPEC.md` documents current state, current capabilities, and pending work.
- `PLAN.md` defines the next WS-2 and WS-7 implementation sequence.
- No runtime files are changed.
- No secrets or environment values are modified.
- The plan is actionable as future components.

