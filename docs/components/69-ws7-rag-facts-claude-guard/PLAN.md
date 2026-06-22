# Component 69 - WS-7 RAG Facts for Claude and Guard Plan

## Implementation Steps

1. Inspect Claude answer composition.
   - Find where tool facts are converted into Claude prompt context.
   - Identify current guard input structure.

2. Add a structured RAG fact model.
   - Normalize chunks from Component 68.
   - Keep source fields stable for UI and eval.

3. Update Claude context assembly.
   - Include structured benefits first.
   - Include SBC chunks as supporting evidence.
   - Tell Claude not to make claims outside facts.

4. Update guard input.
   - Pass structured tool facts and RAG facts together.
   - Preserve provenance so guard can explain what supported the answer.

5. Add reason codes.
   - `supported_by_structured_tool`
   - `supported_by_sbc_rag`
   - `unsupported_claim`
   - `no_facts_available`
   - `rag_unavailable`

6. Add tests.
   - Guard pass with structured facts.
   - Guard pass with SBC chunk facts.
   - Guard fail with unsupported amount/status.
   - Claude prompt includes chunks when present.
   - Claude prompt omits chunks when absent.

## Suggested Files

- `services/voice-agent/src/voice_agent/graph/*`
- `services/voice-agent/src/voice_agent/guard/*`
- `services/voice-agent/src/voice_agent/llm/*`
- `services/voice-agent/tests/unit/*`

## Validation

- Run voice-agent unit tests.
- Run manual `/api/v1/agent/respond` requests for coverage, cost, and formulary.
- Inspect logs/metadata for `supportedBy` and `guardReasonCode`.

## Risks

- Too much chunk text can increase latency and prompt cost.
- Guard may pass weakly related chunks if distance is ignored.
- Prompt changes can make Claude answers verbose unless constrained.

## Done When

- Claude and guard consume the same fact set.
- Guard false positives reduce for valid insurance questions.
- Unsupported claims still fail.
- Response metadata explains why guard passed or failed.
