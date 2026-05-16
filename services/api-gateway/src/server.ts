import Fastify from 'fastify'
import cors from '@fastify/cors'
import rateLimit from '@fastify/rate-limit'

const app = Fastify({ logger: true })
await app.register(cors, { origin: true })
await app.register(rateLimit, { max: 100, timeWindow: '1 minute' })

app.get('/health', async () => ({ status: 'ok' }))

app.listen({ port: 8080, host: '0.0.0.0' })
