/**
 * VoiceTurnController — owns all resources for one active voice turn.
 *
 * Manages the state machine, timers, AbortController, SpeechRecognition,
 * and TTS playback for exactly one turn. Call cleanup() on any success or
 * failure path to guarantee all resources are released.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

const LISTENING_MAX_MS    = 12_000
const SILENCE_AFTER_MS    = 2_000
const BACKEND_TIMEOUT_MS  = 20_000
const MAX_INTERIM_CHARS   = 500
const TTS_EXTRA_BUFFER_MS = 5_000
const TTS_MAX_PLAYBACK_MS = 120_000
const WHOLE_TURN_MAX_MS   = 150_000

function clampMs(ms: number, minMs: number, maxMs: number): number {
  return Math.min(Math.max(ms, minMs), maxMs)
}

function chunkId(bytes: Uint8Array, offset: number): string {
  return String.fromCharCode(bytes[offset], bytes[offset + 1], bytes[offset + 2], bytes[offset + 3])
}

function estimateWavDurationMs(bytes: Uint8Array): number | null {
  if (bytes.length < 44) return null
  if (chunkId(bytes, 0) !== 'RIFF' || chunkId(bytes, 8) !== 'WAVE') return null

  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  let byteRate = 0
  let dataBytes = 0
  let offset = 12

  while (offset + 8 <= bytes.length) {
    const id = chunkId(bytes, offset)
    const size = view.getUint32(offset + 4, true)
    const body = offset + 8

    if (id === 'fmt ' && body + 16 <= bytes.length) {
      byteRate = view.getUint32(body + 8, true)
    } else if (id === 'data') {
      dataBytes = size
    }

    offset = body + size + (size % 2)
  }

  if (byteRate <= 0 || dataBytes <= 0) return null
  return Math.ceil((dataBytes / byteRate) * 1_000)
}

export type TurnState =
  | 'ready'
  | 'listening'
  | 'finalizing_stt'
  | 'thinking'
  | 'preparing_tts'
  | 'speaking'
  | 'error_recoverable'

export interface TurnDiagnostics {
  turnId: string
  transitions: string[]
  sttStart: number | null
  sttEnd: number | null
  sttError: string | null
  backendStart: number | null
  backendEnd: number | null
  backendError: string | null
  ttsProvider: string | null
  ttsStart: number | null
  ttsEnd: number | null
  ttsError: string | null
  cleanupReason: string | null
}

export class VoiceTurnController {
  readonly turnId: string
  private _state: TurnState = 'ready'
  private recognition: any = null
  private abortController: AbortController | null = null
  private audioEl: HTMLAudioElement | null = null
  private timers: ReturnType<typeof setTimeout>[] = []
  private silenceTimer: ReturnType<typeof setTimeout> | null = null
  private listeningTimer: ReturnType<typeof setTimeout> | null = null
  private ttsTimer: ReturnType<typeof setTimeout> | null = null
  private wholeTurnTimer: ReturnType<typeof setTimeout> | null = null
  private speechUtterance: SpeechSynthesisUtterance | null = null
  private speechResumeTimer: ReturnType<typeof setInterval> | null = null
  private cleanedUp = false
  readonly diag: TurnDiagnostics

  constructor(
    private readonly onStateChange: (s: TurnState) => void,
    private readonly onInterimText: (t: string) => void,
    private readonly onFinalText:   (t: string) => void,
    private readonly onError:       (msg: string) => void,
  ) {
    this.turnId = `turn-${Date.now()}`
    this.diag = {
      turnId: this.turnId,
      transitions: [],
      sttStart: null, sttEnd: null, sttError: null,
      backendStart: null, backendEnd: null, backendError: null,
      ttsProvider: null, ttsStart: null, ttsEnd: null, ttsError: null,
      cleanupReason: null,
    }
    this.wholeTurnTimer = setTimeout(() => {
      if (this._state === 'listening' || this._state === 'finalizing_stt') {
        this.diag.sttError ??= 'whole_turn_timeout'
      } else if (this._state === 'thinking') {
        this.diag.backendError ??= 'whole_turn_timeout'
      } else if (this._state === 'preparing_tts' || this._state === 'speaking') {
        this.diag.ttsError ??= 'whole_turn_timeout'
      }
      this.cleanup('whole_turn_timeout')
    }, WHOLE_TURN_MAX_MS)
  }

  get state(): TurnState { return this._state }

  private transition(next: TurnState) {
    this.diag.transitions.push(`${this._state}->${next}`)
    this._state = next
    this.onStateChange(next)
  }

  // ── STT ──────────────────────────────────────────────────────────────────────

  /** Start browser speech recognition. Returns false if SR is unsupported. */
  startSTT(): boolean {
    const w = (typeof window !== 'undefined' ? window : {}) as any
    const SR: any = w.SpeechRecognition ?? w.webkitSpeechRecognition
    if (!SR) {
      this.transition('listening')
      return false
    }

    // Cancel any in-progress TTS before listening
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }

    const rec = new SR()
    rec.continuous     = true
    rec.interimResults = true
    rec.lang           = 'en-US'
    this.recognition   = rec

    let finalText = ''
    let hasSpeech = false

    rec.onresult = (event: any) => {
      if (this.cleanedUp) return
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const r = event.results[i]
        if (r.isFinal) {
          finalText += (r[0].transcript as string) + ' '
        } else {
          interim += r[0].transcript as string
        }
      }
      const combined = (finalText + interim).trim().slice(0, MAX_INTERIM_CHARS)
      if (combined && !hasSpeech) {
        hasSpeech = true
        this.resetSilenceTimer(() => this.stopSTT())
      } else if (hasSpeech) {
        this.resetSilenceTimer(() => this.stopSTT())
      }
      this.onInterimText(combined)
    }

    rec.onend = () => {
      if (this.cleanedUp) return
      this.diag.sttEnd = Date.now()
      this.clearListeningTimer()
      this.clearSilenceTimer()
      const spoken = finalText.trim()
      this.recognition = null
      this.transition('finalizing_stt')
      if (spoken) {
        this.onFinalText(spoken)
      } else {
        this.transition('error_recoverable')
        this.onError('No speech detected')
      }
    }

    rec.onerror = (e: any) => {
      if (this.cleanedUp) return
      const errName: string = (e as any).error ?? 'unknown'
      this.diag.sttError = errName
      this.clearListeningTimer()
      this.clearSilenceTimer()
      this.recognition = null
      this.transition('error_recoverable')
      this.onError(`STT error: ${errName}`)
    }

    rec.start()
    this.diag.sttStart = Date.now()
    this.transition('listening')

    // Max-duration watchdog
    this.listeningTimer = setTimeout(() => {
      if (this._state === 'listening') {
        this.diag.sttError = 'max_duration'
        this.stopSTT()
      }
    }, LISTENING_MAX_MS)

    return true
  }

  stopSTT() {
    this.clearListeningTimer()
    this.clearSilenceTimer()
    if (this.recognition) {
      try { this.recognition.stop() } catch { /* ignore */ }
      // onend fires asynchronously → calls onFinalText or onError
    }
  }

  // ── Backend ───────────────────────────────────────────────────────────────────

  /** Enter thinking state and return an AbortSignal wired to BACKEND_TIMEOUT_MS. */
  startBackend(): AbortSignal {
    this.abortController = new AbortController()
    this.diag.backendStart = Date.now()
    this.transition('thinking')
    const timer = setTimeout(() => {
      if (this.cleanedUp) return
      this.abortController?.abort()
      this.diag.backendError = 'timeout'
    }, BACKEND_TIMEOUT_MS)
    this.timers.push(timer)
    return this.abortController.signal
  }

  backendSuccess() {
    this.diag.backendEnd = Date.now()
    this.transition('preparing_tts')
  }

  backendFailed(reason: string) {
    this.diag.backendEnd   = Date.now()
    this.diag.backendError = reason
    this.transition('error_recoverable')
  }

  // ── TTS ───────────────────────────────────────────────────────────────────────

  /** Play audio from a base64 string. Calls onDone when finished or on error. */
  async speakAudio(
    audioBase64: string,
    mimeType: string,
    onDone: () => void,
    provider = 'audio',
  ) {
    this.diag.ttsProvider = provider
    this.diag.ttsStart    = Date.now()

    let binary = ''
    try {
      binary = atob(audioBase64)
    } catch {
      this.diag.ttsError = 'bad_base64_audio'
      onDone()
      return
    }
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
    if (bytes.length === 0) {
      this.diag.ttsError = 'empty_audio'
      onDone()
      return
    }
    const blob = new Blob([bytes], { type: mimeType || 'audio/wav' })
    const url = URL.createObjectURL(blob)

    const el = new Audio(url)
    this.audioEl = el

    let done = false
    const finish = (reason: string) => {
      if (this.cleanedUp) return
      if (done) return
      done = true
      this.clearTtsTimer()
      try { el.pause() } catch { /* ignore */ }
      if (this.audioEl === el) this.audioEl = null
      if (reason === 'ended') this.diag.ttsEnd = Date.now()
      else this.diag.ttsError = reason
      URL.revokeObjectURL(url)
      onDone()
    }

    const armWatchdog = (reason: string, ms: number) => {
      this.clearTtsTimer()
      this.ttsTimer = setTimeout(() => finish(reason), ms)
    }

    const markPlaybackStarted = () => {
      if (this.cleanedUp) return
      if (this._state === 'preparing_tts') this.transition('speaking')
    }

    // First watchdog: if Chrome accepts play() but never emits playback events,
    // do not leave the turn in "preparing_tts" until the whole-turn timeout.
    armWatchdog('audio_start_timeout', 5_000)

    el.onended = () => {
      finish('ended')
    }
    el.onerror = () => {
      finish('audio_error')
    }
    el.onplaying = () => {
      markPlaybackStarted()
      const wavDurationMs = estimateWavDurationMs(bytes)
      const durationMs = Number.isFinite(el.duration) && el.duration > 0
        ? Math.ceil(el.duration * 1_000) + TTS_EXTRA_BUFFER_MS
        : (wavDurationMs ?? 30_000) + TTS_EXTRA_BUFFER_MS
      armWatchdog('audio_end_timeout', clampMs(durationMs, 3_000, TTS_MAX_PLAYBACK_MS))
    }
    el.onloadedmetadata = () => {
      if (!done && Number.isFinite(el.duration) && el.duration > 0) {
        const durationMs = Math.ceil(el.duration * 1_000) + TTS_EXTRA_BUFFER_MS
        armWatchdog('audio_end_timeout', clampMs(durationMs, 3_000, TTS_MAX_PLAYBACK_MS))
      }
    }
    try {
      await el.play()
      markPlaybackStarted()
    } catch {
      finish('play_rejected')
    }
  }

  /**
   * Browser speechSynthesis with a caller-supplied approved voice.
   * Pass `null` to use the browser default (not recommended — caller should guard).
   * Calls onDone when finished, errored, or timed out.
   */
  speakBrowser(
    text: string,
    voice: SpeechSynthesisVoice | null,
    onDone: () => void,
    opts?: { rate?: number; pitch?: number },
  ) {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      this.diag.ttsError = 'speechSynthesis_unavailable'
      console.warn('[ClaimVoice:TTS] speechSynthesis unavailable')
      onDone()
      return
    }
    this.diag.ttsStart = Date.now()
    window.speechSynthesis.cancel()

    const utter = new SpeechSynthesisUtterance(text)
    this.speechUtterance = utter
    utter.rate = opts?.rate ?? 0.92
    utter.pitch = opts?.pitch ?? 1
    utter.volume = 1

    // Use the earlier, simpler browser strategy: prefer natural local/OS English
    // voices, then en-US, then any English voice. The caller-provided voice is
    // only a final fallback because specific Google browser voices can queue
    // without producing audible playback on some Chrome/macOS setups.
    const voices = window.speechSynthesis.getVoices()
    const preferred = voices.find(v =>
      v.lang.startsWith('en') &&
      /neural|natural|premium|enhanced|samantha|karen|daniel/i.test(v.name)
    ) ?? voices.find(v => v.lang === 'en-US')
      ?? voices.find(v => v.lang.startsWith('en'))
      ?? voice
    if (preferred) utter.voice = preferred
    this.diag.ttsProvider = preferred?.name ?? 'browser'
    console.debug('[ClaimVoice:TTS] speakBrowser simple', {
      provider: this.diag.ttsProvider,
      textLength: text.length,
      voicesCount: voices.length,
      speaking: window.speechSynthesis.speaking,
      pending: window.speechSynthesis.pending,
      paused: window.speechSynthesis.paused,
    })

    let done = false
    const finish = (reason: string) => {
      if (this.cleanedUp) return
      if (done) return
      done = true
      this.clearSpeechResumeTimer()
      this.speechUtterance = null
      this.clearTtsTimer()
      if (reason !== 'ended') this.diag.ttsError = reason
      else this.diag.ttsEnd = Date.now()
      console.debug('[ClaimVoice:TTS] speakBrowser finished', {
        reason,
        provider: this.diag.ttsProvider,
        ttsError: this.diag.ttsError,
        speaking: window.speechSynthesis.speaking,
        pending: window.speechSynthesis.pending,
        paused: window.speechSynthesis.paused,
      })
      onDone()
    }

    const estimatedMs = Math.max(text.length * 300, 3000) + TTS_EXTRA_BUFFER_MS
    this.ttsTimer = setTimeout(() => {
      window.speechSynthesis.cancel()
      finish('timeout')
    }, estimatedMs)

    utter.onend = () => finish('ended')
    utter.onerror = (event) => {
      if (this.cleanedUp && event.error === 'canceled') return
      console.warn('[ClaimVoice:TTS] utterance error', { error: event.error })
      finish('playback_error')
    }
    window.speechSynthesis.speak(utter)
    window.speechSynthesis.resume()
    this.speechResumeTimer = setInterval(() => {
      if (done || this.cleanedUp) return
      window.speechSynthesis.resume()
    }, 1_000)
  }

  stopTTS() {
    this.clearTtsTimer()
    this.clearSpeechResumeTimer()
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }
    this.speechUtterance = null
    if (this.audioEl) {
      this.audioEl.pause()
      this.audioEl.removeAttribute('src')
      try { this.audioEl.load() } catch { /* ignore */ }
      this.audioEl = null
    }
  }

  // ── cleanup ───────────────────────────────────────────────────────────────────

  /** Release all resources and transition back to ready. Safe to call multiple times. */
  cleanup(reason: string) {
    if (this.cleanedUp) return
    this.cleanedUp = true
    this.diag.cleanupReason = reason
    this.clearWholeTurnTimer()
    this.clearListeningTimer()
    this.clearSilenceTimer()
    this.clearTtsTimer()
    this.timers.forEach(t => clearTimeout(t))
    this.timers = []
    if (this.recognition) {
      try { this.recognition.stop() } catch { /* ignore */ }
      this.recognition = null
    }
    this.abortController?.abort()
    this.abortController = null
    this.stopTTS()
    // Log diagnostics to console for observability
    console.debug('[VoiceTurn]', this.turnId, this.diag)
    this.transition('ready')
  }

  // ── private timer helpers ─────────────────────────────────────────────────────

  private resetSilenceTimer(cb: () => void) {
    this.clearSilenceTimer()
    this.silenceTimer = setTimeout(cb, SILENCE_AFTER_MS)
  }
  private clearSilenceTimer() {
    if (this.silenceTimer) { clearTimeout(this.silenceTimer); this.silenceTimer = null }
  }
  private clearListeningTimer() {
    if (this.listeningTimer) { clearTimeout(this.listeningTimer); this.listeningTimer = null }
  }
  private clearTtsTimer() {
    if (this.ttsTimer) { clearTimeout(this.ttsTimer); this.ttsTimer = null }
  }
  private clearSpeechResumeTimer() {
    if (this.speechResumeTimer) { clearInterval(this.speechResumeTimer); this.speechResumeTimer = null }
  }
  private clearWholeTurnTimer() {
    if (this.wholeTurnTimer) { clearTimeout(this.wholeTurnTimer); this.wholeTurnTimer = null }
  }
}
