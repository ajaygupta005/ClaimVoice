import { Langfuse } from 'langfuse'

let client: Langfuse | null = null

export function getLangfuse(): Langfuse {
  if (!client) {
    client = new Langfuse({
      publicKey: process.env.LANGFUSE_PUBLIC_KEY ?? '',
      secretKey: process.env.LANGFUSE_SECRET_KEY ?? '',
      baseUrl: process.env.LANGFUSE_HOST ?? 'http://localhost:3001',
    })
  }
  return client
}
