# Component 68 - WS-7 SBC RAG Tool Fallback Plan

## Implementation Steps

1. Inspect current WS-7 tool routing.
   - Find where coverage and formulary intents call eligibility tools.
   - Identify the state fields that already carry member and plan context.

2. Add a small eligibility RAG client.
   - Call `POST /api/v1/sbc/retrieve`.
   - Keep the client server-side in voice-agent.
   - Reuse existing eligibility base URL and HTTP timeout conventions.

3. Wire RAG as fallback/evidence.
   - Coverage: call RAG when structured tool result is missing, low-confidence, or ambiguous.
   - Formulary: call RAG only when structured formulary is inconclusive.
   - Preserve structured tool results as primary facts.

4. Normalize RAG result metadata.
   - Include attempted/available/error/empty states.
   - Store retrieved chunks in a structured state field for later Claude/guard steps.

5. Add tests.
   - Mock eligibility RAG success.
   - Mock empty chunks.
   - Mock `503` missing `VOYAGE_API_KEY`.
   - Mock timeout/error.
   - Verify structured-tool-only answers still work.

## Suggested Files

- `services/voice-agent/src/voice_agent/tools/*`
- `services/voice-agent/src/voice_agent/graph/nodes/call_tool.py`
- `services/voice-agent/src/voice_agent/graph/state.py`
- `services/voice-agent/tests/unit/*`

## Validation

- Voice-agent unit tests for coverage/formulary flows.
- Manual `/api/v1/agent/respond` checks with and without RAG availability.
- Confirm no UI-facing response includes fake citations.

## Risks

- Calling RAG too often can add latency and Voyage API cost.
- Using RAG as primary truth could conflict with structured benefits.
- Empty chunks can be mistaken for "not covered" unless handled explicitly.

## Done When

- WS-7 can retrieve SBC chunks for a plan-backed question.
- RAG failures are explicit and non-catastrophic.
- Structured tools remain primary.
- RAG metadata is available for Claude, guard, UI, and eval.
