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

export type TurnState =
  | 'ready'
  | 'listening'
  | 'finalizing_stt'
  | 'thinking'
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
      this.abortController?.abort()
      this.diag.backendError = 'timeout'
    }, BACKEND_TIMEOUT_MS)
    this.timers.push(timer)
    return this.abortController.signal
  }

  backendSuccess() {
    this.diag.backendEnd = Date.now()
    this.transition('speaking')
  }

  backendFailed(reason: string) {
    this.diag.backendEnd   = Date.now()
    this.diag.backendError = reason
    this.transition('error_recoverable')
  }

  // ── TTS ───────────────────────────────────────────────────────────────────────

  /** Play audio from a base64 string. Calls onDone when finished or on error. */
  async speakAudio(audioBase64: string, mimeType: string, onDone: () => void) {
    this.diag.ttsProvider = 'google'
    this.diag.ttsStart    = Date.now()

    const binary = atob(audioBase64)
    const bytes  = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
    const blob = new Blob([bytes], { type: mimeType })
    const url  = URL.createObjectURL(blob)

    const el = new Audio(url)
    this.audioEl = el

    this.ttsTimer = setTimeout(() => {
      el.pause()
      this.diag.ttsError = 'timeout'
      URL.revokeObjectURL(url)
      onDone()
    }, 30_000 + TTS_EXTRA_BUFFER_MS)

    el.onended = () => {
      this.clearTtsTimer()
      this.diag.ttsEnd = Date.now()
      URL.revokeObjectURL(url)
      onDone()
    }
    el.onerror = () => {
      this.clearTtsTimer()
      this.diag.ttsError = 'audio_error'
      URL.revokeObjectURL(url)
      onDone()
    }
    try {
      await el.play()
    } catch {
      this.clearTtsTimer()
      this.diag.ttsError = 'play_rejected'
      URL.revokeObjectURL(url)
      onDone()
    }
  }

  /** Browser speechSynthesis fallback. Calls onDone when finished or on error. */
  speakBrowser(text: string, onDone: () => void) {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      this.diag.ttsError = 'speechSynthesis_unavailable'
      onDone()
      return
    }
    this.diag.ttsProvider = 'browser'
    this.diag.ttsStart    = Date.now()
    window.speechSynthesis.cancel()

    const utter = new SpeechSynthesisUtterance(text)
    utter.rate  = 0.92

    // Pick best available English voice: prefer Neural/Natural/Premium/Enhanced,
    // then en-US, then any English. Falls back to browser default if none found.
    const voices = window.speechSynthesis.getVoices()
    if (voices.length > 0) {
      const preferred = voices.find(v =>
        v.lang.startsWith('en') &&
        /neural|natural|premium|enhanced|samantha|karen|daniel/i.test(v.name)
      ) ?? voices.find(v => v.lang === 'en-US')
        ?? voices.find(v => v.lang.startsWith('en'))
      if (preferred) utter.voice = preferred
    }

    let done = false
    const finish = (reason: string) => {
      if (done) return
      done = true
      this.clearTtsTimer()
      if (reason !== 'ended') this.diag.ttsError = reason
      else this.diag.ttsEnd = Date.now()
      onDone()
    }

    // Watchdog: ~300ms per char at 0.95 rate + buffer. Chrome onend is unreliable
    // so this watchdog is the primary recovery path for stuck playback.
    const estimatedMs = Math.max(text.length * 300, 3000) + TTS_EXTRA_BUFFER_MS
    this.ttsTimer = setTimeout(() => {
      window.speechSynthesis.cancel()
      finish('timeout')
    }, estimatedMs)

    utter.onend   = () => finish('ended')
    utter.onerror = () => finish('playback_error')
    window.speechSynthesis.speak(utter)
  }

  stopTTS() {
    this.clearTtsTimer()
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }
    if (this.audioEl) {
      this.audioEl.pause()
      this.audioEl = null
    }
  }

  // ── cleanup ───────────────────────────────────────────────────────────────────

  /** Release all resources and transition back to ready. Safe to call multiple times. */
  cleanup(reason: string) {
    this.diag.cleanupReason = reason
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
}
