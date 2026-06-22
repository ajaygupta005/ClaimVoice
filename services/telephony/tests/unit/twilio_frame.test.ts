import { describe, it, expect } from 'vitest'
import { pcm16ToTwilioFrame } from '../../src/twilio_ws/handler'

describe('pcm16ToTwilioFrame', () => {
  it('produces a valid Twilio media frame with a base64 payload', () => {
    const pcm = Buffer.alloc(48) // 24 PCM16 samples at 24 kHz
    for (let i = 0; i < 24; i++) pcm.writeInt16LE(i * 100, i * 2)
    const frame = pcm16ToTwilioFrame('SM123', pcm)
    const parsed = JSON.parse(frame)
    expect(parsed.event).toBe('media')
    expect(parsed.streamSid).toBe('SM123')
    expect(typeof parsed.media.payload).toBe('string')
    // payload must be valid base64 (round-trips)
    const decoded = Buffer.from(parsed.media.payload, 'base64')
    expect(decoded.length).toBeGreaterThan(0)
  })

  it('downsamples 24 kHz to 8 kHz so the payload is ~1/3 the sample count', () => {
    const pcm = Buffer.alloc(48) // 24 samples
    const frame = pcm16ToTwilioFrame('SM1', pcm)
    const ulaw = Buffer.from(JSON.parse(frame).media.payload, 'base64')
    // 24 samples @24k -> 8 samples @8k -> 8 mu-law bytes
    expect(ulaw.length).toBe(8)
  })
})
