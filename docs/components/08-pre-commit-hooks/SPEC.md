# Component 08 - Pre-Commit Hooks (Code Hygiene)

> **Branch**: `chore/pre-commit`  |  **Day(s)**: 7  |  **Workstream**: WS-7/WS-8

## Goal & Scope

Every commit locally auto-runs the same hygiene checks CI runs, so dev feedback is sub-second.

**Hooks**:
- `ruff` (Python lint + format)
- `mypy` (Python type-check)
- `eslint` (TypeScript lint)
- `prettier` (TS/MD/YAML format)
- `trailing-whitespace`, `end-of-file-fixer`
- `check-yaml`, `check-toml`, `check-merge-conflict`
- `detect-secrets` (with committed baseline)

**Setup**: `pre-commit install` is part of `just install`.

**Out of scope**: anything that needs network access (those run in CI only).

