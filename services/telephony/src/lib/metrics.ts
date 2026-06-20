// Prometheus metrics for the telephony service.
//
// Exposed at GET /metrics (see server.ts). Scraped by Prometheus
// (infra/prometheus/prometheus.yml target telephony:8005). The Grafana
// "Voice Latency" dashboard queries these series.

import { collectDefaultMetrics, Counter, Histogram, Gauge, Registry } from 'prom-client'

export const registry = new Registry()
registry.setDefaultLabels({ service: 'telephony' })

// Node process / GC / event-loop metrics.
collectDefaultMetrics({ register: registry })

// ── Calls ─────────────────────────────────────────────────────────────────────

export const callsTotal = new Counter({
  name: 'telephony_calls_total',
  help: 'Total calls handled, by direction and final status.',
  labelNames: ['direction', 'status'] as const,
  registers: [registry],
})

export const callDurationSeconds = new Histogram({
  name: 'telephony_call_duration_seconds',
  help: 'Media-stream call duration in seconds.',
  labelNames: ['direction'] as const,
  // A member call is usually 30 s – 10 min.
  buckets: [5, 15, 30, 60, 120, 300, 600],
  registers: [registry],
})

export const activeCalls = new Gauge({
  name: 'telephony_active_calls',
  help: 'Number of media streams currently bridged.',
  registers: [registry],
})

// ── Audio throughput ──────────────────────────────────────────────────────────

export const audioBytesTotal = new Counter({
  name: 'telephony_audio_bytes_total',
  help: 'Audio bytes moved through the bridge, by direction.',
  labelNames: ['direction'] as const, // inbound = caller→agent, outbound = agent→caller
  registers: [registry],
})

// ── Recording ─────────────────────────────────────────────────────────────────

export const recordingUploadSeconds = new Histogram({
  name: 'telephony_recording_upload_seconds',
  help: 'Time to encrypt and upload a call recording.',
  buckets: [0.1, 0.25, 0.5, 1, 2, 5, 10],
  registers: [registry],
})

export const recordingsTotal = new Counter({
  name: 'telephony_recordings_total',
  help: 'Recordings uploaded, by outcome.',
  labelNames: ['outcome'] as const, // success | error
  registers: [registry],
})

// ── Outbound API ──────────────────────────────────────────────────────────────

export const outboundCallRequestsTotal = new Counter({
  name: 'telephony_outbound_call_requests_total',
  help: 'POST /api/v1/voice/call requests, by outcome.',
  labelNames: ['outcome'] as const, // placed | rejected | error | rate_limited
  registers: [registry],
})

/** Serialize all metrics in Prometheus text exposition format. */
export async function renderMetrics(): Promise<string> {
  return registry.metrics()
}

export function metricsContentType(): string {
  return registry.contentType
}
