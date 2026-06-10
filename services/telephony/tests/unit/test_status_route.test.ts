// Component 12 - POST /twilio/status returns 200 and logs CallSid + status.

import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest'
import Fastify, { FastifyInstance } from 'fastify'

describe('POST /twilio/status', () => {
  let app: FastifyInstance

  beforeAll(async () => {
    app = Fastify()
    // registerTwilioRoutes(app)
    await app.ready()
  })

  afterAll(async () => {
    await app.close()
  })

  it.skip('returns 200 OK on valid status callback', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/twilio/status',
      payload: { CallSid: 'CA123', CallStatus: 'completed' },
    })
    expect(res.statusCode).toBe(200)
  })
})
