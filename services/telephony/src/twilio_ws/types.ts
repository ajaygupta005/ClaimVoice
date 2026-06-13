// Twilio Media Streams frame shapes.
// https://www.twilio.com/docs/voice/twiml/stream

export interface TwilioStartFrame {
  event: 'start'
  sequenceNumber: string
  start: {
    streamSid: string
    accountSid: string
    callSid: string
    tracks: string[]
    mediaFormat: { encoding: string; sampleRate: number; channels: number }
  }
  streamSid: string
}

export interface TwilioMediaFrame {
  event: 'media'
  sequenceNumber: string
  media: { track: string; chunk: string; timestamp: string; payload: string }
  streamSid: string
}

export interface TwilioStopFrame {
  event: 'stop'
  sequenceNumber: string
  stop: { accountSid: string; callSid: string }
  streamSid: string
}

export type TwilioFrame = TwilioStartFrame | TwilioMediaFrame | TwilioStopFrame

export interface StreamState {
  streamSid: string
  callSid: string
  startedAt: number
  bytesIn: number
  bytesOut: number
}
