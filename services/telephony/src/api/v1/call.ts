import type { FastifyInstance } from 'fastify'
import { z } from 'zod'
import { placeOutboundCall } from '../../twilio/outbound.js'
import { outboundCallRequestsTotal } from '../../lib/metrics.js'

const PlaceCallSchema = z.object({
  to: z.string().regex(/^\+?\d{10,15}$/, 'invalid phone'),
  memberId: z.string().min(1),
})

export function registerCallApi(app: FastifyInstance) {
  app.post(
    '/api/v1/voice/call',
    {
      // Rate limit only this route. Outbound dialing is sensitive (cost + TCPA),
      // so cap it. Twilio webhooks are NOT rate limited (global: false in server.ts).
      config: {
        rateLimit: {
          max: 5,
          timeWindow: '1 minute',
        },
      },
    },
    async (request, reply) => {
      const parsed = PlaceCallSchema.safeParse(request.body)
      if (!parsed.success) {
        outboundCallRequestsTotal.inc({ outcome: 'rejected' })
        reply.code(400)
        return { error: parsed.error.format() }
      }

      try {
        const result = await placeOutboundCall(parsed.data)
        outboundCallRequestsTotal.inc({ outcome: 'placed' })
        return result
      } catch (err) {
        outboundCallRequestsTotal.inc({ outcome: 'error' })
        request.log.error({ err })
        reply.code(500)
        return { error: err instanceof Error ? err.message : 'Call failed' }
      }
    },
  )
}
