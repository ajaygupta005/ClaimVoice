# Component 57 - WS-2 / WS-7 Current State and Roadmap

## Purpose

This component is a docs-only checkpoint for WS-2 and WS-7 after the recent voice-agent, Cartesia, Gemini-runtime, real-data API, and UI demo work.

It answers three questions:

1. What can WS-2 and WS-7 achieve now?
2. What is still mock, partial, or pending?
3. What should the next implementation sequence be?

No runtime code, migrations, secrets, or UI changes are part of this component.

## Evidence Reviewed

- `docs/components/SPEC-WS-2.md`
- `docs/components/SPEC-WS-7.md` (currently not a useful top-level spec; WS-7 state is inferred from component specs and code)
- Components 23-56 under `docs/components`
- WS-2 web routes and components:
  - `apps/web/src/app/dashboard/*`
  - `apps/web/src/components/CardUploadFlow.tsx`
  - `apps/web/src/components/PlanDetailsView.tsx`
  - `apps/web/src/components/ProviderSearchView.tsx`
  - `apps/web/src/components/VoiceAssistantUI.tsx`
- WS-7 service surfaces:
  - `services/voice-agent/src/voice_agent/api/v1`
  - `services/voice-agent/src/voice_agent/graph`
  - `services/voice-agent/src/voice_agent/tts`
  - `services/telephony/src/twilio_ws`
- Real data service surfaces:
  - `services/eligibility/src/eligibility/api/v1`
  - `services/providers/src/providers/api/v1`
  - `services/document-ai/src/document_ai/api/v1`
- Startup and readiness:
  - `scripts/start.py`

## Recent Changes Accounted For

This roadmap accounts for the recent project movement from a generic voice demo toward a more realistic insurance agent:

- Real-data read APIs now exist in Eligibility and Providers.
- Document AI exposes OCR and payor-classification endpoints, though model availability remains a runtime constraint.
- Voice-agent now has a fixed LangGraph-style pipeline rather than only ad hoc mock responses.
- Claude answer composition is available and should remain the answer-generation path.
- Cartesia TTS has become the strongest voice playback path for the browser demo.
- Gemini Live experiments are present, but they caused product-path confusion and should be isolated from the main demo unless explicitly revisited.
- Startup diagnostics now surface voice-runtime, key, SDK, and service health issues more clearly.

## Current Capability Summary

### WS-2 - Dashboard/UI

WS-2 currently provides a usable dashboard shell with routes for card, plan, providers, voice, and calls.

What works now:

- The dashboard shell and sidebar navigation are present.
- The card upload page can demonstrate upload and extracted insurance-card fields using mock extraction data.
- The plan page can show member and plan details using local mock data.
- The providers page can demonstrate provider search UX using local mock provider data.
- The voice page can ask typed questions and receive backend answers.
- Browser speech recognition can capture spoken input when the browser supports it.
- The voice page can send user questions to the voice-agent backend.
- The voice page can play back agent responses through Cartesia when the Cartesia path is configured and healthy.
- The voice page can show pipeline state, latest answer, transcript, runtime status, and backend connection badges.

What is still mock or incomplete:

- Card upload is not yet wired end-to-end to Document AI OCR and payor classification.
- Plan details are not yet read from the eligibility APIs.
- Provider search is not yet read from the providers APIs.
- Call history is not yet connected to real telephony call/session records.
- Voice UI still carries some demo-oriented labels and fallbacks from earlier Gemini and browser-TTS experiments.
- The UI does not yet have a clean "real mode vs demo mode" contract across all pages.
- There is no complete Playwright regression suite for the main dashboard flows.
- Login/member selection is not fully established as a product-level flow.

### WS-7 - Voice Agent and Telephony

WS-7 currently has the main backend pieces needed for a credible insurance voice-agent demo.

What works now:

- Voice-agent exposes `/api/v1/agent/respond`.
- Voice-agent exposes `/api/v1/tts/synthesize`.
- Voice-agent exposes `/api/v1/runtime/status`.
- Voice-agent has a fixed LangGraph-style pipeline:
  - identify member
  - understand intent
  - call tool
  - compose answer
  - hallucination guard
  - prepare response
- Claude answer composition is available when configured.
- Mock composition remains available for deterministic fallback and tests.
- Tool calls can resolve coverage, cost, formulary, provider, and escalation style intents.
- HTTP tool mode can call Eligibility and Providers services instead of only local mocks.
- Hallucination/fact-check guard output is surfaced in responses.
- Cartesia TTS can produce browser-playable speech from the final answer.
- Twilio Media Streams inbound audio bridge exists.
- Twilio return-audio path exists for sending voice-agent audio back to the call stream.
- Startup preflight now reports key voice runtime configuration and missing dependencies.

What is still mock or incomplete:

- Gemini Live is experimental and should not be treated as the primary product path if Cartesia is the selected voice runtime.
- Browser STT is useful for local demo, but is not a production-grade deployed STT strategy by itself.
- The voice-agent still needs a stronger real-mode contract for member context instead of falling back to a demo member.
- Tool traces are not yet standardized as UI events across browser voice and telephony.
- Twilio phone-call flow is not yet proven to parity with the browser voice demo.
- Cartesia output is currently batch-oriented; lower-latency streaming TTS is still pending.
- The agent needs stronger stuck-turn handling, cancellation, and session watchdog coverage.
- Langfuse/MLflow observability is present in infrastructure but not yet fully productized for voice-agent traces.
- Eval harness work exists in specs, but should be promoted into a repeatable pass/fail gate before demo.

## Real APIs Available Now

### Eligibility Service

Current routes include:

- `GET /api/v1/members/{member_id}/summary`
- `GET /api/v1/plans/{plan_id}/benefits`
- `GET /api/v1/formulary/search`
- `POST /api/v1/coverage`
- `POST /api/v1/cost/estimate`
- `POST /api/v1/formulary/lookup`
- `POST /api/v1/fact_check`

These can support:

- Plan details UI from real service data.
- Coverage question answering.
- Cost/copay/deductible question answering.
- Formulary question answering.
- Grounding and hallucination checks.

### Providers Service

Current routes include:

- `GET /api/v1/providers/search`
- `GET /api/v1/providers/{npi}`
- `GET /api/v1/providers/near`
- `POST /api/v1/providers/bulk`

These can support:

- Real provider search UI.
- In-network provider recommendations from the voice agent.
- Provider detail cards.
- Bulk provider lookup for richer tool traces.

### Document AI Service

Current routes include:

- `POST /api/v1/card_ocr`
- `POST /api/v1/payor_classify`

These can support:

- Real insurance-card OCR from the card upload page.
- Payor classification from uploaded card images.
- Field confidence display and human review workflow.

Important limitation:

- Document AI routes depend on model artifacts/runners being loaded. If not loaded, routes can return service unavailable. WS-2 must handle that as a visible fallback, not as a silent failure.

## What Can Be Demoed Now

### Strong Demo Path

The strongest current demo is:

1. Open the Voice page.
2. Ask a typed or spoken insurance question.
3. Send the question to the voice-agent backend.
4. Let LangGraph choose the intent and tool path.
5. Use Eligibility/Providers services when HTTP tool mode is configured.
6. Compose with Claude when configured.
7. Run hallucination guard.
8. Show answer, pipeline state, and tool trace.
9. Speak the final answer with Cartesia.

This is the closest path to a real AI telephone-agent experience today.

### Medium-Confidence Demo Path

The plan, provider, and card pages can be shown as product surfaces, but they should be described as dashboard workflows with mock UI data unless wired to the real services.

### Not Yet Recommended as Demo Path

Gemini Live should not be the core demo path right now. It introduced runtime confusion, inconsistent response ownership, and a mismatch with the desired architecture where Claude composes the answer and Cartesia speaks it.

## Recommended Product Architecture

The clean direction is:

- Claude composes grounded insurance answers.
- LangGraph owns the deterministic pipeline and tool routing.
- Eligibility, Providers, and Document AI provide real data.
- Cartesia provides the human voice.
- Browser STT remains the local demo input path until a production STT provider is selected.
- Twilio Media Streams becomes the telephone transport once browser demo parity is proven.
- Gemini experiments should be retired or isolated behind a clearly disabled experimental flag.

## Pending WS-2 Work

High priority:

- Wire Card Upload to Document AI OCR and payor classification.
- Wire Plan Details to Eligibility member summary and benefits APIs.
- Wire Provider Search to Providers search/near APIs.
- Add a shared API client layer and typed response contracts.
- Add clear UI mode labels: real data, demo data, service unavailable.
- Add Playwright tests for card, plan, provider, and voice flows.

Medium priority:

- Add member selection or authenticated member context.
- Add call history from real telephony/session data.
- Add export/share transcript or call summary.
- Improve responsive layout and demo polish.
- Add loading, empty, error, retry, and stale-data states consistently.

Lower priority:

- Add map visualization for provider locations.
- Add richer tutorial and guided demo mode.
- Add user-facing settings for voice provider and answer mode.

## Pending WS-7 Work

High priority:

- Make HTTP tool mode the default real path for local demo when services are healthy.
- Remove hidden demo-member fallback outside explicit demo mode.
- Standardize the agent response contract consumed by WS-2.
- Standardize tool trace and pipeline events.
- Add stuck-turn watchdog and cancellation guarantees.
- Keep Cartesia as the selected TTS runtime and remove Gemini from the main path.
- Add integration tests for Claude + tools + guard + Cartesia response metadata.

Medium priority:

- Add streaming Cartesia playback to reduce perceived latency.
- Add production STT option for deployed/browser-independent use.
- Add Twilio phone-call parity with the browser voice flow.
- Add Langfuse traces for every agent turn.
- Add eval scenarios as a required regression gate.

Lower priority:

- Add voice persona tuning.
- Add member memory/thread continuity.
- Add escalation handoff summaries.
- Add cost and latency dashboards.

## Non-Goals

- This component does not implement WS-2 UI wiring.
- This component does not implement WS-7 runtime changes.
- This component does not add new API endpoints.
- This component does not modify `.env`, secrets, or deployment configuration.
- This component does not remove Gemini code.

## Acceptance Criteria

- The current WS-2 and WS-7 state is documented.
- Real APIs that can be used by UI and voice-agent are listed.
- Mock, partial, and real capabilities are separated clearly.
- Pending WS-2 items are prioritized.
- Pending WS-7 items are prioritized.
- A follow-up implementation plan exists in `PLAN.md`.
- No runtime code is changed by this component.
