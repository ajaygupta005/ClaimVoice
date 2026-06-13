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

export function pcm16ToUlaw(buf: Buffer): Buffer {
  const out = Buffer.alloc(buf.length / 2)
  for (let i = 0; i < out.length; i++) {
    let s = buf.readInt16LE(i * 2)
    const sign = s < 0 ? 0x80 : 0
    if (s < 0) s = -s
    s += 0x84
    if (s > 0x7fff) s = 0x7fff
    let exp = 0
    while (s >= 0x0080 << exp) exp++
    if (exp > 7) exp = 7
    const mant = (s >> (exp + 3)) & 0x0f
    out[i] = ~(sign | (exp << 4) | mant) & 0xff
  }
  return out
}
