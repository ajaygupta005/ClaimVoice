import { describe, it, expect } from 'vitest'
import { ulawToPcm16, pcm16ToUlaw } from '../../src/audio_codec/ulaw'

describe('ulaw codec', () => {
  it('decode produces 2x output length', () => {
    const ulaw = Buffer.from([0xff, 0x7f, 0x00])
    const pcm = ulawToPcm16(ulaw)
    expect(pcm.length).toBe(6)
  })

  it('encode produces 0.5x output length', () => {
    const pcm = Buffer.alloc(8)
    pcm.writeInt16LE(0, 0)
    pcm.writeInt16LE(1000, 2)
    pcm.writeInt16LE(-1000, 4)
    pcm.writeInt16LE(32767, 6)
    const ulaw = pcm16ToUlaw(pcm)
    expect(ulaw.length).toBe(4)
  })

  it('round trip preserves zero', () => {
    const pcm = Buffer.alloc(2)
    pcm.writeInt16LE(0, 0)
    const back = ulawToPcm16(pcm16ToUlaw(pcm))
    expect(Math.abs(back.readInt16LE(0))).toBeLessThan(200)
  })

  // Regression guard for the G.711 exponent off-by-one. Standard mu-law
  // encodes 0 to 0xFF and full-scale positive to 0x80.
  it('encodes known reference values per G.711', () => {
    const enc = (v: number) => {
      const b = Buffer.alloc(2)
      b.writeInt16LE(v, 0)
      return pcm16ToUlaw(b)[0]
    }
    expect(enc(0)).toBe(0xff)
    expect(enc(32767)).toBe(0x80)
    expect(enc(-32768)).toBe(0x00)
  })

  it('round trip stays close for mid-scale samples', () => {
    for (const v of [-8000, -1000, 500, 4000, 16000, 30000]) {
      const b = Buffer.alloc(2)
      b.writeInt16LE(v, 0)
      const back = ulawToPcm16(pcm16ToUlaw(b)).readInt16LE(0)
      // Standard G.711 quantization error is small across the range.
      expect(Math.abs(back - v)).toBeLessThan(200)
    }
  })

  it('decoded values stay within int16 range', () => {
    for (let byte = 0; byte < 256; byte++) {
      const back = ulawToPcm16(Buffer.from([byte])).readInt16LE(0)
      expect(back).toBeGreaterThanOrEqual(-32768)
      expect(back).toBeLessThanOrEqual(32767)
    }
  })
})
