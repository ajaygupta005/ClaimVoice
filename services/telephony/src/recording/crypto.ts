// Encrypt recordings with AES-256-GCM. Per-call random key, wrapped under
// per-tenant master key. Plaintext (decrypted) never persisted.

import { createCipheriv, createDecipheriv, randomBytes } from 'node:crypto'

const ALGO = 'aes-256-gcm'
const IV_LEN = 12
const KEY_LEN = 32

export interface EncryptedBlob {
  ciphertext: Buffer  // iv || ciphertext || authTag
  wrappedKey: Buffer  // iv || wrappedKey || authTag
}

export function encryptRecording(plaintext: Buffer, masterKey: Buffer): EncryptedBlob {
  if (masterKey.length !== KEY_LEN) throw new Error('master key must be 32 bytes')

  // 1. Generate per-call key
  const callKey = randomBytes(KEY_LEN)

  // 2. Encrypt plaintext with call key
  const iv1 = randomBytes(IV_LEN)
  const c1 = createCipheriv(ALGO, callKey, iv1)
  const ct1 = Buffer.concat([c1.update(plaintext), c1.final()])
  const tag1 = c1.getAuthTag()
  const ciphertext = Buffer.concat([iv1, ct1, tag1])

  // 3. Wrap the call key with the master key
  const iv2 = randomBytes(IV_LEN)
  const c2 = createCipheriv(ALGO, masterKey, iv2)
  const ct2 = Buffer.concat([c2.update(callKey), c2.final()])
  const tag2 = c2.getAuthTag()
  const wrappedKey = Buffer.concat([iv2, ct2, tag2])

  return { ciphertext, wrappedKey }
}

export function decryptRecording(blob: EncryptedBlob, masterKey: Buffer): Buffer {
  // Unwrap call key
  const iv2 = blob.wrappedKey.subarray(0, IV_LEN)
  const tag2 = blob.wrappedKey.subarray(blob.wrappedKey.length - 16)
  const ct2 = blob.wrappedKey.subarray(IV_LEN, blob.wrappedKey.length - 16)
  const d2 = createDecipheriv(ALGO, masterKey, iv2)
  d2.setAuthTag(tag2)
  const callKey = Buffer.concat([d2.update(ct2), d2.final()])

  // Decrypt plaintext
  const iv1 = blob.ciphertext.subarray(0, IV_LEN)
  const tag1 = blob.ciphertext.subarray(blob.ciphertext.length - 16)
  const ct1 = blob.ciphertext.subarray(IV_LEN, blob.ciphertext.length - 16)
  const d1 = createDecipheriv(ALGO, callKey, iv1)
  d1.setAuthTag(tag1)
  return Buffer.concat([d1.update(ct1), d1.final()])
}
