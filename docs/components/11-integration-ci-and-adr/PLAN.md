# Component 11 - Integration Tests CI + ADR-0002 (Claude over GPT) - Implementation Plan

> Step-by-step. Check off as you go.

### Integration workflow
1. [ ] Author `.github/workflows/integration.yml` with `on: { push: { branches: [main] } }`.
2. [ ] Define `services:` block with `postgres` and `redis` containers.
3. [ ] Pass `DATABASE_URL` and `REDIS_URL` env to the test steps.
4. [ ] Run `bash scripts/db_migrate.sh`.
5. [ ] Run `uv run pytest tests/integration -q`.
6. [ ] Upload JUnit XML artifact on failure.

### ADR-0002
7. [ ] Author `docs/adr/0002-claude-over-gpt.md` with the 5 sections.
8. [ ] Cite specific eval comparisons we ran (or plan to run) in Component 10.
9. [ ] Link from `ARCHITECTURE.md` (which gets finalized in Component 12).

### Wrap
10. [ ] Commit with message `chore(ci): integration tests workflow + adr-0002 claude over gpt`.

