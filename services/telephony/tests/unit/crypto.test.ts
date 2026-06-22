import { describe, it, expect } from 'vitest'
import { randomBytes } from 'node:crypto'
import { encryptRecording, decryptRecording } from '../../src/recording/crypto'

describe('recording crypto', () => {
  it('round trip recovers plaintext', () => {
    const masterKey = randomBytes(32)
    const plaintext = Buffer.from('hello world this is audio')
    const blob = encryptRecording(plaintext, masterKey)
    const back = decryptRecording(blob, masterKey)
    expect(back.toString()).toBe('hello world this is audio')
  })

  it('decryption fails with wrong master key', () => {
    const masterKey = randomBytes(32)
    const wrongKey = randomBytes(32)
    const blob = encryptRecording(Buffer.from('secret'), masterKey)
    expect(() => decryptRecording(blob, wrongKey)).toThrow()
  })

  it('rejects non-32-byte master key', () => {
    expect(() => encryptRecording(Buffer.from('x'), Buffer.alloc(16))).toThrow()
  })

  it('produces different ciphertext for the same plaintext (random key + IV)', () => {
    const masterKey = randomBytes(32)
    const plaintext = Buffer.from('same audio bytes')
    const a = encryptRecording(plaintext, masterKey)
    const b = encryptRecording(plaintext, masterKey)
    expect(a.ciphertext.equals(b.ciphertext)).toBe(false)
    expect(a.wrappedKey.equals(b.wrappedKey)).toBe(false)
    // both still decrypt back to the same plaintext
    expect(decryptRecording(a, masterKey).toString()).toBe('same audio bytes')
    expect(decryptRecording(b, masterKey).toString()).toBe('same audio bytes')
  })

  it('round trips an empty buffer', () => {
    const masterKey = randomBytes(32)
    const blob = encryptRecording(Buffer.alloc(0), masterKey)
    expect(decryptRecording(blob, masterKey).length).toBe(0)
  })
})
