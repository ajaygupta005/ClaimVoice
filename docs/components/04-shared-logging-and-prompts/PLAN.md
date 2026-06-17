# Component 04 - Shared Logging + Prompts Packages - Implementation Plan

> Step-by-step. Check off as you go.

### Shared-logging
1. [ ] Build `packages/shared-logging/python/` with loguru.
2. [ ] Configure loguru sink to emit the schema JSON.
3. [ ] Implement `bind_correlation_id(id)` context manager.
4. [ ] Implement PII redaction processor with field allow-list.
5. [ ] Build `packages/shared-logging/node/` with pino.
6. [ ] Mirror the schema configuration in pino.
7. [ ] Mirror PII redaction.
8. [ ] Author `docs/logging.md` documenting the schema and correlation-ID propagation rules.

### Shared-prompts
9. [ ] Build `packages/shared-prompts/` as TypeScript package.
10. [ ] Create subfolders `src/card_extraction/`, `src/coverage_qa/`, `src/tool_use/`, `src/voice/greet/`, `src/voice/answer/`.
11. [ ] Each subfolder gets a `prompt.ts` (typed export) and `README.md` (rationale + changelog).
12. [ ] Add 2-3 stub prompts as proof-of-shape.

### Wire up
13. [ ] Add the packages to root `pnpm-workspace.yaml` (already there) and `pyproject.toml` workspace members.
14. [ ] Demonstrate one service importing from both.
15. [ ] Commit with message `feat(packages): shared-logging and shared-prompts packages`.

