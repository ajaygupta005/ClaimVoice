# Component 09 - Shared Observability - Results

## Checklist
- [ ] `setup_tracer` produces a span visible in the console exporter
- [ ] `@observe_anthropic` decorator records a Langfuse trace
- [ ] Same in Node

## Files in this commit
- `packages/shared-observability/python/` (OTel + Langfuse decorator)
- `packages/shared-observability/node/`
- `docs/observability.md`
- `.env.example` (added ANTHROPIC_API_KEY)

## Commit
```
git add packages/shared-observability/ docs/observability.md .env.example tests/packages/test_otel_tracer_emits_span.py tests/packages/test_langfuse_observe_decorator.py tests/packages/test_correlation_id_in_span.py docs/components/09-shared-observability/
git commit -m "feat(packages): shared observability with otel and langfuse"
```
