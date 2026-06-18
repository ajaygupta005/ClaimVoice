# Component 17 - Provider Lookup Eval - Plan

1. Implement `rank_providers()` reference in `eval/tasks/provider_lookup_eval.py`.
2. Author `eval/datasets/provider_queries.json` (5 cases covering each filter).
3. Deterministic `score_case()` comparing NPI order to golden.
4. Lazy inspect-ai task registration.
5. Tests in `eval/tests/test_provider_lookup.py`.
