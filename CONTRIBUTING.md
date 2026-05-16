# Contributing

## Branch naming
- `feat/<scope>` — new features
- `fix/<scope>` — bug fixes
- `refactor/<scope>` — internal cleanup
- `chore/<scope>` — infra, deps, configs
- `docs/<scope>` — documentation only
- `test/<scope>` — tests only

## Commit messages
We use [Conventional Commits](https://www.conventionalcommits.org):
```
feat(voice): add check_coverage tool
fix(doc-ai): handle low-confidence regions with PaddleOCR fallback
refactor(eligibility): split plan_graph into queries and mutations
```

## PRs
- Open against `main`.
- At least one approving review from a teammate.
- All CI checks green.
- Squash-merge with a clean Conventional Commit title.

## Pre-commit
Pre-commit hooks run automatically: `ruff`, `mypy`, `eslint`, `prettier`,
`detect-secrets`. Install once: `pre-commit install`.
