// Linear-interpolation resample between PCM16 sample rates.
// Used to go 8 kHz <-> 24 kHz between Twilio and the voice agent.

export function resamplePcm16(buf: Buffer, fromRate: number, toRate: number): Buffer {
  if (fromRate === toRate) return buf
  // PCM16 is 2 bytes per sample; ignore a trailing odd byte rather than
  // reading past the end of the buffer.
  const inSamples = Math.floor(buf.length / 2)
  if (inSamples === 0) return Buffer.alloc(0)
  const ratio = toRate / fromRate
  const outSamples = Math.floor(inSamples * ratio)
  const out = Buffer.alloc(outSamples * 2)

  for (let i = 0; i < outSamples; i++) {
    const srcF = i / ratio
    const srcI = Math.floor(srcF)
    const frac = srcF - srcI
    const s0 = srcI < inSamples ? buf.readInt16LE(srcI * 2) : 0
    const s1 = srcI + 1 < inSamples ? buf.readInt16LE((srcI + 1) * 2) : 0
    const interp = Math.round(s0 + (s1 - s0) * frac)
    out.writeInt16LE(Math.max(-32768, Math.min(32767, interp)), i * 2)
  }
  return out
}
