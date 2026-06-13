// Upload encrypted recordings to MinIO/S3.

import { S3Client, PutObjectCommand, GetObjectCommand } from '@aws-sdk/client-s3'
import type { EncryptedBlob } from './crypto.js'

function client() {
  return new S3Client({
    endpoint: process.env.S3_ENDPOINT,
    region: 'us-east-1',
    credentials: {
      accessKeyId: process.env.S3_ACCESS_KEY ?? '',
      secretAccessKey: process.env.S3_SECRET_KEY ?? '',
    },
    forcePathStyle: true,
  })
}

function bucket(): string {
  return process.env.S3_BUCKET || 'claimvoice'
}

export async function uploadEncrypted(callSid: string, blob: EncryptedBlob): Promise<string> {
  const s3 = client()
  const ciphertextKey = `recordings/${callSid}.bin`
  const wrappedKeyKey = `recordings/${callSid}.key`

  await s3.send(new PutObjectCommand({
    Bucket: bucket(),
    Key: ciphertextKey,
    Body: blob.ciphertext,
    ContentType: 'application/octet-stream',
  }))
  await s3.send(new PutObjectCommand({
    Bucket: bucket(),
    Key: wrappedKeyKey,
    Body: blob.wrappedKey,
    ContentType: 'application/octet-stream',
  }))

  return ciphertextKey
}
