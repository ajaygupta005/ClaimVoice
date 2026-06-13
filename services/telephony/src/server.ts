import Fastify from 'fastify'
import formbody from '@fastify/formbody'
import websocket from '@fastify/websocket'
import { loadConfig } from './lib/config.js'
import { voiceRoute, statusRoute } from './twilio/voice.js'
import { registerMediaStreamHandler } from './twilio_ws/handler.js'
import { registerCallApi } from './api/v1/call.js'

const config = loadConfig()

const app = Fastify({
  logger: {
    level: 'info',
    base: { service: 'telephony' },
  },
})

await app.register(formbody)
await app.register(websocket)

app.get('/health', async () => ({ status: 'ok' }))

app.post('/twilio/voice', voiceRoute)
app.post('/twilio/status', statusRoute)

registerMediaStreamHandler(app)
registerCallApi(app)

try {
  await app.listen({ port: config.PORT, host: '0.0.0.0' })
} catch (err) {
  app.log.error(err)
  process.exit(1)
}
