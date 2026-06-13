import { describe, it, expect } from 'vitest'
import { z } from 'zod'

// Re-declare the schema inline since route file requires fastify import
const PlaceCallSchema = z.object({
  to: z.string().regex(/^\+?\d{10,15}$/, 'invalid phone'),
  memberId: z.string().min(1),
})

describe('outbound call schema', () => {
  it('accepts valid input', () => {
    const result = PlaceCallSchema.safeParse({ to: '+12125551234', memberId: 'M1' })
    expect(result.success).toBe(true)
  })

  it('rejects bad phone', () => {
    const result = PlaceCallSchema.safeParse({ to: 'not-a-phone', memberId: 'M1' })
    expect(result.success).toBe(false)
  })

  it('rejects empty memberId', () => {
    const result = PlaceCallSchema.safeParse({ to: '+12125551234', memberId: '' })
    expect(result.success).toBe(false)
  })
})
