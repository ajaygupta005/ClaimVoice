/**
 * Bridge from a Twilio Media Stream to the Voice Agent WebSocket service.
 *
 * Outbound (telephony → voice-agent) event types:
 *
 *   { type: 'start', callSid, streamSid, mediaFormat }
 *   { type: 'audio', callSid, streamSid, pcm24k: <base64 PCM16 24 kHz> }
 *   { type: 'stop',  callSid, streamSid }
 *
 * Inbound (voice-agent → telephony) event types handled:
 *
 *   { type: 'tts.audio', callSid, streamSid, chunkIndex, totalChunks,
 *     isFinal, pcm24k: <base64 PCM16 24 kHz> }
 *
 * When a tts.audio event is received the bridge calls `onReturnAudio` with the
 * decoded PCM16 24 kHz buffer so the caller can convert it to Twilio format.
 *
 * All other inbound messages are logged at debug level and ignored.
 *
 * If VOICE_AGENT_WS_URL is absent or the connection fails the bridge becomes
 * a silent no-op — the Twilio socket stays alive so the caller is not dropped.
 */

import { WebSocket } from 'ws'
import type { Logger } from 'pino'

// ── Outbound event shapes (telephony → voice-agent) ───────────────────────────

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

// ── Inbound event shapes (voice-agent → telephony) ────────────────────────────

export interface TtsAudioInbound {
  type: 'tts.audio'
  callSid: string
  streamSid: string
  chunkIndex: number
  totalChunks: number
  isFinal: boolean
  pcm24k: string  // base64-encoded PCM16 24 kHz
}

// ── Return-audio callback ─────────────────────────────────────────────────────

/** Called with decoded PCM16 24 kHz audio that should be sent back to Twilio. */
export type ReturnAudioCallback = (pcm24k: Buffer, isFinal: boolean) => void

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
  private readonly onReturnAudio: ReturnAudioCallback | undefined
  private closed = false
  private readonly pending: BridgeEvent[] = []

  constructor(
    ws: WebSocket,
    callSid: string,
    streamSid: string,
    log: Logger,
    onReturnAudio?: ReturnAudioCallback,
  ) {
    this.ws = ws
    this.callSid = callSid
    this.streamSid = streamSid
    this.log = log
    this.onReturnAudio = onReturnAudio

    ws.on('open', () => {
      log.info({ event: 'bridge.open', callSid, streamSid })
      for (const ev of this.pending) this.#write(ev)
      this.pending.length = 0
    })

    ws.on('message', (raw: Buffer | string) => {
      this.#handleInbound(raw.toString())
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

  #handleInbound(raw: string): void {
    let msg: Record<string, unknown>
    try {
      msg = JSON.parse(raw) as Record<string, unknown>
    } catch {
      this.log.warn({ event: 'bridge.inbound_parse_error', callSid: this.callSid, raw: raw.slice(0, 120) })
      return
    }

    if (msg.type === 'tts.audio' && this.onReturnAudio) {
      const ev = msg as unknown as TtsAudioInbound
      try {
        const pcm24k = Buffer.from(ev.pcm24k, 'base64')
        this.log.debug({
          event: 'bridge.return_audio',
          callSid: this.callSid,
          streamSid: this.streamSid,
          chunkIndex: ev.chunkIndex,
          isFinal: ev.isFinal,
          bytes: pcm24k.length,
        })
        this.onReturnAudio(pcm24k, ev.isFinal)
      } catch (err) {
        this.log.warn({ event: 'bridge.return_audio_error', callSid: this.callSid, err })
      }
      return
    }

    // Log-and-ignore all other inbound messages (acks, transcripts, answers…)
    this.log.debug({ event: 'bridge.inbound_ignored', type: msg.type, callSid: this.callSid })
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
 *
 * @param onReturnAudio  Called with decoded PCM16 24 kHz when the voice-agent
 *                       sends a tts.audio event. The caller converts the buffer
 *                       to Twilio µ-law format and writes it to the caller socket.
 *
 * Always returns a valid VoiceAgentBridge — falls back to NoOpBridge if the
 * URL is missing or the initial WebSocket constructor throws.
 */
export function openBridge(
  voiceAgentUrl: string | undefined,
  callSid: string,
  streamSid: string,
  log: Logger,
  onReturnAudio?: ReturnAudioCallback,
): VoiceAgentBridge {
  if (!voiceAgentUrl) {
    log.warn({ event: 'bridge.disabled', callSid, streamSid, reason: 'VOICE_AGENT_WS_URL not configured' })
    return new NoOpBridge()
  }

  try {
    const url = `${voiceAgentUrl}?callSid=${encodeURIComponent(callSid)}&streamSid=${encodeURIComponent(streamSid)}`
    const ws = new WebSocket(url)
    log.info({ event: 'bridge.connecting', callSid, streamSid, voiceAgentUrl })
    return new LiveBridge(ws, callSid, streamSid, log, onReturnAudio)
  } catch (err) {
    log.error({ event: 'bridge.open_failed', callSid, streamSid, err })
    return new NoOpBridge()
  }
}
