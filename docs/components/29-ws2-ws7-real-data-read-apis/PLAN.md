# Component 29 - WS-2/WS-7 Real Data Read APIs - Implementation Plan

> Create read-only real-data APIs for UI and telephone AI.

## Inspect

1. [ ] Read `data/README.md`.
2. [ ] Read `services/eligibility/alembic/versions/001_init_schema.py`.
3. [ ] Read `services/eligibility/src/eligibility/api/v1/__init__.py`.
4. [ ] Read `services/providers/src/providers/api/v1/__init__.py`.
5. [ ] Confirm `database_url` config in both services.
6. [ ] Confirm local Postgres table names match schema.

## Design

7. [ ] Add SQLAlchemy connection/session helpers to eligibility service.
8. [ ] Add SQLAlchemy connection/session helpers to providers service.
9. [ ] Add Pydantic response schemas for member summary, plan, benefit, formulary drug, and provider.
10. [ ] Keep all endpoints read-only.
11. [ ] Keep API responses stable enough for both frontend and voice-agent tools.

## Eligibility Implementation

12. [ ] Create repository helpers for:
    - member lookup by `member_id`
    - plan lookup by `plans.id`
    - benefit lookup by `plan_id`
    - formulary lookup by `plan_id` and drug text
13. [ ] Add `GET /api/v1/members/{member_id}/summary`.
14. [ ] Add `GET /api/v1/plans/{plan_id}/benefits`.
15. [ ] Add `GET /api/v1/formulary/search`.
16. [ ] Return `404` when member or plan does not exist.
17. [ ] Return empty arrays for no benefit/formulary matches.

## Providers Implementation

18. [ ] Create repository helpers for:
    - provider search by specialty/state/zip
    - provider lookup by NPI
19. [ ] Add `GET /api/v1/providers/search`.
20. [ ] Add `GET /api/v1/providers/{npi}`.
21. [ ] Sort provider search results predictably:
    - quality rating descending
    - accepting new patients first
    - provider name ascending
22. [ ] Keep `planId` accepted but optional; if in-network filtering is not ready, document that it is not applied yet.

## Tests

23. [ ] Add eligibility unit tests for schema mapping.
24. [ ] Add eligibility unit tests for empty/missing rows.
25. [ ] Add provider unit tests for search response mapping.
26. [ ] Add provider unit tests for missing NPI.
27. [ ] Add integration smoke tests gated on `DATABASE_URL`.
28. [ ] Run:
    - `uv run pytest services/eligibility/tests`
    - `uv run pytest services/providers/tests`
    - existing voice-agent tests if touched indirectly

## Manual Verification

29. [ ] Start local stack with `python scripts/start.py`.
30. [ ] Check:
    - `curl http://localhost:8002/health`
    - `curl http://localhost:8003/health`
31. [ ] Try member summary with a seeded member.
32. [ ] Try benefit lookup with a real plan id.
33. [ ] Try formulary search with a known drug.
34. [ ] Try provider search with a specialty/state.

## Commit

35. [ ] Commit only this component.

```bash
git commit -m "feat(data): expose real-data read APIs for UI and voice tools"