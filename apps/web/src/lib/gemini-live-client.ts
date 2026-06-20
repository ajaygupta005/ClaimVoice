/**
 * GeminiLiveClient — browser-side Gemini Live STT client (Component 52).
 *
 * Captures microphone audio, streams PCM16 frames to the ClaimVoice
 * voice-agent backend WebSocket, and surfaces normalized transcript events.
 *
 * Security: GEMINI_API_KEY never touches the browser. The server holds the key
 * and runs the Gemini Live session server-side. The browser sends raw PCM audio
 * and receives text-only transcript events.
 *
 * Usage:
 *   const client = new GeminiLiveClient({ wsUrl, onPartial, onFinal, onError, onClose })
 *   await client.start()   // requests mic, opens WebSocket, starts streaming
 *   client.stop()          // sends stop signal, releases mic
 *   client.cleanup()       // idempotent — safe to call multiple times
 */

// ── Normalized event types (mirror the backend bridge) ──────────────────────

export interface GeminiSessionOpenedEvent {
  kind: 'session.opened'
  session_id: string
}

export interface GeminiTranscriptPartialEvent {
  kind: 'transcript.partial'
  text: string
  confidence: number
}

export interface GeminiTranscriptFinalEvent {
  kind: 'transcript.final'
  text: string
  confidence: number
  duration_ms: number
}

export interface GeminiSessionClosedEvent {
  kind: 'session.closed'
  reason: string
}

export interface GeminiBridgeErrorEvent {
  kind: 'error'
  code: string
  message: string
}

export type GeminiLiveEvent =
  | GeminiSessionOpenedEvent
  | GeminiTranscriptPartialEvent
  | GeminiTranscriptFinalEvent
  | GeminiSessionClosedEvent
  | GeminiBridgeErrorEvent

// ── Client options ───────────────────────────────────────────────────────────

export interface GeminiLiveClientOptions {
  /** WebSocket URL of the voice-agent backend, e.g. ws://localhost:8004/api/v1/ws/gemini-live */
  wsUrl: string
  /** Called for every interim transcript text update */
  onPartial: (text: string) => void
  /** Called once when ASR produces a final transcript */
  onFinal: (text: string) => void
  /** Called on any unrecoverable error */
  onError: (code: string, message: string) => void
  /** Called when the session closes (normally or after error) */
  onClose: () => void
  /** Max ms to wait for mic permission before giving up (default 8 000) */
  micPermissionTimeoutMs?: number
  /** Max ms after start() before we expect at least one partial (default 20 000) */
  noTranscriptTimeoutMs?: number
}

// ── Target sample rate sent to Gemini Live ───────────────────────────────────

const TARGET_SAMPLE_RATE = 16_000  // Hz — Gemini Live expects 16 kHz PCM16 LE
const FRAME_SIZE = 4_096           // samples per ScriptProcessor frame

// ── Client ───────────────────────────────────────────────────────────────────

export class GeminiLiveClient {
  private readonly opts: Required<GeminiLiveClientOptions>

  private ws: WebSocket | null = null
  private audioCtx: AudioContext | null = null
  private sourceNode: MediaStreamAudioSourceNode | null = null
  private processorNode: ScriptProcessorNode | null = null
  private stream: MediaStream | null = null
  private cleanedUp = false
  private noTranscriptTimer: ReturnType<typeof setTimeout> | null = null

  constructor(opts: GeminiLiveClientOptions) {
    this.opts = {
      micPermissionTimeoutMs: 8_000,
      noTranscriptTimeoutMs: 20_000,
      ...opts,
    }
  }

  /** Request mic, open WebSocket, start streaming. Throws on mic permission denial. */
  async start(): Promise<void> {
    if (this.cleanedUp) throw new Error('GeminiLiveClient already cleaned up')

    // Request mic with a timeout
    const stream = await this._requestMic()
    this.stream = stream

    // Open WebSocket to backend
    const ws = new WebSocket(this.opts.wsUrl)
    this.ws = ws
    ws.binaryType = 'arraybuffer'

    await new Promise<void>((resolve, reject) => {
      ws.onopen = () => resolve()
      ws.onerror = () => reject(new Error('WebSocket failed to connect'))
      // 5 s connect timeout
      const t = setTimeout(() => reject(new Error('WebSocket connect timeout')), 5_000)
      ws.onopen = () => { clearTimeout(t); resolve() }
    })

    ws.onmessage = (ev) => this._handleMessage(ev)
    ws.onclose = () => {
      if (!this.cleanedUp) this.opts.onClose()
      this._releaseAudio()
    }
    ws.onerror = () => {
      this.opts.onError('ws_error', 'WebSocket connection lost')
      this.cleanup()
    }

    // Start audio capture pipeline
    this._startAudioCapture(stream)

    // No-transcript watchdog
    this.noTranscriptTimer = setTimeout(() => {
      if (!this.cleanedUp) {
        this.opts.onError('no_transcript', 'No speech detected — check microphone')
        this.cleanup()
      }
    }, this.opts.noTranscriptTimeoutMs)
  }

  /** Signal end of speech to the server, then release resources. */
  stop(): void {
    this._sendStop()
    this._releaseAudio()
  }

  /** Idempotent cleanup — safe to call multiple times. */
  cleanup(): void {
    if (this.cleanedUp) return
    this.cleanedUp = true
    this._clearNoTranscriptTimer()
    this._sendStop()
    this._releaseAudio()
    if (this.ws && this.ws.readyState <= WebSocket.OPEN) {
      try { this.ws.close() } catch { /* ignore */ }
    }
    this.ws = null
  }

  // ── Private ────────────────────────────────────────────────────────────────

  private async _requestMic(): Promise<MediaStream> {
    const permitted = new Promise<MediaStream>((resolve, reject) => {
      const t = setTimeout(
        () => reject(new Error('Microphone permission timeout')),
        this.opts.micPermissionTimeoutMs,
      )
      navigator.mediaDevices
        .getUserMedia({ audio: { sampleRate: TARGET_SAMPLE_RATE, channelCount: 1, echoCancellation: true } })
        .then(s => { clearTimeout(t); resolve(s) })
        .catch(err => { clearTimeout(t); reject(err) })
    })
    return permitted
  }

  private _startAudioCapture(stream: MediaStream): void {
    // AudioContext resamples to TARGET_SAMPLE_RATE for us
    this.audioCtx = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE })
    this.sourceNode = this.audioCtx.createMediaStreamSource(stream)

    // ScriptProcessorNode is deprecated but has universal support without COOP headers.
    // An AudioWorklet version can be swapped in later without changing the WS protocol.
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    this.processorNode = this.audioCtx.createScriptProcessor(FRAME_SIZE, 1, 1)
    this.processorNode.onaudioprocess = (ev) => {
      if (this.cleanedUp || !this.ws || this.ws.readyState !== WebSocket.OPEN) return
      const float32 = ev.inputBuffer.getChannelData(0)
      const pcm16 = this._float32ToPcm16(float32)
      this.ws.send(pcm16.buffer)
    }

    this.sourceNode.connect(this.processorNode)
    this.processorNode.connect(this.audioCtx.destination)
  }

  private _float32ToPcm16(float32: Float32Array): Int16Array {
    const pcm = new Int16Array(float32.length)
    for (let i = 0; i < float32.length; i++) {
      const s = Math.max(-1, Math.min(1, float32[i]))
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
    }
    return pcm
  }

  private _handleMessage(ev: MessageEvent): void {
    let data: GeminiLiveEvent
    try {
      data = JSON.parse(ev.data as string) as GeminiLiveEvent
    } catch {
      return
    }

    switch (data.kind) {
      case 'transcript.partial':
        this._clearNoTranscriptTimer()  // we have speech — cancel the no-speech timeout
        this.opts.onPartial(data.text)
        break
      case 'transcript.final':
        this._clearNoTranscriptTimer()
        this.opts.onFinal(data.text)
        break
      case 'session.closed':
        if (!this.cleanedUp) this.opts.onClose()
        this.cleanup()
        break
      case 'error':
        this.opts.onError(data.code, data.message)
        this.cleanup()
        break
    }
  }

  private _sendStop(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try { this.ws.send(JSON.stringify({ type: 'stop' })) } catch { /* ignore */ }
    }
  }

  private _releaseAudio(): void {
    try { this.processorNode?.disconnect() } catch { /* ignore */ }
    try { this.sourceNode?.disconnect() } catch { /* ignore */ }
    try { this.audioCtx?.close() } catch { /* ignore */ }
    this.stream?.getTracks().forEach(t => t.stop())
    this.processorNode = null
    this.sourceNode = null
    this.audioCtx = null
    this.stream = null
  }

  private _clearNoTranscriptTimer(): void {
    if (this.noTranscriptTimer) {
      clearTimeout(this.noTranscriptTimer)
      this.noTranscriptTimer = null
    }
  }
}

// ── WebSocket URL helper ─────────────────────────────────────────────────────

/**
 * Build the backend WebSocket URL from the env var.
 * NEXT_PUBLIC_VOICE_AGENT_WS_URL defaults to ws://localhost:8004
 */
export function buildGeminiWsUrl(): string {
  const base =
    process.env.NEXT_PUBLIC_VOICE_AGENT_WS_URL ??
    (typeof window !== 'undefined'
      ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
      : 'ws://localhost:8004')
  // If the env var is an HTTP URL, convert to WS
  const wsBase = base.replace(/^http/, 'ws')
  return `${wsBase}/api/v1/ws/gemini-live`
}
