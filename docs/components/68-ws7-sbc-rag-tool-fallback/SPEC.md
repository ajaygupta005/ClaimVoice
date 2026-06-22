# Component 68 - WS-7 SBC RAG Tool Fallback

## Purpose

Use the newly merged WS-4 SBC RAG endpoint as a grounding fallback and citation source for WS-7 insurance answers.

The existing structured eligibility/formulary tools remain the primary source of truth. SBC RAG is used when structured tools cannot confidently answer or when the answer would benefit from source text evidence.

## Required Behavior

- WS-7 can call `POST /api/v1/sbc/retrieve` on the eligibility service.
- The request contains:
  - `planId`
  - `query`
  - `topK`
- Coverage questions should query SBC RAG when structured coverage data is missing, ambiguous, or needs supporting text.
- Formulary questions may query SBC RAG only as supporting evidence; structured formulary lookup remains primary.
- Empty RAG results are not treated as a fatal error.
- Missing `VOYAGE_API_KEY` or an unavailable RAG service produces an explicit fallback reason.
- RAG use must be visible in WS-7 response metadata.

## Response Metadata

Responses that attempted RAG must include enough metadata for UI, eval, and logs:

- `ragAttempted`
- `ragAvailable`
- `ragFallbackReason`
- `ragChunksCount`
- `ragSource`

`ragSource` should identify the eligibility SBC endpoint, not expose service secrets.

## Failure Modes

- Missing `VOYAGE_API_KEY`: return explicit unavailable metadata and continue with structured tool result if possible.
- Empty `sbc_chunks`: return explicit empty-result metadata and do not invent citations.
- Missing plan ID: skip RAG and report `missing_plan_id`.
- Eligibility service timeout: continue only if primary structured facts are sufficient; otherwise produce a safe clarification/escalation.

## Acceptance Criteria

- A coverage answer can use SBC RAG when structured coverage data is insufficient.
- Structured coverage/formulary answers still work when RAG is unavailable.
- No answer claims that RAG evidence exists when `chunks` is empty.
- Unit tests cover successful chunks, empty chunks, missing key, service failure, and missing plan ID.
- Manual curl against `/api/v1/agent/respond` shows RAG metadata for an MRI coverage question when indexed SBC data exists.
