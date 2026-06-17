# Component 11 - Integration Tests CI + ADR-0002 (Claude over GPT)

> **Branch**: `chore/integration-ci-and-adr`  |  **Day(s)**: 11-12  |  **Workstream**: WS-7/WS-8

## Goal & Scope

Two related deliverables:

### A. Integration tests CI workflow
Every push to `main` runs cross-service integration tests with real Postgres + Redis service containers.

**Workflow file**: `.github/workflows/integration.yml`

**Triggers**: push to `main` only (not PRs - too slow for fast feedback there).

**Steps**:
1. Spin up Postgres + Redis as GitHub Actions service containers.
2. `bash scripts/db_migrate.sh` to apply migrations.
3. `uv run pytest tests/integration -q`.
4. Upload JUnit XML on failure.

### B. ADR-0002: Claude over GPT
Architecture Decision Record documenting the choice of Anthropic Claude 3.5 Sonnet over OpenAI GPT-4o.

**Format**: Status / Context / Decision / Consequences / Alternatives.

**File**: `docs/adr/0002-claude-over-gpt.md`.

