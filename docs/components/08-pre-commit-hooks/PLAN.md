# Component 08 - Pre-Commit Hooks (Code Hygiene) - Implementation Plan

> Step-by-step. Check off as you go.

1. [ ] Author `.pre-commit-config.yaml` with all hooks pinned to current stable versions:
    - astral-sh/ruff-pre-commit (`ruff`, `ruff-format`)
    - pre-commit/mirrors-mypy
    - pre-commit/pre-commit-hooks (trailing-whitespace, EOF, check-yaml, check-toml, check-merge-conflict)
    - Yelp/detect-secrets
    - prettier
    - eslint
2. [ ] Run `detect-secrets scan > .secrets.baseline` to seed.
3. [ ] Update `Justfile` `install` recipe to call `pre-commit install`.
4. [ ] Run `pre-commit run --all-files` once to clean the repo and confirm a green state.
5. [ ] Commit with message `chore(ci): add pre-commit hooks with ruff mypy eslint prettier and secret scan`.

