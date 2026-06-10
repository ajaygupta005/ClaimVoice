# Component 03 - GitHub Actions CI Pipeline

> **Branch**: `chore/ci-workflow`  |  **Day(s)**: 3  |  **Workstream**: WS-7/WS-8

## Goal & Scope

Every pull request and every push to `main` runs lint + typecheck + unit tests inside GitHub Actions within 5 minutes.

**Workflow file**: `.github/workflows/ci.yml`

**Matrix**:
- Node 20 with pnpm cache.
- Python 3.12 with uv cache.

**Steps in order**:
1. checkout
2. setup-node with pnpm
3. setup-python with uv (astral-sh/setup-uv)
4. `pnpm install --frozen-lockfile`
5. `uv sync`
6. `pnpm lint` (eslint)
7. `pnpm typecheck` (tsc --noEmit per workspace)
8. `uv run ruff check .`
9. `uv run mypy .`
10. `pnpm test` (vitest/jest)
11. `uv run pytest -q`

**Fail-fast: false** so a single failure shows all problems.

**Out of scope**: integration tests (component 11), nightly eval workflow.

