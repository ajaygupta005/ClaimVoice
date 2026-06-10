# Component 03 - GitHub Actions CI Pipeline - Research

> Alternatives considered, decisions made, references.

## Why GitHub Actions
- Free for public repos. Free 2000 min/month for private.
- Native integration with PR checks, status badges, secrets management.
- Service containers built-in (used in component 11 for integration tests).

## Workflow split: 5 separate workflows vs one mega-workflow
- Faster PR feedback (CI is the fastest, runs on every push).
- Different triggers (cron for evals, manual gate for deploy).
- Easier to read in the Actions tab.

## pnpm action vs npm caching
- `pnpm/action-setup@v4` handles the pnpm store automatically. Saves ~20s per run vs hand-rolling the cache.

## astral-sh/setup-uv vs manual install
- Official action from Astral. Caches uv binary + Python interpreter. ~30s faster than running `pip install uv` each time.

## Why mypy in CI even when pre-commit runs it
- Pre-commit is local; teammates can skip it with `--no-verify`.
- CI is the gate.

## References
- GitHub Actions docs: https://docs.github.com/en/actions
- pnpm/action-setup: https://github.com/pnpm/action-setup
- astral-sh/setup-uv: https://github.com/astral-sh/setup-uv

