/**
 * Bridge from a Twilio Media Stream to the Voice Agent WebSocket service.
 *
 * Three event types are forwarded (JSON over WS):
 *
 *   { type: 'start', callSid, streamSid, mediaFormat }
 *   { type: 'audio', callSid, streamSid, pcm24k: <base64 PCM16 24 kHz> }
 *   { type: 'stop',  callSid, streamSid }
 *
 * If VOICE_AGENT_WS_URL is absent or the connection fails the bridge becomes
 * a silent no-op — the Twilio socket stays alive so the caller is not dropped.
 */

import { WebSocket } from 'ws'
import type { Logger } from 'pino'

// ── Event shape ───────────────────────────────────────────────────────────────

export interface BridgeStartEvent {
  type: 'start'
  callSid: string
  streamSid: string
  mediaFormat?: { encoding: string; sampleRate: number; channels: number }
}

export interface BridgeAudioEvent {
  type: 'audio'
  callSid: string
  streamSid: string
  pcm24k: string  // base64-encoded PCM16 24 kHz
}

export interface BridgeStopEvent {
  type: 'stop'
  callSid: string
  streamSid: string
}

export type BridgeEvent = BridgeStartEvent | BridgeAudioEvent | BridgeStopEvent

// ── Public interface ──────────────────────────────────────────────────────────

export interface VoiceAgentBridge {
  sendStart(meta: Omit<BridgeStartEvent, 'type'>): void
  sendAudio(pcm24k: Buffer): void
  sendStop(): void
  close(): void
}

// ── Live bridge (real WS connection) ─────────────────────────────────────────

class LiveBridge implements VoiceAgentBridge {
  private readonly ws: WebSocket
  private readonly callSid: string
  private readonly streamSid: string
  private readonly log: Logger
  private closed = false
  private readonly pending: BridgeEvent[] = []

  constructor(ws: WebSocket, callSid: string, streamSid: string, log: Logger) {
    this.ws = ws
    this.callSid = callSid
    this.streamSid = streamSid
    this.log = log

    ws.on('open', () => {
      log.info({ event: 'bridge.open', callSid, streamSid })
      for (const ev of this.pending) this.#write(ev)
      this.pending.length = 0
    })

    ws.on('error', (err) => {
      log.error({ event: 'bridge.error', callSid, streamSid, err })
      this.closed = true
    })

    ws.on('close', () => {
      if (!this.closed) {
        log.info({ event: 'bridge.closed', callSid, streamSid })
        this.closed = true
      }
    })
  }

  sendStart(meta: Omit<BridgeStartEvent, 'type'>): void {
    this.#emit({ type: 'start', ...meta })
  }

  sendAudio(pcm24k: Buffer): void {
    this.#emit({
      type: 'audio',
      callSid: this.callSid,
      streamSid: this.streamSid,
      pcm24k: pcm24k.toString('base64'),
    })
  }

  sendStop(): void {
    this.#emit({ type: 'stop', callSid: this.callSid, streamSid: this.streamSid })
  }

  close(): void {
    if (!this.closed && this.ws.readyState !== WebSocket.CLOSED) {
      this.closed = true
      this.ws.close()
    }
  }

  #emit(ev: BridgeEvent): void {
    if (this.closed) return
    if (this.ws.readyState === WebSocket.CONNECTING) {
      this.pending.push(ev)
    } else {
      this.#write(ev)
    }
  }

  #write(ev: BridgeEvent): void {
    try {
      this.ws.send(JSON.stringify(ev))
    } catch (err) {
      this.log.warn({ event: 'bridge.send_failed', callSid: this.callSid, streamSid: this.streamSid, err })
    }
  }
}

// ── No-op bridge ──────────────────────────────────────────────────────────────

class NoOpBridge implements VoiceAgentBridge {
  sendStart() { /* no-op */ }
  sendAudio() { /* no-op */ }
  sendStop()  { /* no-op */ }
  close()     { /* no-op */ }
}

// ── Factory ───────────────────────────────────────────────────────────────────

/**
 * Open a bridge to the voice-agent WebSocket.
 * Always returns a valid VoiceAgentBridge — falls back to NoOpBridge if the
 * URL is missing or the initial WebSocket constructor throws.
 */
export function openBridge(
  voiceAgentUrl: string | undefined,
  callSid: string,
  streamSid: string,
  log: Logger,
): VoiceAgentBridge {
  if (!voiceAgentUrl) {
    log.warn({ event: 'bridge.disabled', callSid, streamSid, reason: 'VOICE_AGENT_WS_URL not configured' })
    return new NoOpBridge()
  }

  try {
    const url = `${voiceAgentUrl}?callSid=${encodeURIComponent(callSid)}&streamSid=${encodeURIComponent(streamSid)}`
    const ws = new WebSocket(url)
    log.info({ event: 'bridge.connecting', callSid, streamSid, voiceAgentUrl })
    return new LiveBridge(ws, callSid, streamSid, log)
  } catch (err) {
    log.error({ event: 'bridge.open_failed', callSid, streamSid, err })
    return new NoOpBridge()
  }
}
