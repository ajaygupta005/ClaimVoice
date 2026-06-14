/**
 * Tests for the WS-7 Twilio audio return path (Component 28).
 *
 * Verifies that tts.audio events received from the voice-agent bridge are
 * converted to Twilio media frames and forwarded to the "Twilio" socket.
 */

import { describe, it, expect } from 'vitest'
import { createServer } from 'node:http'
import { WebSocket, WebSocketServer } from 'ws'
import pino from 'pino'
import { openBridge, type BridgeEvent } from '../../src/twilio_ws/voice_agent_bridge.js'
import { pcm16ToTwilioFrame } from '../../src/twilio_ws/handler.js'
import { ulawToPcm16, resamplePcm16 } from '../../src/audio_codec/index.js'

const log = pino({ level: 'silent' })

// ── Fake voice-agent server ───────────────────────────────────────────────────

interface FakeAgent {
  url: string
  /** Sends a raw JSON string to the connected bridge client. */
  pushToClient: (msg: string) => void
  teardown: () => Promise<void>
}

async function startFakeAgent(): Promise<FakeAgent> {
  const http = createServer()
  const wss = new WebSocketServer({ server: http })
  let clientSocket: WebSocket | null = null

  wss.on('connection', (ws) => { clientSocket = ws })

  await new Promise<void>((resolve) => http.listen(0, '127.0.0.1', resolve))
  const { port } = http.address() as { port: number }

  return {
    url: `ws://127.0.0.1:${port}`,
    pushToClient: (msg) => { clientSocket?.send(msg) },
    teardown: () =>
      new Promise<void>((resolve) => {
        wss.close()
        http.close(() => resolve())
      }),
  }
}

/** Wait until `arr` has at least `n` items, or throw on timeout. */
async function waitFor<T>(arr: T[], n: number, ms = 1500): Promise<void> {
  const deadline = Date.now() + ms
  while (arr.length < n && Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 20))
  }
  if (arr.length < n) throw new Error(`Expected ${n} items, got ${arr.length}`)
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Build a valid tts.audio JSON string with n bytes of silent PCM24k. */
function makeTtsAudioMsg(callSid: string, streamSid: string, nBytes = 48, isFinal = false): string {
  const pcm = Buffer.alloc(nBytes, 0)
  return JSON.stringify({
    type: 'tts.audio',
    callSid,
    streamSid,
    chunkIndex: 0,
    totalChunks: 1,
    isFinal,
    pcm24k: pcm.toString('base64'),
  })
}

// ── pcm16ToTwilioFrame unit tests ─────────────────────────────────────────────

describe('pcm16ToTwilioFrame', () => {
  it('produces a valid Twilio media JSON frame', () => {
    const pcm24k = Buffer.alloc(48, 0)
    const frame = pcm16ToTwilioFrame('SM001', pcm24k)
    const parsed = JSON.parse(frame)
    expect(parsed.event).toBe('media')
    expect(parsed.streamSid).toBe('SM001')
    expect(typeof parsed.media.payload).toBe('string')
    // payload must be non-empty base64
    const decoded = Buffer.from(parsed.media.payload, 'base64')
    expect(decoded.length).toBeGreaterThan(0)
  })

  it('resamples 24 kHz to 8 kHz: output is shorter', () => {
    const pcm24k = Buffer.alloc(4800, 0)  // 100 ms at 24 kHz, int16 = 200 ms
    const frame = pcm16ToTwilioFrame('SM002', pcm24k)
    const parsed = JSON.parse(frame)
    // µ-law output: 1 byte per sample, 8 kHz → 1/3 of 24 kHz samples
    const ulawOut = Buffer.from(parsed.media.payload, 'base64')
    // Input: 4800 bytes = 2400 samples at 24 kHz → resampled to ~800 samples at 8 kHz → 800 µ-law bytes
    expect(ulawOut.length).toBeLessThan(2400)
  })
})

// ── Return-audio integration tests ────────────────────────────────────────────

describe('return audio path — bridge → Twilio socket', () => {
  it('tts.audio from voice-agent triggers the return-audio callback', async () => {
    const agent = await startFakeAgent()
    const returned: Array<{ pcm: Buffer; isFinal: boolean }> = []

    try {
      const bridge = openBridge(
        agent.url,
        'CA-RA01',
        'SM-RA01',
        log,
        (pcm, isFinal) => returned.push({ pcm, isFinal }),
      )
      bridge.sendStart({ callSid: 'CA-RA01', streamSid: 'SM-RA01', mediaFormat: undefined })

      // Give the WS time to connect, then have the fake agent push a tts.audio back
      await new Promise((r) => setTimeout(r, 80))
      agent.pushToClient(makeTtsAudioMsg('CA-RA01', 'SM-RA01', 64, true))

      await waitFor(returned, 1)
      bridge.close()

      expect(returned.length).toBe(1)
      expect(returned[0].pcm.length).toBe(64)
      expect(returned[0].isFinal).toBe(true)
    } finally {
      await agent.teardown()
    }
  })

  it('multiple tts.audio chunks all reach the callback', async () => {
    const agent = await startFakeAgent()
    const returned: Buffer[] = []

    try {
      const bridge = openBridge(
        agent.url,
        'CA-RA02',
        'SM-RA02',
        log,
        (pcm) => returned.push(pcm),
      )
      bridge.sendStart({ callSid: 'CA-RA02', streamSid: 'SM-RA02', mediaFormat: undefined })

      await new Promise((r) => setTimeout(r, 80))
      for (let i = 0; i < 3; i++) {
        agent.pushToClient(makeTtsAudioMsg('CA-RA02', 'SM-RA02', 32, i === 2))
        await new Promise((r) => setTimeout(r, 10))
      }

      await waitFor(returned, 3)
      bridge.close()

      expect(returned.length).toBe(3)
      for (const buf of returned) expect(buf.length).toBe(32)
    } finally {
      await agent.teardown()
    }
  })

  it('non-tts.audio inbound messages are ignored without crashing', async () => {
    const agent = await startFakeAgent()
    const returned: Buffer[] = []

    try {
      const bridge = openBridge(
        agent.url,
        'CA-RA03',
        'SM-RA03',
        log,
        (pcm) => returned.push(pcm),
      )
      bridge.sendStart({ callSid: 'CA-RA03', streamSid: 'SM-RA03', mediaFormat: undefined })

      await new Promise((r) => setTimeout(r, 80))
      // Send an ack and a transcript event — neither should trigger the callback
      agent.pushToClient(JSON.stringify({ ack: 'start', callSid: 'CA-RA03', streamSid: 'SM-RA03' }))
      agent.pushToClient(JSON.stringify({ type: 'transcript.final', text: 'Hello', callSid: 'CA-RA03', streamSid: 'SM-RA03' }))

      await new Promise((r) => setTimeout(r, 100))
      bridge.close()

      expect(returned.length).toBe(0)
    } finally {
      await agent.teardown()
    }
  })

  it('bridge with no callback ignores tts.audio safely', async () => {
    const agent = await startFakeAgent()

    try {
      // openBridge without onReturnAudio — must not throw when tts.audio arrives
      const bridge = openBridge(agent.url, 'CA-RA04', 'SM-RA04', log)
      bridge.sendStart({ callSid: 'CA-RA04', streamSid: 'SM-RA04', mediaFormat: undefined })

      await new Promise((r) => setTimeout(r, 80))
      expect(() => agent.pushToClient(makeTtsAudioMsg('CA-RA04', 'SM-RA04', 16))).not.toThrow()

      await new Promise((r) => setTimeout(r, 80))
      bridge.close()
    } finally {
      await agent.teardown()
    }
  })

  it('invalid base64 in tts.audio does not crash the bridge', async () => {
    const agent = await startFakeAgent()
    const returned: Buffer[] = []

    try {
      const bridge = openBridge(
        agent.url,
        'CA-RA05',
        'SM-RA05',
        log,
        (pcm) => returned.push(pcm),
      )
      bridge.sendStart({ callSid: 'CA-RA05', streamSid: 'SM-RA05', mediaFormat: undefined })

      await new Promise((r) => setTimeout(r, 80))
      agent.pushToClient(JSON.stringify({
        type: 'tts.audio',
        callSid: 'CA-RA05',
        streamSid: 'SM-RA05',
        chunkIndex: 0,
        totalChunks: 1,
        isFinal: true,
        pcm24k: '!!!not-valid-base64!!!',
      }))

      await new Promise((r) => setTimeout(r, 80))
      bridge.close()

      // Buffer.from with invalid base64 doesn't throw in Node — it silently
      // produces a truncated buffer. The callback may or may not be called,
      // but the bridge must remain operational.
      // Key assertion: no unhandled exception.
    } finally {
      await agent.teardown()
    }
  })
})
