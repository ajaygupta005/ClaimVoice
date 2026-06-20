# Component 41 - WS-4 Formulary Lookup

> **Branch**: feat/ws456-grounded-agent | **Milestone**: M5 | **Workstream**: WS-4

## Goal

`GET /api/v1/formulary/lookup` -- resolve a drug against the member's plan formulary
and return enough for the voice agent to answer "is my drug covered, and is there a
cheaper option?".

- Best match: prefer an exact drug-name match, then the lowest formulary tier.
- `alternatives`: other formulary drugs at the same-or-lower tier (cheaper or equal),
  excluding the match itself, tier-ranked.
- `onFormulary` boolean and a human-readable `facts: list[str]` for grounding.
- Reproduce golden values for demo member `CVX-0042-MT`: lisinopril -> Tier 1, no
  prior auth; Humira -> Tier 4, prior auth required, with lisinopril surfaced as a
  lower-tier alternative.

## Out of scope

- Real Medicare Part D / formulary ingest (that is WS-1's data pipeline; this runs on
  the seeded `formulary_drug` rows).
- Drug-class / therapeutic-equivalence modelling -- "alternatives" here is a pure
  tier-cost heuristic, not a clinical substitution.
