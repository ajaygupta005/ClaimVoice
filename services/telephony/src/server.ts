import Fastify from 'fastify'
const app = Fastify({ logger: true })
app.get('/health', async () => ({ status: 'ok' }))
app.listen({ port: 8005, host: '0.0.0.0' })
