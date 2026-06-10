import Fastify from 'fastify'
import formbody from '@fastify/formbody'
import { loadConfig } from './lib/config.js'
import { voiceRoute, statusRoute } from './twilio/voice.js'

const config = loadConfig()

const app = Fastify({
  logger: {
    level: 'info',
    base: { service: 'telephony' },
  },
})

await app.register(formbody) // Twilio sends application/x-www-form-urlencoded

app.get('/health', async () => ({ status: 'ok' }))

app.post('/twilio/voice', voiceRoute)
app.post('/twilio/status', statusRoute)

try {
  await app.listen({ port: config.PORT, host: '0.0.0.0' })
} catch (err) {
  app.log.error(err)
  process.exit(1)
}
