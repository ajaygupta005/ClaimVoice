# Component 03 - GitHub Actions CI Pipeline - Implementation Plan

> Step-by-step. Check off as you go.

1. [ ] Author `.github/workflows/ci.yml` with `on: { pull_request, push: { branches: [main] } }`.
2. [ ] Add `permissions: { contents: read }` (least privilege).
3. [ ] Define `lint-and-test` job with `runs-on: ubuntu-latest`.
4. [ ] Add Node 20 setup with pnpm cache (use pnpm-lock.yaml as cache key).
5. [ ] Add Python 3.12 setup with uv (use `uv sync --frozen` after).
6. [ ] Add the 11-step pipeline (install, install, lint, typecheck x2, test x2).
7. [ ] Set `fail-fast: false` on the job matrix if any.
8. [ ] Author `.github/PULL_REQUEST_TEMPLATE.md` with What / Why / How / Testing sections.
9. [ ] Author `.github/CODEOWNERS` mapping paths to reviewers.
10. [ ] Open a PR with a deliberate lint error to confirm CI blocks merges.
11. [ ] Open a PR fixing the error to confirm CI passes and merges work.
12. [ ] Commit with message `chore(ci): add github actions ci workflow with lint typecheck and tests`.

