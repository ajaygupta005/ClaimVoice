# Component 46 - WS-6 Hallucination Guard - Research

## Why generalize the dollar-only guard to tiers and booleans
The original `graph/nodes/hallucination_guard.py` only matched dollar amounts, so
a fabricated formulary tier or a flipped coverage boolean ("not covered" when the
facts say covered, "prior authorization required" with no such fact) would sail
through ungrounded. WS-6 surfaces formulary and coverage answers, so the matcher
is extended to three families that cover the answers the agent actually produces:
dollar amounts (`$[\d,]+`), formulary tiers (`Tier N`), and coverage booleans.
Any token of those families that is present in the answer but absent from the
grounding `facts` marks the answer ungrounded.

## Why call the shared WS-4 backbone with an in-process fallback
Grounding truth should have a single source. WS-4 already exposes a mock
`POST /fact_check` with the same matcher, and in production it will check against
the plan knowledge graph and SBC RAG. So in `tool_mode="http"` the guard POSTs
`{answer, facts}` to WS-4 and trusts its `grounded` / `guardReason`, keeping one
authoritative implementation. To keep the ~236-test suite offline and resilient,
the guard runs the identical matcher in-process whenever mode is `mock` or the
HTTP call fails — the two paths agree by construction because the in-process
matcher mirrors WS-4's mock.

## Why preserve the reason-string vocabulary
The graph tests and downstream UI assert on the substrings `grounded`,
`ungrounded`, and `escalat`. Keeping those tokens in the reason strings
(`"all claims grounded in tool result"`, `"ungrounded claims: [...]"`, and the
escalation reason) means the rewire is behavior-preserving for the existing
suite while adding the real http path.
