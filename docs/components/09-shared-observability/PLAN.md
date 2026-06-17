# Component 09 - Shared Observability Package (OTel + Langfuse) - Implementation Plan

> Step-by-step. Check off as you go.

1. [ ] Build `packages/shared-observability/python/tracing.py` with OTel SDK setup (OTLP exporter to localhost:4317).
2. [ ] Build `packages/shared-observability/python/langfuse_client.py` wrapping `langfuse.Langfuse()`.
3. [ ] Implement the `@observe_anthropic` decorator that creates a Langfuse generation span around `messages.create`.
4. [ ] Implement correlation-ID propagation from `X-Correlation-ID` header into spans.
5. [ ] Mirror in Node (`packages/shared-observability/node/`): `tracing.ts`, `langfuse_client.ts`.
6. [ ] Author `docs/observability.md` documenting what's traced and how to add spans.
7. [ ] Demonstrate first usage from `services/document-ai/main.py` (or wherever the first Anthropic call lives).
8. [ ] Commit with message `feat(packages): shared-observability with otel and langfuse client`.

