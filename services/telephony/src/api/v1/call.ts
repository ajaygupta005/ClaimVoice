import type { FastifyInstance } from 'fastify'
import { z } from 'zod'
import { placeOutboundCall } from '../../twilio/outbound.js'

const PlaceCallSchema = z.object({
  to: z.string().regex(/^\+?\d{10,15}$/, 'invalid phone'),
  memberId: z.string().min(1),
})

export function registerCallApi(app: FastifyInstance) {
  app.post('/api/v1/voice/call', async (request, reply) => {
    const parsed = PlaceCallSchema.safeParse(request.body)
    if (!parsed.success) {
      reply.code(400)
      return { error: parsed.error.format() }
    }

    try {
      const result = await placeOutboundCall(parsed.data)
      return result
    } catch (err) {
      request.log.error({ err })
      reply.code(500)
      return { error: err instanceof Error ? err.message : 'Call failed' }
    }
  })
}
