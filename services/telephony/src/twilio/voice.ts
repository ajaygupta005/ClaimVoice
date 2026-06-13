import type { FastifyRequest, FastifyReply } from 'fastify'
import { consentTwiml } from '../recording/consent.js'

interface TwilioVoiceBody {
  CallSid?: string
  From?: string
  To?: string
}

// Inbound: Twilio dials our webhook when a call comes in. We respond with
// TwiML that plays a greeting, optionally announces recording, and connects
// to the Media Streams bridge.
export async function voiceRoute(req: FastifyRequest, reply: FastifyReply) {
  const body = (req.body as TwilioVoiceBody) || {}
  const consent = consentTwiml(body.From || '')

  const host = (req.headers['x-forwarded-host'] as string) || req.headers.host || 'localhost:8005'
  const proto = (req.headers['x-forwarded-proto'] as string) === 'https' ? 'wss' : 'ws'
  const streamUrl = `${proto}://${host}/media-stream`

  reply.type('text/xml')
  return `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  ${consent}
  <Say voice="alice">Hello, this is ClaimVoice. How can I help you today?</Say>
  <Connect>
    <Stream url="${streamUrl}" />
  </Connect>
</Response>`
}

// Twilio call status webhook. Updates whatever we track for the call.
export async function statusRoute(req: FastifyRequest, reply: FastifyReply) {
  const body = req.body as { CallSid?: string; CallStatus?: string }
  req.log.info({
    event: 'twilio.status',
    CallSid: body.CallSid,
    CallStatus: body.CallStatus,
  })
  reply.code(200).send()
}
