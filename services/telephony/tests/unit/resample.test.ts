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

  it('empty buffer returns empty', () => {
    expect(resamplePcm16(Buffer.alloc(0), 8000, 24000).length).toBe(0)
  })

  it('ignores a trailing odd byte instead of reading past the end', () => {
    // 5 bytes = 2 whole samples + 1 stray byte.
    const buf = Buffer.alloc(5)
    buf.writeInt16LE(1000, 0)
    buf.writeInt16LE(-1000, 2)
    const out = resamplePcm16(buf, 8000, 24000)
    // 2 input samples upsampled 3x = 6 output samples, no crash.
    expect(out.length / 2).toBe(6)
  })
})
