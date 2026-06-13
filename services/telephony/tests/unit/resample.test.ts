import { describe, it, expect } from 'vitest'
import { resamplePcm16 } from '../../src/audio_codec/resample'

describe('resample', () => {
  it('same rate returns same buffer', () => {
    const buf = Buffer.alloc(20)
    expect(resamplePcm16(buf, 8000, 8000)).toBe(buf)
  })

  it('upsample 8k to 24k triples sample count', () => {
    const samples = 100
    const buf = Buffer.alloc(samples * 2)
    for (let i = 0; i < samples; i++) buf.writeInt16LE(i, i * 2)
    const out = resamplePcm16(buf, 8000, 24000)
    expect(out.length / 2).toBe(samples * 3)
  })

  it('downsample 24k to 8k thirds sample count', () => {
    const samples = 300
    const buf = Buffer.alloc(samples * 2)
    const out = resamplePcm16(buf, 24000, 8000)
    expect(out.length / 2).toBe(samples / 3)
  })
})
