// Component 12 - GET /health returns { status: "ok" }.

import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import Fastify, { FastifyInstance } from 'fastify'

describe('GET /health', () => {
  let app: FastifyInstance

  beforeAll(async () => {
    app = Fastify()
    app.get('/health', async () => ({ status: 'ok' }))
    await app.ready()
  })

  afterAll(async () => {
    await app.close()
  })

  it('returns 200 OK with status ok', async () => {
    const res = await app.inject({ method: 'GET', url: '/health' })
    expect(res.statusCode).toBe(200)
    expect(JSON.parse(res.body)).toEqual({ status: 'ok' })
  })
})
