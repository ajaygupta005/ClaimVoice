import { z } from 'zod'

const schema = z.object({
  PORT: z.coerce.number().default(8005),
  TWILIO_ACCOUNT_SID: z.string().optional(),
  TWILIO_AUTH_TOKEN: z.string().optional(),
  TWILIO_FROM_NUMBER: z.string().optional(),
  PUBLIC_BASE_URL: z.string().optional(),
  S3_ENDPOINT: z.string().optional(),
  S3_BUCKET: z.string().optional(),
  S3_ACCESS_KEY: z.string().optional(),
  S3_SECRET_KEY: z.string().optional(),
  MASTER_KEY_HEX: z.string().optional(),
  VOICE_AGENT_WS_URL: z.string().optional(),
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
