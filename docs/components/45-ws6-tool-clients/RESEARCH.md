# Component 45 - WS-6 Typed Tool Clients - Research

## Why mock-fallback discipline
The graph and scorer suites pin roughly 15 deterministic mock strings and
assertions (`$` present in cost answers; "deductible" / "lisinopril" /
"cardiolog" present; per-intent grounded flags). The whole ~236-test voice-agent
suite runs offline with no DB, no services, and no keys. If the typed clients
changed those strings, the existing tests would regress. So `mock` mode is the
default and every HTTP error falls back to the exact same mock string the inline
dispatch used to return — the real path is purely additive and env-gated.

## Why facts[] flow to the guard
The old dispatch produced a single result string and the guard re-derived
grounding from it. Splitting `ToolResult` into `result` (narration) and `facts`
(grounding list) lets each tool publish the precise grounding strings — provider
names + distances, formulary tiers, dollar amounts — that the hallucination guard
(component 46) checks against, instead of re-parsing free text. `call_tool`
threads `tool_facts` onto `AgentState` so the guard node consumes them directly
and falls back to `[tool_result]` only when a tool emits no explicit facts.

## Why member_id defaults to CVX-0042-MT for http
HTTP lookups need a real member id, but the bare graph callers in the unit tests
do not pass one (they assert deterministic mock behavior). Until full member
threading lands in component 48, `call_tool` substitutes the seeded demo member
`CVX-0042-MT` whenever the state has no member id or carries the test sentinel
`MOCK-MEMBER-001`. This keeps mock tests deterministic while letting the http path
hit a member that actually exists in the seeded WS-4 database.

## Why broaden find_provider specialty extraction (fix 5837aba)
The first cut matched only a couple of specialties, so live queries like
"find a cardiologist" or "where can I get an x-ray" fell through to a generic
"provider" specialty and missed the seeded WS-5 rows. Commit `5837aba` widened
the regex to the seeded specialties (primary care / PCP, imaging / radiology,
cardiology, dermatology, pediatrics, psychiatry, orthopedics, urgent care,
OB-GYN, ophthalmology / optometry, etc.) so the http path resolves to a specialty
the providers service actually indexes.
