// G.711 mu-law codec. Twilio sends 8 kHz mu-law audio over Media Streams.
// We decode to PCM16 to feed the voice agent, and encode back for outbound.

const ULAW_DECODE = new Int16Array(256)
for (let i = 0; i < 256; i++) {
  let u = ~i & 0xff
  const sign = u & 0x80 ? -1 : 1
  const exp = (u >> 4) & 0x07
  const mant = u & 0x0f
  const val = ((mant << 4) + 0x08) << (exp + 3)
  ULAW_DECODE[i] = sign * (val - 0x84)
}

export function ulawToPcm16(buf: Buffer): Buffer {
  const out = Buffer.alloc(buf.length * 2)
  for (let i = 0; i < buf.length; i++) {
    out.writeInt16LE(ULAW_DECODE[buf[i]], i * 2)
  }
  return out
}

const ULAW_BIAS = 0x84
const ULAW_CLIP = 32635

export function pcm16ToUlaw(buf: Buffer): Buffer {
  const out = Buffer.alloc(buf.length / 2)
  for (let i = 0; i < out.length; i++) {
    let sample = buf.readInt16LE(i * 2)
    const sign = (sample >> 8) & 0x80
    if (sign !== 0) sample = -sample
    if (sample > ULAW_CLIP) sample = ULAW_CLIP
    sample += ULAW_BIAS
    // Find the exponent = position of the highest set bit at or above bit 7.
    let exponent = 7
    for (let mask = 0x4000; (sample & mask) === 0 && exponent > 0; exponent--, mask >>= 1) {
      /* shift down until we hit the leading 1 */
    }
    const mantissa = (sample >> (exponent + 3)) & 0x0f
    out[i] = ~(sign | (exponent << 4) | mantissa) & 0xff
  }
  return out
}
