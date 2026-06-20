import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import Fastify, { type FastifyInstance } from 'fastify'
import formbody from '@fastify/formbody'
import { voiceRoute } from '../../src/twilio/voice'

async function buildApp(): Promise<FastifyInstance> {
  const app = Fastify({ logger: false })
  await app.register(formbody)
  app.post('/twilio/voice', voiceRoute)
  await app.ready()
  return app
}

async function twimlFor(app: FastifyInstance, from: string): Promise<string> {
  const res = await app.inject({
    method: 'POST',
    url: '/twilio/voice',
    payload: { From: from, To: '+18005550000', CallSid: 'CA-test' },
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
  })
  expect(res.statusCode).toBe(200)
  return res.body
}

describe('consent flow in inbound TwiML', () => {
  let app: FastifyInstance

  beforeAll(async () => {
    app = await buildApp()
  })

  afterAll(async () => {
    await app.close()
  })

  it('includes the recording notice for a two-party-consent state (CA)', async () => {
    const twiml = await twimlFor(app, '+14155550100')
    expect(twiml).toContain('recorded')
    expect(twiml).toContain('<Stream')
  })

  it('omits the recording notice for a one-party-consent state (TX)', async () => {
    const twiml = await twimlFor(app, '+12145550100')
    expect(twiml).not.toContain('recorded')
    expect(twiml).toContain('<Stream')
  })

  it('plays the notice when the caller state is unknown (safer default)', async () => {
    const twiml = await twimlFor(app, '+19995550100')
    expect(twiml).toContain('recorded')
  })
})
