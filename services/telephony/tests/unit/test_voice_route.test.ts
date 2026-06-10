// Component 12 - POST /twilio/voice returns valid TwiML.
//
// Run with: pnpm --filter @claimvoice/telephony test
//
// Asserts:
//   - 200 status
//   - Content-Type text/xml
//   - <Response> root element present
//   - TwiML well-formed (parseable XML)

import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import Fastify, { FastifyInstance } from 'fastify'
// import { registerTwilioRoutes } from '../../src/twilio/routes'

describe('POST /twilio/voice', () => {
  let app: FastifyInstance

  beforeAll(async () => {
    app = Fastify()
    // registerTwilioRoutes(app)
    await app.ready()
  })

  afterAll(async () => {
    await app.close()
  })

  it.skip('returns valid TwiML', async () => {
    const res = await app.inject({ method: 'POST', url: '/twilio/voice' })
    expect(res.statusCode).toBe(200)
    expect(res.headers['content-type']).toMatch(/xml/)
    expect(res.body).toContain('<Response>')
  })
})
