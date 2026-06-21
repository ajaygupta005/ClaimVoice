# Component 56 - WS-2/WS-7 Voice Demo Readiness

## Goal

Capture the current voice assistant state after the Cartesia Skylar cleanup, and define the remaining WS-2 and WS-7 work needed to move from a strong local demo to a production-shaped voice flow.

## Current Outcome

The Voice Assistant page now supports a practical local demo:

- Browser STT is the default microphone path.
- Claude remains the answer composer.
- The agent uses the existing grounded tool flow for coverage, formulary, cost, provider, and escalation intents.
- Cartesia Skylar is the default answer speakback path when `VOICE_AGENT_TTS_PROVIDER=cartesia` and `CARTESIA_API_KEY` are configured.
- Gemini Live is no longer the default member-facing voice path. It remains an experimental runtime behind explicit flags.
- The UI shows answer text immediately, then prepares and plays Cartesia audio without blocking the transcript.
- Voice state has watchdogs so stuck listening, preparing, or speaking states return to a usable state.
- `scripts/start.py` reports voice runtime readiness and missing runtime dependencies during startup.

## In Scope

- Document what is ready now.
- Document the next WS-2 UI items.
- Document the next WS-7 voice-agent and backend items.
- Keep the plan implementation-ready, with small ordered steps.

## Out of Scope

- New code changes in this component.
- Removing Gemini source files entirely.
- Replacing browser STT with a production STT vendor.
- Building full Twilio phone-call voice parity.

## WS-2 Status

WS-2 is now usable for a browser-based demo:

- Voice page layout is stable enough for demo use.
- User can type or speak questions.
- Transcript receives the final user question and agent answer.
- Agent pipeline shows the grounded response flow.
- Connections panel reports the current local service/runtime status.
- Cartesia speakback can be heard when configured.

WS-2 still needs:

- A production STT decision for deployed environments.
- Better mobile and narrow-screen layout checks.
- A small demo script mode that loads a known member, plan, and question set.
- Transcript export or session reset controls.
- More explicit error copy when microphone permissions fail.
- Runtime latency indicators for STT, Claude, tools, guard, and TTS.

## WS-7 Status

WS-7 is now usable as a local voice-agent backend:

- Claude answer composition is active when configured.
- LangGraph/tool orchestration is represented by the agent pipeline.
- Eligibility and provider tools can ground answers through local service APIs.
- Hallucination guard blocks or escalates weak answers.
- Cartesia TTS endpoint returns playable WAV audio for browser speakback.
- Gemini runtime has fallback checks, but is no longer the recommended default for this demo.

WS-7 still needs:

- Production STT integration if browser STT is not enough.
- Streaming Cartesia TTS or chunked audio playback to reduce perceived latency.
- Stronger tool coverage for member benefits, prior authorization, provider lookup, formulary, claims, and document-derived plan facts.
- Better guard policies for partial answers, uncertain coverage, and escalation.
- Evaluation runs over realistic insurance scenarios.
- Observability in Langfuse or logs for each voice turn.
- Twilio phone-call parity using the same answer and TTS contracts.

## Acceptance Criteria

- The repository contains a clear roadmap for the current voice demo state.
- WS-2 and WS-7 pending work is separated.
- The plan can be used directly to create the next components without rediscovering context.
- No environment secrets are documented.
