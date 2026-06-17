# Component 11 - Integration CI + ADR - Results

## Checklist
- [ ] Push to main triggers integration workflow
- [ ] Workflow goes green
- [ ] ADR-0002 reads as standalone rationale

## Files in this commit
- `.github/workflows/integration.yml`
- `docs/adr/0002-claude-over-gpt.md`

## Commit
```
git add .github/workflows/integration.yml docs/adr/0002-claude-over-gpt.md tests/ci/test_integration_workflow_valid.py tests/docs/test_adr_0002_structure.py docs/components/11-integration-ci-and-adr/
git commit -m "chore(ci): add integration tests workflow and adr-0002"
```
