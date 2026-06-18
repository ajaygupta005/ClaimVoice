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

The telephony service does this in an `onRequest` hook: it reuses an incoming
`X-Correlation-ID` or mints a UUID, echoes it back in the response header, and
binds it to the per-request logger.

## Prometheus metrics

Prometheus scrapes each service's `/metrics` endpoint (targets in
`infra/prometheus/prometheus.yml`). Grafana dashboards live in
`infra/grafana/dashboards/`.

The telephony service exposes these series at `GET /metrics`:

| Metric | Type | Meaning |
| --- | --- | --- |
| `telephony_calls_total` | counter | calls handled, by direction and status |
| `telephony_call_duration_seconds` | histogram | media-stream call duration |
| `telephony_active_calls` | gauge | calls currently bridged |
| `telephony_audio_bytes_total` | counter | audio bytes, by direction |
| `telephony_recording_upload_seconds` | histogram | encrypt + upload time |
| `telephony_recordings_total` | counter | recordings, by outcome |
| `telephony_outbound_call_requests_total` | counter | outbound API calls, by outcome |

The "Voice / Telephony" Grafana dashboard reads these directly.
