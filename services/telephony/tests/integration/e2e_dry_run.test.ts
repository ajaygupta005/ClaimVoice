// End-to-end dry run for the telephony service.
//
// Boots the real Fastify app in-process and exercises the HTTP surface:
//   - GET  /health         → 200
//   - GET  /metrics        → 200, prometheus text
//   - POST /twilio/voice   → 200, valid TwiML with a <Stream> URL
//   - POST /api/v1/voice/call (bad body) → 400
//   - rate limit: 6th outbound call within the window → 429
//
// A *real* outbound phone call is only attempted when DRY_RUN_REAL_CALL=1 and
// Twilio creds + DRY_RUN_TO are set. That part is skipped in CI.

import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import Fastify, { type FastifyInstance } from 'fastify'
import formbody from '@fastify/formbody'
import rateLimit from '@fastify/rate-limit'
import { voiceRoute, statusRoute } from '../../src/twilio/voice'
import { registerCallApi } from '../../src/api/v1/call'
import { renderMetrics, metricsContentType } from '../../src/lib/metrics'

async function buildApp(): Promise<FastifyInstance> {
  const app = Fastify({ logger: false })
  await app.register(formbody)
  await app.register(rateLimit, { global: false, max: 5, timeWindow: '1 minute' })
  app.get('/health', async () => ({ status: 'ok' }))
  app.get('/metrics', async (_req, reply) => {
    reply.header('Content-Type', metricsContentType())
    return renderMetrics()
  })
  app.post('/twilio/voice', voiceRoute)
  app.post('/twilio/status', statusRoute)
  registerCallApi(app)
  await app.ready()
  return app
}

describe('telephony e2e dry run', () => {
  let app: FastifyInstance

  beforeAll(async () => {
    app = await buildApp()
  })

  afterAll(async () => {
    await app.close()
  })

  it('GET /health returns ok', async () => {
    const res = await app.inject({ method: 'GET', url: '/health' })
    expect(res.statusCode).toBe(200)
    expect(res.json()).toEqual({ status: 'ok' })
  })

  it('GET /metrics returns prometheus text', async () => {
    const res = await app.inject({ method: 'GET', url: '/metrics' })
    expect(res.statusCode).toBe(200)
    expect(res.body).toContain('telephony_')
  })

  it('POST /twilio/voice returns TwiML with a Stream URL', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/twilio/voice',
      payload: { From: '+12125551234', To: '+18005550000', CallSid: 'CA-test' },
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
    })
    expect(res.statusCode).toBe(200)
    expect(res.headers['content-type']).toContain('xml')
    expect(res.body).toContain('<Response>')
    expect(res.body).toContain('<Stream')
  })

  it('POST /api/v1/voice/call with a bad body returns 400', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/api/v1/voice/call',
      payload: { to: 'not-a-phone', memberId: '' },
    })
    expect(res.statusCode).toBe(400)
  })

  it('rate limits outbound calls after 5 in the window', async () => {
    // No Twilio creds in CI, so each call 500s, but the rate limiter still
    // counts attempts. The 6th attempt should be 429.
    const codes: number[] = []
    for (let i = 0; i < 6; i++) {
      const res = await app.inject({
        method: 'POST',
        url: '/api/v1/voice/call',
        payload: { to: '+12125551234', memberId: 'M1' },
      })
      codes.push(res.statusCode)
    }
    expect(codes[codes.length - 1]).toBe(429)
  })

  // Real outbound call — only when explicitly enabled.
  const realCall = process.env.DRY_RUN_REAL_CALL === '1'
  it.skipIf(!realCall)('places a real outbound call', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/api/v1/voice/call',
      payload: { to: process.env.DRY_RUN_TO, memberId: 'DRYRUN' },
    })
    expect(res.statusCode).toBe(200)
    expect(res.json()).toHaveProperty('callSid')
  })
})
