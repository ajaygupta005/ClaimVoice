import twilio from 'twilio'

let cachedClient: ReturnType<typeof twilio> | null = null

function getClient() {
  if (cachedClient) return cachedClient
  const sid = process.env.TWILIO_ACCOUNT_SID
  const token = process.env.TWILIO_AUTH_TOKEN
  if (!sid || !token) throw new Error('Twilio credentials not configured')
  cachedClient = twilio(sid, token)
  return cachedClient
}

export async function placeOutboundCall(opts: {
  to: string
  memberId: string
}): Promise<{ callSid: string; status: string }> {
  const client = getClient()
  const from = process.env.TWILIO_FROM_NUMBER
  if (!from) throw new Error('TWILIO_FROM_NUMBER not configured')

  const baseUrl = process.env.PUBLIC_BASE_URL || 'http://localhost:8005'
  const call = await client.calls.create({
    to: opts.to,
    from,
    url: `${baseUrl}/twilio/voice?memberId=${encodeURIComponent(opts.memberId)}`,
    statusCallback: `${baseUrl}/twilio/status`,
    statusCallbackEvent: ['initiated', 'ringing', 'answered', 'completed'],
  })

  return { callSid: call.sid, status: call.status }
}
