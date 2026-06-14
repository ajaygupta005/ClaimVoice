import { describe, it, expect } from 'vitest'
import { createServer } from 'node:http'
import { WebSocketServer } from 'ws'
import pino from 'pino'
import { openBridge, type BridgeEvent } from '../../src/twilio_ws/voice_agent_bridge.js'

const log = pino({ level: 'silent' })

// ── Fake voice-agent server helpers ──────────────────────────────────────────

interface FakeAgent {
  url: string
  received: BridgeEvent[]
  teardown: () => Promise<void>
}

async function startFakeAgent(): Promise<FakeAgent> {
  const received: BridgeEvent[] = []
  const http = createServer()
  const wss = new WebSocketServer({ server: http })

  wss.on('connection', (ws) => {
    ws.on('message', (raw) => {
      received.push(JSON.parse(raw.toString()) as BridgeEvent)
    })
  })

  await new Promise<void>((resolve) => http.listen(0, '127.0.0.1', resolve))
  const { port } = http.address() as { port: number }

  return {
    url: `ws://127.0.0.1:${port}`,
    received,
    teardown: () =>
      new Promise<void>((resolve) => {
        wss.close()
        http.close(() => resolve())
      }),
  }
}

// Wait until `received` has at least `n` entries (or throw on timeout).
async function waitFor(received: BridgeEvent[], n: number, ms = 1000): Promise<void> {
  const deadline = Date.now() + ms
  while (received.length < n && Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 20))
  }
  if (received.length < n)
    throw new Error(`Expected ${n} messages, got ${received.length} after ${ms}ms`)
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('openBridge — no-op fallback', () => {
  it('returns a no-op bridge when URL is undefined', () => {
    const bridge = openBridge(undefined, 'CA-noop', 'SM-noop', log)
    expect(() => {
      bridge.sendStart({ callSid: 'CA-noop', streamSid: 'SM-noop', mediaFormat: undefined })
      bridge.sendAudio(Buffer.alloc(4))
      bridge.sendStop()
      bridge.close()
    }).not.toThrow()
  })

  it('returns a no-op bridge when the URL is unreachable', async () => {
    const bridge = openBridge('ws://127.0.0.1:1', 'CA-dead', 'SM-dead', log)
    expect(() => {
      bridge.sendStart({ callSid: 'CA-dead', streamSid: 'SM-dead', mediaFormat: undefined })
      bridge.sendAudio(Buffer.alloc(4))
      bridge.sendStop()
    }).not.toThrow()
    await new Promise((r) => setTimeout(r, 80))
    bridge.close()
  })
})

describe('openBridge — live connection', () => {
  it('forwards a start event with callSid, streamSid, and mediaFormat', async () => {
    const agent = await startFakeAgent()
    try {
      const bridge = openBridge(agent.url, 'CA001', 'SM001', log)
      bridge.sendStart({
        callSid: 'CA001',
        streamSid: 'SM001',
        mediaFormat: { encoding: 'audio/x-mulaw', sampleRate: 8000, channels: 1 },
      })
      await waitFor(agent.received, 1)
      bridge.close()

      const ev = agent.received[0] as Extract<BridgeEvent, { type: 'start' }>
      expect(ev.type).toBe('start')
      expect(ev.callSid).toBe('CA001')
      expect(ev.streamSid).toBe('SM001')
      expect(ev.mediaFormat?.sampleRate).toBe(8000)
    } finally {
      await agent.teardown()
    }
  })

  it('forwards an audio event with base64 PCM payload', async () => {
    const agent = await startFakeAgent()
    try {
      const bridge = openBridge(agent.url, 'CA002', 'SM002', log)
      const pcm = Buffer.alloc(64, 0x7f)
      bridge.sendAudio(pcm)
      await waitFor(agent.received, 1)
      bridge.close()

      const ev = agent.received[0] as Extract<BridgeEvent, { type: 'audio' }>
      expect(ev.type).toBe('audio')
      expect(ev.callSid).toBe('CA002')
      expect(ev.streamSid).toBe('SM002')
      expect(Buffer.from(ev.pcm24k, 'base64').length).toBe(64)
    } finally {
      await agent.teardown()
    }
  })

  it('forwards a stop event after start', async () => {
    const agent = await startFakeAgent()
    try {
      const bridge = openBridge(agent.url, 'CA003', 'SM003', log)
      bridge.sendStart({ callSid: 'CA003', streamSid: 'SM003', mediaFormat: undefined })
      bridge.sendStop()
      await waitFor(agent.received, 2)
      bridge.close()

      expect(agent.received.map((e) => e.type)).toEqual(['start', 'stop'])
      expect(agent.received[1].callSid).toBe('CA003')
    } finally {
      await agent.teardown()
    }
  })

  it('buffers events queued before the socket opens', async () => {
    const agent = await startFakeAgent()
    try {
      const bridge = openBridge(agent.url, 'CA004', 'SM004', log)
      // All three sent synchronously — socket is still CONNECTING
      bridge.sendStart({ callSid: 'CA004', streamSid: 'SM004', mediaFormat: undefined })
      bridge.sendAudio(Buffer.alloc(8))
      bridge.sendStop()
      await waitFor(agent.received, 3)
      bridge.close()

      expect(agent.received.map((e) => e.type)).toEqual(['start', 'audio', 'stop'])
    } finally {
      await agent.teardown()
    }
  })

  it('does not send after close is called', async () => {
    const agent = await startFakeAgent()
    try {
      const bridge = openBridge(agent.url, 'CA005', 'SM005', log)
      bridge.sendStart({ callSid: 'CA005', streamSid: 'SM005', mediaFormat: undefined })
      await waitFor(agent.received, 1)
      bridge.close()
      bridge.sendAudio(Buffer.alloc(4))
      await new Promise((r) => setTimeout(r, 80))

      expect(agent.received.length).toBe(1)
    } finally {
      await agent.teardown()
    }
  })
})
