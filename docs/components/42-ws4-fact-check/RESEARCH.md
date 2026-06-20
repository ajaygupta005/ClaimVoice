# Component 42 - WS-4 Fact-Check - Research

## Why structured deterministic matching as the default
The fact-check endpoint is on the critical path of every spoken answer, so it must
work offline, with no API key, and give the same verdict every time -- a flaky or
key-gated guard is worse than no guard. The default `mock` mode is therefore a pure
deterministic matcher over the three claim shapes that actually carry risk in this
domain: dollar amounts (`\$[\d,]+`), formulary tiers (`[Tt]ier \d+`), and a small set
of coverage booleans ("not covered", "prior authorization required"). Each token
found in the answer must appear in the joined `facts` text; amounts are normalised
(strip commas, lowercase) before comparison so `$1,050` matches `$1050`. The matcher
deliberately mirrors the producers: coverage/cost/formulary emit facts through the
same `cents_to_usd` and `Tier N` phrasing this regex looks for, so a grounded answer
passes and an invented amount/tier/flag lands in `ungroundedClaims`. It is pure over
its payload -- no DB, no network -- which is exactly what CI and the WS-6 unit tests
need.

## Why claude mode is advisory with a mock fallback
Free-text answers can be grounded while paraphrasing the facts in ways a regex
misses ("about a thousand dollars" vs `$1,050`), so an optional `claude` entailment
judge (`FACT_CHECK_MODE=claude` + `ANTHROPIC_API_KEY`, model `claude-sonnet-4-6`)
gives a softer, semantic verdict and a human-readable reason. But the LLM call can
time out, rate-limit, or return malformed JSON, and the guard must never hard-fail
the answer pipeline on that. So claude mode is wrapped in try/except and falls back
to the deterministic matcher on any error -- the endpoint always returns a verdict,
and the `mode` field tells the caller which path produced it. Claude is thus an
*upgrade* to grounding confidence, not a dependency.

## Why this is the single backbone WS-6's guard calls
There is exactly one place in the system that decides "is this claim grounded?" --
this endpoint -- rather than re-implementing matching logic inside the voice agent.
WS-6's hallucination guard posts the candidate answer plus the tool-sourced `facts`
here and refuses to speak anything that comes back ungrounded. Centralising the
verdict means the offline matcher, the optional Claude judge, and the producer
phrasing (Components 40-41) all evolve in one spot, and the same `{grounded,
guardReason, ungroundedClaims, mode}` contract serves both the unit tests and the
live guard. The end-to-end `test_member_journey` integration test (M7) exercises this
backbone in the context of the full WS-4 journey, and the shared `conftest.py`'s
auto-skip keeps that integration coverage from breaking the offline unit run.
