# Component 04 - Shared Logging + Prompts - Results

## Checklist
- [ ] Python logger emits JSON matching the schema
- [ ] Node logger emits the same shape
- [ ] PII fields get redacted
- [ ] `pnpm install` picks up the new TS packages

## Files in this commit
- `packages/shared-logging/python/` (loguru)
- `packages/shared-logging/node/` (pino)
- `packages/shared-prompts/` (Claude prompts)
- `docs/logging.md`

## Commit
```
git add packages/shared-logging/ packages/shared-prompts/ docs/logging.md tests/packages/ docs/components/04-shared-logging-and-prompts/
git commit -m "feat(packages): shared logging and prompts packages"
```
