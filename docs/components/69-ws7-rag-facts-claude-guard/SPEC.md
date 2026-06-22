# Component 69 - WS-7 RAG Facts for Claude and Guard

## Purpose

Feed retrieved SBC chunks into Claude answer composition and hallucination guard so valid insurance answers are less likely to be incorrectly guarded.

This component depends on Component 68 producing structured RAG chunks in WS-7 state.

## Required Behavior

- Claude receives SBC chunks as structured facts, not as loose debug text.
- The hallucination guard receives the same retrieved facts used by Claude.
- Guard decisions can distinguish:
  - supported by structured tool facts
  - supported by SBC RAG facts
  - unsupported by any fact
  - no facts available
- RAG-backed facts must include:
  - `chunkText`
  - `sectionName`
  - `sourceFile`
  - `distance`
- Claude should not cite a chunk unless it was actually retrieved.

## Guard Behavior

Valid answers should pass when the claim is supported by structured tool facts or RAG facts.

Unsupported claims should still fail, including:

- invented dollar amounts
- invented coverage status
- invented prior authorization status
- invented formulary tier
- invented provider availability

## Response Metadata

Guard output should include:

- `guardPassed`
- `guardReasonCode`
- `supportedBy`
- `unsupportedClaims`
- `ragFactsUsed`

`supportedBy` may include `structured_tool`, `sbc_rag`, or both.

## Acceptance Criteria

- A valid MRI coverage answer backed by SBC chunks passes guard.
- A valid urgent-care/cost answer backed only by structured data still passes guard.
- An unsupported coverage claim fails with a concrete reason code.
- Claude answers do not mention citations when no RAG chunks exist.
- Tests cover guard pass/fail behavior for structured-only, RAG-backed, and unsupported answers.
