# Observability

We use OpenTelemetry for general tracing and Langfuse specifically for LLM calls.

## OTel

Every service calls `setup_tracer(service_name)` at startup. By default spans
are printed to stdout (good for dev). Set `OTEL_EXPORTER_OTLP_ENDPOINT` to
send spans to a collector.

## Langfuse

Wrap any anthropic.messages.create call with `@observe_anthropic("name")`.
Token usage and cost are recorded automatically.

## Correlation IDs

Coming from the API gateway via `X-Correlation-ID` header. Each service should
read it and bind it to the logger context. (See shared-logging.)
