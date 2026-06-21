/**
 * Component 66 — Twilio Phone Demo Parity (TypeScript side)
 *
 * Tests that the telephony handler path produces identical protocol behavior
 * to the browser voice path:
 *
 * 1. Full frame sequence: start → media → stop is forwarded to voice-agent bridge.
 * 2. µ-law 8 kHz (Twilio inbound) is converted to PCM16 24 kHz before forwarding.
 * 3. TTS audio returned from voice-agent is converted back to µ-law 8 kHz for Twilio.
 * 4. Disconnect before stop (caller hangs up) finalizes the bridge safely.
 * 5. Multiple media frames accumulate audio bytes.
 * 6. µ-law 8 kHz encoded payload round-trips without crashing (codec parity).
 * 7. Bridge forwards events in order even when WS is still CONNECTING at send time.
 * 8. No events are forwarded after the bridge is closed (stop-once guarantee).
 */

import { describe, it, expect, afterEach } from 'vitest'
import { createServer } from 'node:http'
import { WebSocketServer, type WebSocket as WsSocket } from 'ws'
import pino from 'pino'
import { openBridge, type BridgeEvent } from '../../src/twilio_ws/voice_agent_bridge.js'
import { pcm16ToTwilioFrame } from '../../src/twilio_ws/handler.js'
import { ulawToPcm16, pcm16ToUlaw, resamplePcm16 } from '../../src/audio_codec/index.js'

const log = pino({ level: 'silent' })

// ── Fake voice-agent server ───────────────────────────────────────────────────

interface FakeAgent {
  url: string
  received: BridgeEvent[]
  lastSocket: WsSocket | null
  pushToClient: (msg: string) => void
  teardown: () => Promise<void>
}

async function startFakeAgent(): Promise<FakeAgent> {
  const received: BridgeEvent[] = []
  let lastSocket: WsSocket | null = null
  const http = createServer()
  const wss = new WebSocketServer({ server: http })

  wss.on('connection', (ws) => {
    lastSocket = ws
    ws.on('message', (raw) => {
      received.push(JSON.parse(raw.toString()) as BridgeEvent)
    })
  })

  await new Promise<void>((resolve) => http.listen(0, '127.0.0.1', resolve))
  const { port } = http.address() as { port: number }

  const agent: FakeAgent = {
    url: `ws://127.0.0.1:${port}`,
    received,
    get lastSocket() { return lastSocket },
    pushToClient: (msg) => { lastSocket?.send(msg) },
    teardown: () =>
      new Promise<void>((resolve) => {
        wss.close()
        http.close(() => resolve())
      }),
  }
  return agent
}

async function waitFor<T>(arr: T[], n: number, ms = 1500): Promise<void> {
  const deadline = Date.now() + ms
  while (arr.length < n && Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 20))
  }
  if (arr.length < n)
    throw new Error(`Expected ${n} items, got ${arr.length} after ${ms}ms`)
}

// Build a µ-law payload (base64) for simulating a Twilio `media` frame.
function makeTwilioUlawPayload(nSamples = 160): string {
  const ulaw = Buffer.alloc(nSamples, 0xff)  // silence in µ-law
  return ulaw.toString('base64')
}

// Build a tts.audio inbound JSON string (voice-agent → bridge).
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

// ── 1. Full sequence: start → media → stop forwarded in order ─────────────────

describe('handler parity: full frame sequence', () => {
  it('start → media → stop are all forwarded to voice-agent bridge in order', async () => {
    const agent = await startFakeAgent()
    try {
      const bridge = openBridge(agent.url, 'CA-seq1', 'SM-seq1', log)

      // Simulate the Twilio handler processing start, media, stop frames.
      bridge.sendStart({
        callSid: 'CA-seq1',
        streamSid: 'SM-seq1',
        mediaFormat: { encoding: 'audio/x-mulaw', sampleRate: 8000, channels: 1 },
      })

      const ulaw = Buffer.from(makeTwilioUlawPayload(160), 'base64')
      const pcm8k = ulawToPcm16(ulaw)
      const pcm24k = resamplePcm16(pcm8k, 8000, 24000)
      bridge.sendAudio(pcm24k)

      bridge.sendStop()
      await waitFor(agent.received, 3)
      bridge.close()

      expect(agent.received.map((e) => e.type)).toEqual(['start', 'audio', 'stop'])
    } finally {
      await agent.teardown()
    }
  })

  it('start event includes callSid, streamSid, and mediaFormat', async () => {
    const agent = await startFakeAgent()
    try {
      const bridge = openBridge(agent.url, 'CA-seq2', 'SM-seq2', log)
      bridge.sendStart({
        callSid: 'CA-seq2',
        streamSid: 'SM-seq2',
        mediaFormat: { encoding: 'audio/x-mulaw', sampleRate: 8000, channels: 1 },
      })
      await waitFor(agent.received, 1)
      bridge.close()

      const ev = agent.received[0] as Extract<BridgeEvent, { type: 'start' }>
      expect(ev.type).toBe('start')
      expect(ev.callSid).toBe('CA-seq2')
      expect(ev.streamSid).toBe('SM-seq2')
      expect(ev.mediaFormat?.encoding).toBe('audio/x-mulaw')
    } finally {
      await agent.teardown()
    }
  })

  it('stop event carries callSid and streamSid', async () => {
    const agent = await startFakeAgent()
    try {
      const bridge = openBridge(agent.url, 'CA-seq3', 'SM-seq3', log)
      bridge.sendStart({ callSid: 'CA-seq3', streamSid: 'SM-seq3', mediaFormat: undefined })
      bridge.sendStop()
      await waitFor(agent.received, 2)
      bridge.close()

      const stop = agent.received[1]
      expect(stop.type).toBe('stop')
      expect(stop.callSid).toBe('CA-seq3')
      expect(stop.streamSid).toBe('SM-seq3')
    } finally {
      await agent.teardown()
    }
  })
})

// ── 2. µ-law 8 kHz → PCM16 24 kHz codec parity ───────────────────────────────

describe('handler parity: inbound codec conversion', () => {
  it('µ-law input payload survives ulawToPcm16 → resamplePcm16 without throwing', () => {
    const ulaw = Buffer.from(makeTwilioUlawPayload(160), 'base64')
    expect(() => {
      const pcm8k = ulawToPcm16(ulaw)
      const pcm24k = resamplePcm16(pcm8k, 8000, 24000)
      expect(pcm24k.length).toBeGreaterThan(0)
      expect(pcm24k.length % 2).toBe(0)  // PCM16: 2 bytes per sample
    }).not.toThrow()
  })

  it('160 µ-law samples (20 ms at 8 kHz) become 480 PCM16 samples at 24 kHz', () => {
    const ulaw = Buffer.alloc(160, 0xff)  // 160 samples of silence
    const pcm8k = ulawToPcm16(ulaw)      // 160 samples × 2 = 320 bytes
    const pcm24k = resamplePcm16(pcm8k, 8000, 24000)  // 480 samples × 2 = 960 bytes
    expect(pcm8k.length).toBe(320)
    expect(pcm24k.length).toBe(960)
  })

  it('audio forwarded to bridge has correct length after conversion', async () => {
    const agent = await startFakeAgent()
    try {
      const bridge = openBridge(agent.url, 'CA-codec1', 'SM-codec1', log)
      bridge.sendStart({ callSid: 'CA-codec1', streamSid: 'SM-codec1', mediaFormat: undefined })

      const ulaw = Buffer.alloc(160, 0xff)
      const pcm8k = ulawToPcm16(ulaw)
      const pcm24k = resamplePcm16(pcm8k, 8000, 24000)
      bridge.sendAudio(pcm24k)
      await waitFor(agent.received, 2)
      bridge.close()

      const audioEv = agent.received[1] as Extract<BridgeEvent, { type: 'audio' }>
      const forwardedBytes = Buffer.from(audioEv.pcm24k, 'base64')
      expect(forwardedBytes.length).toBe(pcm24k.length)
    } finally {
      await agent.teardown()
    }
  })
})

// ── 3. Return audio: voice-agent TTS → Twilio µ-law ─────────────────────────

describe('handler parity: return audio path', () => {
  it('tts.audio triggers the return-audio callback with PCM24k buffer', async () => {
    const agent = await startFakeAgent()
    const returned: Array<{ pcm: Buffer; isFinal: boolean }> = []

    try {
      const bridge = openBridge(
        agent.url,
        'CA-ret1',
        'SM-ret1',
        log,
        (pcm, isFinal) => returned.push({ pcm, isFinal }),
      )
      bridge.sendStart({ callSid: 'CA-ret1', streamSid: 'SM-ret1', mediaFormat: undefined })

      await new Promise((r) => setTimeout(r, 80))
      agent.pushToClient(makeTtsAudioMsg('CA-ret1', 'SM-ret1', 64, true))
      await waitFor(returned, 1)
      bridge.close()

      expect(returned.length).toBe(1)
      expect(returned[0].pcm.length).toBe(64)
      expect(returned[0].isFinal).toBe(true)
    } finally {
      await agent.teardown()
    }
  })

  it('pcm16ToTwilioFrame converts PCM24k to a valid Twilio media frame', () => {
    const pcm24k = Buffer.alloc(960, 0)  // 480 samples, 20 ms at 24 kHz
    const frame = pcm16ToTwilioFrame('SM-ret2', pcm24k)
    const parsed = JSON.parse(frame)

    expect(parsed.event).toBe('media')
    expect(parsed.streamSid).toBe('SM-ret2')
    expect(typeof parsed.media.payload).toBe('string')

    // Payload must be valid base64 µ-law: ~160 bytes (960 → 480 → 160)
    const ulaw = Buffer.from(parsed.media.payload, 'base64')
    expect(ulaw.length).toBeGreaterThan(0)
    expect(ulaw.length).toBeLessThan(960)  // downsampled
  })

  it('full round-trip: PCM24k → Twilio frame → µ-law → PCM8k does not throw', () => {
    const pcm24k = Buffer.alloc(960, 0)
    const frame = pcm16ToTwilioFrame('SM-ret3', pcm24k)
    const parsed = JSON.parse(frame)
    const ulaw = Buffer.from(parsed.media.payload, 'base64')
    expect(() => {
      const pcm8k = ulawToPcm16(ulaw)
      expect(pcm8k.length % 2).toBe(0)
    }).not.toThrow()
  })
})

// ── 4. Disconnect safety ──────────────────────────────────────────────────────

describe('handler parity: disconnect safety', () => {
  it('closing bridge before stop does not throw', async () => {
    const agent = await startFakeAgent()
    try {
      const bridge = openBridge(agent.url, 'CA-disc1', 'SM-disc1', log)
      bridge.sendStart({ callSid: 'CA-disc1', streamSid: 'SM-disc1', mediaFormat: undefined })
      await waitFor(agent.received, 1)

      // Caller hangs up — close without sendStop
      expect(() => { bridge.close() }).not.toThrow()
    } finally {
      await agent.teardown()
    }
  })

  it('no events forwarded after bridge.close()', async () => {
    const agent = await startFakeAgent()
    try {
      const bridge = openBridge(agent.url, 'CA-disc2', 'SM-disc2', log)
      bridge.sendStart({ callSid: 'CA-disc2', streamSid: 'SM-disc2', mediaFormat: undefined })
      await waitFor(agent.received, 1)
      bridge.close()

      bridge.sendAudio(Buffer.alloc(64))
      await new Promise((r) => setTimeout(r, 80))

      expect(agent.received.length).toBe(1)  // only the start event
    } finally {
      await agent.teardown()
    }
  })

  it('unreachable voice-agent URL falls back to no-op safely', () => {
    expect(() => {
      const bridge = openBridge('ws://127.0.0.1:1', 'CA-disc3', 'SM-disc3', log)
      bridge.sendStart({ callSid: 'CA-disc3', streamSid: 'SM-disc3', mediaFormat: undefined })
      bridge.sendAudio(Buffer.alloc(4))
      bridge.sendStop()
      bridge.close()
    }).not.toThrow()
  })
})

// ── 5. Multiple media frames ─────────────────────────────────────────────────

describe('handler parity: multiple media frames', () => {
  it('three media frames all reach the bridge as separate audio events', async () => {
    const agent = await startFakeAgent()
    try {
      const bridge = openBridge(agent.url, 'CA-multi1', 'SM-multi1', log)
      bridge.sendStart({ callSid: 'CA-multi1', streamSid: 'SM-multi1', mediaFormat: undefined })

      const ulaw = Buffer.alloc(160, 0xff)
      const pcm24k = resamplePcm16(ulawToPcm16(ulaw), 8000, 24000)

      bridge.sendAudio(pcm24k)
      bridge.sendAudio(pcm24k)
      bridge.sendAudio(pcm24k)

      await waitFor(agent.received, 4)  // start + 3 audio
      bridge.close()

      const audioEvents = agent.received.filter((e) => e.type === 'audio')
      expect(audioEvents.length).toBe(3)
    } finally {
      await agent.teardown()
    }
  })
})

// ── 6. Pending queue: events buffered before WS opens ────────────────────────

describe('handler parity: CONNECTING-state buffering', () => {
  it('start + audio + stop queued synchronously all arrive after WS opens', async () => {
    const agent = await startFakeAgent()
    try {
      const bridge = openBridge(agent.url, 'CA-buf1', 'SM-buf1', log)

      const pcm = Buffer.alloc(128, 0)
      bridge.sendStart({ callSid: 'CA-buf1', streamSid: 'SM-buf1', mediaFormat: undefined })
      bridge.sendAudio(pcm)
      bridge.sendStop()

      await waitFor(agent.received, 3, 2000)
      bridge.close()

      expect(agent.received.map((e) => e.type)).toEqual(['start', 'audio', 'stop'])
    } finally {
      await agent.teardown()
    }
  })
})
