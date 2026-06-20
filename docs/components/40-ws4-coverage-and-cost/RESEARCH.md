# Component 40 - WS-4 Coverage & Cost - Research

## Why a representative plan-level deductible / OOP (MAX over In-Network benefits)
Deductible and out-of-pocket maximums in the seeded `plan_benefits` table are
attached to individual benefit rows, not stored once per plan. A member asking
"how much of my deductible is left?" must get an answer even when the question
does not name a service that happens to match a benefit row. We compute a single
representative plan level by taking `MAX(individual_deductible_cents)` and
`MAX(out_of_pocket_max_cents)` over the plan's In-Network benefit rows. MAX (rather
than MIN or an average) picks the true plan-wide ceiling -- the value the member's
spend is actually measured against -- so the math is stable and independent of
whether a service matched. This keeps `/cost/estimate` correct for the bare
`costType: "deductible"` / `"oop"` cases.

## Why cents-only + lib/money.py for display
All monetary values are stored and computed as integer cents (BIGINT) so there is
no floating-point drift in deductible/OOP arithmetic -- `max(0, total - spent)` is
exact. Money only ever becomes a string at the presentation boundary, via
`lib/money.py::cents_to_usd`, which renders `150000 -> "$1,500"`, `3000 -> "$30"`,
and `12345 -> "$123.45"` (whole-dollar amounts drop the trailing `.00`). Centralising
formatting matters because those USD strings are embedded verbatim in the `facts`
list, and the fact-check guard later regex-matches `\$[\d,]+` against the same
strings -- so a single canonical formatter keeps the producer and the verifier in
agreement.

## Why facts[] on every response
The fact-check guard (Component 42) and WS-6's hallucination guard do not re-derive
coverage from the database; they verify that an answer is *entailed* by a list of
grounding strings. Coverage and cost are the primary producers of those strings, so
each response builds `facts` as it builds the structured fields: e.g.
`"MRI is covered (In Network)"`, `"20% coinsurance"`, `"prior authorization required"`,
`"deductible $1,050 remaining"`. The facts use the same `cents_to_usd` output and the
same `Tier N` / boolean phrasing the guard's matcher expects, so a grounded answer
passes deterministically and an invented dollar amount or flag fails.

## Why a copay-vs-coinsurance estimate range
A definitive single-number cost estimate is only honest when the benefit is
copay-based -- then `estimateLow == estimateHigh == copay`. For a coinsurance
benefit the member's actual cost depends on the negotiated service price and how
much deductible is left, neither of which the structured data alone pins down. So
for coinsurance we surface a conservative range: `estimateLowCents = 0` (if the
service is fully covered after the deductible is met) up to
`estimateHighCents = deductibleRemainingCents` (worst case: the member pays the
negotiated rate against the remaining deductible). Returning a range -- rather than
guessing a point estimate -- avoids fabricating a precise dollar figure the guard
would have to reject as ungrounded.
