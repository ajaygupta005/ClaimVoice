import { describe, it, expect } from 'vitest'
import {
  registry,
  callsTotal,
  outboundCallRequestsTotal,
  renderMetrics,
  metricsContentType,
} from '../../src/lib/metrics'

describe('telephony metrics', () => {
  it('renders Prometheus text format', async () => {
    const out = await renderMetrics()
    expect(typeof out).toBe('string')
    expect(out).toContain('telephony_calls_total')
  })

  it('content type is the prometheus exposition type', () => {
    expect(metricsContentType()).toContain('text/plain')
  })

  it('counters increment and show up in the registry', async () => {
    callsTotal.inc({ direction: 'inbound', status: 'completed' })
    outboundCallRequestsTotal.inc({ outcome: 'placed' })
    const out = await renderMetrics()
    expect(out).toMatch(/telephony_calls_total\{[^}]*direction="inbound"/)
    expect(out).toMatch(/telephony_outbound_call_requests_total\{[^}]*outcome="placed"/)
  })

  it('default labels include the service name', async () => {
    const out = await renderMetrics()
    expect(out).toContain('service="telephony"')
  })

  it('registry exposes default process metrics', () => {
    const names = registry.getMetricsAsArray().map((m) => m.name)
    expect(names).toContain('telephony_calls_total')
    expect(names).toContain('telephony_call_duration_seconds')
    expect(names).toContain('telephony_active_calls')
  })
})
