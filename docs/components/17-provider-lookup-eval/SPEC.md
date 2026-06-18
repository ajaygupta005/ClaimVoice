# Component 17 - Provider Lookup Eval

> Branch: `feat/eval-provider-lookup` | Day(s): 23 | Workstream: WS-8

Deterministic Inspect AI task that scores provider ranking/filtering against a golden dataset. Runs in CI with no DB and no API key. Pins the `/providers/near` ranking contract: specialty match, radius filter, in-network / accepting-new filters, distance ascending with quality as tiebreak.
