import { z } from 'zod'

const schema = z.object({
  PORT: z.coerce.number().default(8005),
  // Twilio creds are optional in dev (only needed for outbound calls)
  TWILIO_ACCOUNT_SID: z.string().optional(),
  TWILIO_AUTH_TOKEN: z.string().optional(),
  TWILIO_FROM_NUMBER: z.string().optional(),
})

export type Config = z.infer<typeof schema>

export function loadConfig(): Config {
  const parsed = schema.safeParse(process.env)
  if (!parsed.success) {
    console.error('Bad env:', parsed.error.format())
    throw new Error('Invalid telephony config')
  }
  return parsed.data
}
