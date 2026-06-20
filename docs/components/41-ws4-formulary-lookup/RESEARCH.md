# Component 41 - WS-4 Formulary Lookup - Research

## Why "alternatives" = same-or-lower tier, excluding the match
Formulary tier is the structured data's only honest proxy for member cost: a lower
tier means a lower copay/coinsurance. Without drug-class metadata in the seeded data
we cannot claim two drugs are clinically interchangeable, so "alternative" is scoped
to the one thing we *can* defend -- "this drug is on your formulary at an equal or
cheaper tier." We therefore select drugs with `formulary_tier <= match.tier`,
order by tier ascending, and exclude the matched drug's own row (`id != match.id`)
so it never lists itself. For Humira (Tier 4) this surfaces lisinopril (Tier 1) and
other lower-tier drugs; for lisinopril (already Tier 1) the same-or-lower set is
small. The cutoff is deliberately conservative: we never suggest a *more* expensive
drug as an "alternative", which would be misleading. Alternatives are only computed
when the match has a non-null tier.

## Why reuse the existing FormularyDrugOut mapper
The service already had `search_formulary` SQL and a `FormularyDrugOut` camelCase
schema (`drugName`, `ndcCode`, `formularyTier`, `priorAuthRequired`,
`stepTherapyRequired`, `quantityLimit`) feeding `GET /api/v1/formulary/search`. The
lookup endpoint returns the same drug shape for both the `match` and every entry in
`alternatives`, so we factored a single `drug_out(row)` mapper that converts a
snake_case `formulary_drug` row to `FormularyDrugOut` and reused it everywhere. This
keeps the two formulary endpoints in lockstep -- one place decides how a drug row is
presented -- and avoids a second, drifting mapping. `member_repo.lookup_drug` reuses
the same `ILIKE` / tier-ordering SQL pattern as `search_formulary`, so the lookup is
a thin specialisation of an already-tested query rather than new SQL surface.
