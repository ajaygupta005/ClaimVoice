# Component 01 - Monorepo Foundation - Implementation Plan

> Step-by-step. Check off as you go.

1. [ ] Create `.gitignore` (Node + Python + IDE + data/raw + artifacts).
2. [ ] Create `.editorconfig` (2-space default, 4-space for Python, LF line endings).
3. [ ] Create `LICENSE` (MIT).
4. [ ] Author `pnpm-workspace.yaml` listing workspace globs.
5. [ ] Author root `pyproject.toml` as a uv workspace with `[tool.uv.workspace]` members.
6. [ ] Author `turbo.json` with `build`, `lint`, `typecheck`, `test`, `dev` pipelines.
7. [ ] Author `Justfile` with `install`, `up`, `down`, `dev`, `test`, `eval`, `data.ingest` recipes.
8. [ ] Author baseline `README.md` (placeholder for the full README in component 12).
9. [ ] Run `pnpm install` to confirm pnpm-workspace loads.
10. [ ] Run `uv sync` to confirm uv workspace loads.
11. [ ] Commit with message `chore(repo): initialize monorepo with pnpm and uv workspaces`.

