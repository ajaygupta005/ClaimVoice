# Component 09 - Shared Observability Package (OTel + Langfuse) - Research

> Alternatives considered, decisions made, references.

## OpenTelemetry vs vendor-specific tracing
- OTel is the CNCF standard. Vendor-neutral; export the same spans to Langfuse, Jaeger, Honeycomb, Datadog without changing instrumentation code.
- Worth the slight complexity over a single-vendor SDK.

## Decorator pattern vs middleware
- Decorators are the simplest API for ad-hoc instrumentation in long-running handlers.
- Middleware handles framework-level instrumentation (we get that for free from Fastify and FastAPI plugins).

## Why Langfuse-only for LLM observability
- LLM-specific concerns (token counts, prompt versions, cost attribution) need a tool that knows about them.
- Generic OTel spans don't capture cost well.

## References
- OpenTelemetry Python: https://opentelemetry.io/docs/instrumentation/python/
- OpenTelemetry JS: https://opentelemetry.io/docs/instrumentation/js/
- Langfuse decorators: https://langfuse.com/docs/sdk/python/decorators

