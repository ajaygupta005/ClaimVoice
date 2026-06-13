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
})
