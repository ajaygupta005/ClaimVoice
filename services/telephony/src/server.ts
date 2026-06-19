import Fastify, { type FastifyError } from 'fastify'
import formbody from '@fastify/formbody'
import websocket from '@fastify/websocket'
import rateLimit from '@fastify/rate-limit'
import { randomUUID } from 'node:crypto'
import { loadConfig } from './lib/config.js'
import { voiceRoute, statusRoute } from './twilio/voice.js'
import { registerMediaStreamHandler } from './twilio_ws/handler.js'
import { registerCallApi } from './api/v1/call.js'
import { renderMetrics, metricsContentType, outboundCallRequestsTotal } from './lib/metrics.js'

const config = loadConfig()

const app = Fastify({
  logger: {
    level: 'info',
    base: { service: 'telephony' },
  },
})

await app.register(formbody)
await app.register(websocket)

// Correlation IDs: reuse an incoming X-Correlation-ID or mint one, echo it
// back, and bind it to the per-request logger (matches the logging contract).
app.addHook('onRequest', async (request, reply) => {
  const cid = (request.headers['x-correlation-id'] as string) || randomUUID()
  reply.header('x-correlation-id', cid)
  request.log = request.log.child({ correlation_id: cid })
})

// Rate limiting is opt-in per route (global: false). Twilio webhooks must NOT
// be limited — Twilio can burst. Only /api/v1/voice/call opts in (see call.ts).
await app.register(rateLimit, {
  global: false,
  max: 5,
  timeWindow: '1 minute',
})

// Count rate-limited outbound-call attempts.
app.setErrorHandler((error: FastifyError, request, reply) => {
  if (error.statusCode === 429 && request.url.startsWith('/api/v1/voice/call')) {
    outboundCallRequestsTotal.inc({ outcome: 'rate_limited' })
  }
  reply.send(error)
})

const startedAt = Date.now()
app.get('/health', async () => ({
  status: 'ok',
  service: 'telephony',
  uptime_s: Math.round((Date.now() - startedAt) / 1000),
}))

app.get('/metrics', async (_request, reply) => {
  reply.header('Content-Type', metricsContentType())
  return renderMetrics()
})

app.post('/twilio/voice', voiceRoute)
app.post('/twilio/status', statusRoute)

registerMediaStreamHandler(app)
registerCallApi(app)

// Close the server cleanly on container stop so in-flight calls drain.
for (const signal of ['SIGTERM', 'SIGINT'] as const) {
  process.on(signal, () => {
    app.log.info({ event: 'shutdown', signal })
    app.close().then(() => process.exit(0))
  })
}

try {
  await app.listen({ port: config.PORT, host: '0.0.0.0' })
} catch (err) {
  app.log.error(err)
  process.exit(1)
}
