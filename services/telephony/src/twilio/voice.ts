import type { FastifyRequest, FastifyReply } from 'fastify'

export async function voiceRoute(req: FastifyRequest, reply: FastifyReply) {
  // Twilio sends a POST to this URL when a call comes in.
  // We respond with TwiML that plays a greeting and (later) bridges to
  // the voice-agent over Media Streams.
  reply.type('text/xml')
  return `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice">Hello, this is ClaimVoice. We will connect you to an agent shortly.</Say>
  <Pause length="1"/>
</Response>`
}

export async function statusRoute(req: FastifyRequest, reply: FastifyReply) {
  // Twilio calls this with call status updates (ringing, completed, etc).
  const body = req.body as { CallSid?: string; CallStatus?: string }
  req.log.info({
    event: 'twilio.status',
    CallSid: body.CallSid,
    CallStatus: body.CallStatus,
  })
  reply.code(200).send()
}
