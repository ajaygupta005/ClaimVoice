'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Mic, MicOff, Send, CheckCircle2, Loader2, Circle, ShieldCheck, Bot, User, ChevronDown, RotateCcw, Volume2,
} from 'lucide-react'
import { type VoiceTurn, type VoiceStatus } from '@/lib/mock-data'
import { runMockPipeline, type BackendStatus, type LedStatus } from '@/lib/mock-pipeline'
import { sendVoiceAgentQuestion, fetchRuntimeStatus, type VoiceRuntimeStatus, type EvidenceItem, type RagStatusKind } from '@/lib/voice-agent-client'
import EvidencePanel from '@/components/EvidencePanel'
import { GeminiLiveClient, buildGeminiWsUrl, cvDebug } from '@/lib/gemini-live-client'
import { VoiceTurnController } from '@/lib/voice-turn-controller'
import { synthesizeSpeech, synthesizeGeminiSpeech } from '@/lib/tts-client'

// ── Waveform ──────────────────────────────────────────────────────────────────

function Waveform({ active }: { active: boolean }) {
  return (
    <div className="flex items-end gap-[2px] h-5">
      {[0.4, 0.7, 1, 0.6, 0.9, 0.5, 0.8, 0.45, 0.7].map((h, i) => (
        <div
          key={i}
          className={`w-[3px] rounded-full transition-all duration-300 ${active ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'}`}
          style={{
            height: active ? `${h * 20}px` : '3px',
            animation: active ? `wave 0.8s ease-in-out ${i * 70}ms infinite alternate` : 'none',
          }}
        />
      ))}
      <style>{`@keyframes wave { from { transform: scaleY(0.3); } to { transform: scaleY(1); } }`}</style>
    </div>
  )
}

// ── Status pill ───────────────────────────────────────────────────────────────

function StatusPill({ status }: { status: VoiceStatus }) {
  const map: Record<VoiceStatus, { label: string; cls: string; dot: string }> = {
    ready:            { label: 'Ready',       cls: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',    dot: 'bg-slate-400' },
    listening:        { label: 'Listening',   cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',     dot: 'bg-blue-500 animate-pulse' },
    finalizing_stt:   { label: 'Finalizing…', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',     dot: 'bg-blue-400' },
    thinking:         { label: 'Thinking',    cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300', dot: 'bg-amber-500 animate-pulse' },
    preparing_tts:    { label: 'Preparing voice', cls: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300', dot: 'bg-violet-500 animate-pulse' },
    speaking:         { label: 'Speaking',    cls: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300', dot: 'bg-green-500 animate-pulse' },
    error_recoverable:{ label: 'Error',       cls: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',         dot: 'bg-red-500' },
  }
  const { label, cls, dot } = map[status]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {(status === 'thinking' || status === 'preparing_tts') && <Loader2 size={10} className="animate-spin -ml-0.5" />}
      {label}
    </span>
  )
}

// ── Transcript bubble ─────────────────────────────────────────────────────────

function Bubble({ turn }: { turn: VoiceTurn }) {
  const isMember = turn.role === 'member'
  return (
    <div className={`flex items-end gap-1.5 ${isMember ? 'flex-row-reverse' : ''}`}>
      <div className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${
        isMember ? 'bg-blue-100 dark:bg-blue-900/40' : 'bg-slate-100 dark:bg-slate-800'
      }`}>
        {isMember
          ? <User size={11} className="text-blue-600 dark:text-blue-400" />
          : <Bot  size={11} className="text-slate-500 dark:text-slate-400" />}
      </div>
      <div className={`max-w-[82%] px-3 py-2 rounded-2xl text-xs leading-relaxed ${
        isMember
          ? 'bg-blue-500 text-white rounded-br-sm'
          : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 rounded-bl-sm'
      }`}>
        {turn.text}
      </div>
    </div>
  )
}

// ── Horizontal pipeline ───────────────────────────────────────────────────────

type StepState = 'completed' | 'running' | 'pending'
interface PipeStep { title: string; detail: string; state: StepState }

function PipelineStep({ step }: { step: PipeStep }) {
  return (
    <div className="flex flex-col items-center gap-0.5 min-w-0 px-1">
      <div className="flex items-center gap-1">
        {step.state === 'completed' && <CheckCircle2 size={11} className="text-green-500 shrink-0" />}
        {step.state === 'running'   && <Loader2      size={11} className="text-blue-500 animate-spin shrink-0" />}
        {step.state === 'pending'   && <Circle       size={11} className="text-slate-300 dark:text-slate-600 shrink-0" />}
        <span className={`text-[11px] font-semibold truncate ${
          step.state === 'completed' ? 'text-slate-700 dark:text-slate-200' :
          step.state === 'running'   ? 'text-blue-700 dark:text-blue-300'   :
                                       'text-slate-400 dark:text-slate-500'
        }`}>{step.title}</span>
      </div>
      <p className="text-[9px] text-slate-400 dark:text-slate-500 truncate w-full text-center leading-tight">
        {step.detail}
      </p>
    </div>
  )
}

// ── Pipeline step builder ─────────────────────────────────────────────────────

interface CompletedPipeDetails {
  identify: string
  understand: string
  check: string
  guard: string
  respond: string
}

function getPipelineSteps(
  status: VoiceStatus,
  completed?: CompletedPipeDetails,
): PipeStep[] {
  if (status === 'listening' || status === 'finalizing_stt') return [
    { title: 'Identify',   detail: 'Listening…',   state: 'running'   },
    { title: 'Understand', detail: 'Waiting',       state: 'pending'   },
    { title: 'Check',      detail: 'Waiting',       state: 'pending'   },
    { title: 'Guard',      detail: 'Waiting',       state: 'pending'   },
    { title: 'Respond',    detail: 'Waiting',       state: 'pending'   },
  ]
  if (status === 'thinking') return [
    { title: 'Identify',   detail: 'Member verified', state: 'completed' },
    { title: 'Understand', detail: 'Extracting…',     state: 'running'   },
    { title: 'Check',      detail: 'Querying…',       state: 'running'   },
    { title: 'Guard',      detail: 'Waiting',         state: 'pending'   },
    { title: 'Respond',    detail: 'Waiting',         state: 'pending'   },
  ]
  if (status === 'preparing_tts') return [
    { title: 'Identify',   detail: completed?.identify ?? 'Member verified',       state: 'completed' },
    { title: 'Understand', detail: completed?.understand ?? 'Intent extracted',     state: 'completed' },
    { title: 'Check',      detail: completed?.check ?? 'Eligibility queried',       state: 'completed' },
    { title: 'Guard',      detail: completed?.guard ?? 'Claims grounded',           state: 'completed' },
    { title: 'Respond',    detail: 'Preparing Skylar…',                             state: 'running'   },
  ]
  const d = completed ?? {
    identify:   'Member verified',
    understand: 'Intent extracted',
    check:      'Eligibility queried',
    guard:      'Claims grounded',
    respond:    'Answer delivered',
  }
  if (status === 'speaking') return [
    { title: 'Identify',   detail: d.identify,   state: 'completed' },
    { title: 'Understand', detail: d.understand, state: 'completed' },
    { title: 'Check',      detail: d.check,      state: 'completed' },
    { title: 'Guard',      detail: d.guard,      state: 'completed' },
    { title: 'Respond',    detail: 'Speaking…',  state: 'running'   },
  ]
  return [
    { title: 'Identify',   detail: d.identify,   state: 'completed' },
    { title: 'Understand', detail: d.understand, state: 'completed' },
    { title: 'Check',      detail: d.check,      state: 'completed' },
    { title: 'Guard',      detail: d.guard,      state: 'completed' },
    { title: 'Respond',    detail: d.respond,    state: 'completed' },
  ]
}

// ── LED rail ──────────────────────────────────────────────────────────────────

function LedRow({ label, ledStatus }: { label: string; ledStatus: LedStatus }) {
  const dot: Record<LedStatus, string> = {
    connected: 'bg-green-500',
    demo:      'bg-slate-400 dark:bg-slate-500',
    degraded:  'bg-amber-400 animate-pulse',
    offline:   'bg-red-500',
  }
  return (
    <div className="flex items-center gap-1.5 py-[3px]">
      <span className={`shrink-0 w-1.5 h-1.5 rounded-full ${dot[ledStatus]}`} />
      <span className="text-[10px] text-slate-500 dark:text-slate-400 truncate leading-none">{label}</span>
    </div>
  )
}

// ── Runtime status row ────────────────────────────────────────────────────────

function RuntimeRow({ status }: { status: VoiceRuntimeStatus }) {
  const { runtime, model, voice, note } = status
  const dotCls =
    runtime === 'gemini-live-configured' ? 'bg-violet-500'  :
    runtime === 'gemini-live-unavailable'? 'bg-amber-400 animate-pulse' :
    runtime === 'fallback'               ? 'bg-red-400'     :
                                           'bg-slate-400 dark:bg-slate-500'
  const label =
    runtime === 'gemini-live-configured'  ? 'Gemini Live configured' :
    runtime === 'gemini-live-unavailable' ? 'Gemini unavailable'     :
    runtime === 'fallback'                ? 'Backend offline'        :
                                            'Browser voice'
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center gap-1.5 py-[3px]">
        <span className={`shrink-0 w-1.5 h-1.5 rounded-full ${dotCls}`} />
        <span className="text-[10px] text-slate-500 dark:text-slate-400 truncate leading-none">{label}</span>
      </div>
      {(model || voice) && (
        <span className="text-[9px] text-slate-400 dark:text-slate-500 pl-3 truncate">
          {[model, voice].filter(Boolean).join(' · ')}
        </span>
      )}
      {note && (
        <span className="text-[9px] text-slate-300 dark:text-slate-600 pl-3 truncate" title={note}>
          {note.length > 30 ? note.slice(0, 28) + '…' : note}
        </span>
      )}
    </div>
  )
}

// ── RAG readiness row (Component 71) ─────────────────────────────────────────

function RagStatusRow({ status }: { status: VoiceRuntimeStatus }) {
  const ragStatus = status.rag_status ?? 'unreachable'
  const chunksCount = status.rag_chunks_count ?? 0

  const dotCls: Record<RagStatusKind, string> = {
    ready:          'bg-green-500',
    key_missing:    'bg-red-500',
    table_missing:  'bg-red-500',
    empty:          'bg-amber-400 animate-pulse',
    no_plan_links:  'bg-amber-400 animate-pulse',
    db_error:       'bg-red-400',
    unreachable:    'bg-slate-300 dark:bg-slate-600',
  }
  const label: Record<RagStatusKind, string> = {
    ready:          `RAG ready (${chunksCount})`,
    key_missing:    'RAG key missing',
    table_missing:  'RAG table missing',
    empty:          'RAG empty',
    no_plan_links:  'RAG no plans',
    db_error:       'RAG DB error',
    unreachable:    'RAG unavailable',
  }

  return (
    <div className="flex items-center gap-1.5 py-[3px]" data-testid="rag-status-row">
      <span className={`shrink-0 w-1.5 h-1.5 rounded-full ${dotCls[ragStatus]}`} />
      <span className="text-[10px] text-slate-500 dark:text-slate-400 truncate leading-none">
        {label[ragStatus]}
      </span>
    </div>
  )
}

// ── Approved browser voices ───────────────────────────────────────────────────

const APPROVED_BROWSER_VOICES = [
  { name: 'Google UK English Male',   lang: 'en-GB', pitch: 0.85 },
  { name: 'Google UK English Female', lang: 'en-GB', pitch: 0.95 },
] as const

const VOICE_PREVIEW_PHRASE = 'ClaimVoice is ready. I will answer using verified plan facts.'

type BrowserVoiceResolution = {
  voice: SpeechSynthesisVoice | null
  label: string
  pitch: number
}

type SpeechSynthesisDump = {
  supported: boolean
  speaking: boolean
  pending: boolean
  paused: boolean
  voicesCount: number
  resolved: {
    label: string
    pitch: number
    voice: {
      name: string
      lang: string
      default: boolean
      localService: boolean
    } | null
  }
  voices: string[]
}

declare global {
  interface Window {
    __claimVoiceTtsDump?: () => SpeechSynthesisDump
  }
}

// Resolve a usable browser voice at speak-time (not from stale React state).
// Prefers approved Google UK voices, then any en-US, then any English.
function resolveBrowserVoice(): BrowserVoiceResolution {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    return { voice: null, label: 'Browser default', pitch: 0.9 }
  }
  const voices = window.speechSynthesis.getVoices()
  for (const approved of APPROVED_BROWSER_VOICES) {
    const match = voices.find(v => v.name === approved.name)
    if (match) return { voice: match, label: match.name, pitch: approved.pitch }
  }
  const english = voices.find(v => v.lang === 'en-US')
    ?? voices.find(v => v.lang.startsWith('en'))
    ?? null
  return { voice: english, label: english?.name ?? 'Browser default', pitch: 0.9 }
}

function getSpeechSynthesisDump(): SpeechSynthesisDump {
  const synth = typeof window !== 'undefined' ? window.speechSynthesis : null
  const voices = synth?.getVoices() ?? []
  const resolved = resolveBrowserVoice()
  return {
    supported: Boolean(synth),
    speaking: synth?.speaking ?? false,
    pending: synth?.pending ?? false,
    paused: synth?.paused ?? false,
    voicesCount: voices.length,
    resolved: {
      label: resolved.label,
      pitch: resolved.pitch,
      voice: resolved.voice
        ? {
            name: resolved.voice.name,
            lang: resolved.voice.lang,
            default: resolved.voice.default,
            localService: resolved.voice.localService,
          }
        : null,
    },
    voices: voices.map(v => `${v.name} | ${v.lang} | default=${v.default} | local=${v.localService}`),
  }
}

function logTtsDump(event: string): SpeechSynthesisDump {
  const dump = getSpeechSynthesisDump()
  console.debug(`[ClaimVoice:TTS] ${event}`, dump)
  return dump
}

// ── Constants ─────────────────────────────────────────────────────────────────

const VOICE_QUESTIONS = [
  'Is an MRI of the brain covered?',
  'What is my urgent care copay?',
  'Is lisinopril on my formulary?',
  'Find a cardiologist near me who is in network',
  'Where can I get an x-ray?',
  'What can you do?',
]

const DEFAULT_BACKENDS: BackendStatus[] = [
  { label: 'Voice Agent API', detail: '',          status: 'demo' },
  { label: 'STT: Browser',    detail: '',          status: 'demo' },
  { label: 'TTS: Cartesia Skylar', detail: 'inactive', status: 'demo' },
  { label: 'Guard',           detail: '',          status: 'demo' },
  { label: 'Claude answer',   detail: 'mock',      status: 'demo' },
]

// Gemini Live is useful for streaming STT, but using it as "read this exact
// answer aloud" is not deterministic: it can paraphrase because it is a
// conversational model, not a dedicated TTS endpoint. Keep it opt-in only.
const ENABLE_GEMINI_TTS = process.env.NEXT_PUBLIC_ENABLE_GEMINI_TTS === '1'
// Gemini STT remains experimental. The default demo path uses browser STT so
// stop/final-transcript races in Gemini Live cannot strand the user.
const ENABLE_GEMINI_STT = process.env.NEXT_PUBLIC_ENABLE_GEMINI_STT === '1'

function isTtsBackendLabel(label: string): boolean {
  return label === 'Voice' || label === 'TTS' || label.startsWith('Voice:') || label.startsWith('TTS:')
}

// ── Examples drawer ───────────────────────────────────────────────────────────

function ExamplesDrawer({
  onPick, disabled,
}: {
  onPick: (q: string) => void
  disabled: boolean
}) {
  const [open, setOpen] = useState(false)
  return (
    <div className="px-3 pb-1 shrink-0">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1 text-[10px] text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
      >
        <ChevronDown
          size={11}
          className={`transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
        Examples
      </button>
      {open && (
        <div className="mt-1.5 flex flex-col gap-1">
          {VOICE_QUESTIONS.map(q => (
            <button
              key={q}
              onClick={() => { setOpen(false); onPick(q) }}
              disabled={disabled}
              className="text-left text-[11px] px-2.5 py-1.5 rounded-md border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-blue-50 hover:border-blue-200 dark:hover:bg-blue-900/20 dark:hover:border-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function VoiceAssistantUI() {
  const [status,       setStatus]      = useState<VoiceStatus>('ready')
  const [turns,        setTurns]       = useState<VoiceTurn[]>([])
  const [input,        setInput]       = useState('')
  const [backends,     setBackends]    = useState<BackendStatus[]>(DEFAULT_BACKENDS)
  const [guardPassed,  setGuardPassed] = useState<boolean | null>(null)
  const [pipeDetails,  setPipeDetails] = useState<CompletedPipeDetails | undefined>(undefined)
  const [usedFallback, setUsedFallback] = useState(false)
  const [composerMode, setComposerMode] = useState<string>('mock')
  const [interimText,  setInterimText] = useState('')
  const [evidence,     setEvidence]    = useState<EvidenceItem[]>([])
  const [ragSource,    setRagSource]   = useState<string | undefined>(undefined)

  // ── Voice runtime selector (Component 50) ───────────────────────────────────
  const [runtimeStatus, setRuntimeStatus] = useState<VoiceRuntimeStatus | null>(null)

  useEffect(() => {
    fetchRuntimeStatus().then(setRuntimeStatus).catch(() => {/* swallowed — fetchRuntimeStatus never throws */})
  }, [])

  // ── Browser voice discovery ──────────────────────────────────────────────────
  const [selectedVoice, setSelectedVoice] = useState<SpeechSynthesisVoice | null>(null)
  const [voiceLabel,    setVoiceLabel]    = useState<string>('Voice unavailable')
  const [isPreviewing,  setIsPreviewing]  = useState(false)
  const speechPrimedRef = useRef(false)

  const refreshVoices = useCallback(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return
    const all = window.speechSynthesis.getVoices()
    for (const approved of APPROVED_BROWSER_VOICES) {
      const match = all.find(v => v.name === approved.name)
      if (match) {
        setSelectedVoice(match)
        setVoiceLabel(`Voice: ${match.name}`)
        return
      }
    }
    setSelectedVoice(null)
    setVoiceLabel('Voice unavailable')
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return
    refreshVoices()
    window.__claimVoiceTtsDump = () => logTtsDump('manual_dump')
    window.speechSynthesis.addEventListener('voiceschanged', refreshVoices)
    return () => {
      window.speechSynthesis.removeEventListener('voiceschanged', refreshVoices)
      window.speechSynthesis.cancel()
      delete window.__claimVoiceTtsDump
    }
  }, [refreshVoices])

  const primeSpeechSynthesis = useCallback((reason: string) => {
    if (speechPrimedRef.current) return
    if (typeof window === 'undefined' || !window.speechSynthesis) return
    const utter = new SpeechSynthesisUtterance('ready')
    utter.volume = 0
    utter.rate = 1
    utter.pitch = 1
    utter.onstart = () => {
      speechPrimedRef.current = true
      console.debug('[ClaimVoice:TTS] speechSynthesis primed', { reason })
    }
    utter.onend = () => {
      speechPrimedRef.current = true
    }
    utter.onerror = (event) => {
      console.warn('[ClaimVoice:TTS] speechSynthesis prime failed', { reason, error: event.error })
    }
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(utter)
    window.speechSynthesis.resume()
  }, [])

  // ── Preview voice ────────────────────────────────────────────────────────────
  async function handlePreviewVoice() {
    if (isPreviewing) return
    setIsPreviewing(true)
    try {
      if (isCartesiaTts) {
        const ttsData = await synthesizeSpeech({ text: VOICE_PREVIEW_PHRASE })
        if (ttsData?.audioBase64) {
          const ctrl = controllerRef.current ?? newController()
          await ctrl.speakAudio(ttsData.audioBase64, ttsData.mimeType, () => setIsPreviewing(false), ttsData.provider)
          return
        }
      }
      // Browser synthesis fallback (or Cartesia unavailable)
      if (typeof window === 'undefined' || !window.speechSynthesis) { setIsPreviewing(false); return }
      const resolved = resolveBrowserVoice()
      window.speechSynthesis.cancel()
      const utter = new SpeechSynthesisUtterance(VOICE_PREVIEW_PHRASE)
      if (resolved.voice) utter.voice = resolved.voice
      utter.rate = 0.9
      utter.pitch = resolved.pitch
      utter.onend = () => setIsPreviewing(false)
      utter.onerror = () => setIsPreviewing(false)
      window.speechSynthesis.speak(utter)
    } catch {
      setIsPreviewing(false)
    }
  }

  const controllerRef  = useRef<VoiceTurnController | null>(null)
  const geminiClientRef = useRef<GeminiLiveClient | null>(null)
  const transcriptRef  = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (transcriptRef.current)
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
  }, [turns])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      controllerRef.current?.cleanup('unmount')
      geminiClientRef.current?.cleanup()
    }
  }, [])

  // ── Gemini mic path ──────────────────────────────────────────────────────────

  function stopGeminiMic() {
    geminiClientRef.current?.stop()
    geminiClientRef.current = null
  }

  async function startGeminiMic() {
    // Tear down any running session first
    stopGeminiMic()
    controllerRef.current?.cleanup('gemini_start')

    setStatus('listening')
    setInterimText('')
    cvDebug('starting Gemini Live mic session')

    const client = new GeminiLiveClient({
      wsUrl: buildGeminiWsUrl(),
      onPartial: (text) => {
        cvDebug('stt partial', { len: text.length })
        setInterimText(text)
      },
      onFinal: (text) => {
        cvDebug('stt final', { len: text.length })
        setInterimText('')
        setStatus('finalizing_stt')
        // Hand final transcript to existing pipeline — same path as browser STT
        void runPipeline(text, 'voice')
      },
      onError: (code, message) => {
        cvDebug('gemini error', { code })
        console.warn('[ClaimVoice:GeminiLive] error', code, message)
        setInterimText('')
        setStatus('error_recoverable')
        geminiClientRef.current = null
      },
      onClose: () => {
        cvDebug('gemini session closed normally')
        // Session closed normally without a final — return to ready
        if (geminiClientRef.current) {
          geminiClientRef.current = null
          setStatus('ready')
        }
      },
    })
    geminiClientRef.current = client

    try {
      await client.start()
    } catch (err) {
      geminiClientRef.current = null
      setInterimText('')

      const isPermissionDenied =
        err instanceof Error &&
        (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError')

      if (isPermissionDenied) {
        console.warn('[ClaimVoice:GeminiLive] mic permission denied')
        setStatus('error_recoverable')
        return
      }

      console.warn('[ClaimVoice:GeminiLive] start failed, falling back to browser STT:', err)
      // Fall back to browser STT if available
      const ctrl = newController()
      const srOk = ctrl.startSTT()
      if (!srOk) {
        setStatus('error_recoverable')
        ctrl.cleanup('gemini_fallback_no_sr')
      }
    }
  }

  function newController(): VoiceTurnController {
    controllerRef.current?.cleanup('new_turn')
    // ctrl reference captured so the error handler can call cleanup on itself
    let ctrl: VoiceTurnController
    ctrl = new VoiceTurnController(
      (s) => setStatus(s as VoiceStatus),
      (t) => setInterimText(t),
      (text) => { void runPipeline(text, 'voice') },
      (msg) => {
        console.warn('[VoiceUI] STT error:', msg)
        setInterimText('')
        // cleanup transitions to ready via onStateChange
        ctrl.cleanup(`stt_error: ${msg}`)
      },
    )
    controllerRef.current = ctrl
    return ctrl
  }

  async function runPipeline(question: string, source: 'typed' | 'voice' | 'demo' = 'typed') {
    const ctrl = controllerRef.current ?? newController()
    // Snapshot turnId — any state update from an older turn is ignored
    const myTurnId = ctrl.turnId
    const signal   = ctrl.startBackend()
    const pipelineStart = Date.now()

    cvDebug('pipeline start', { source, questionLen: question.length })

    setInterimText('')
    setEvidence([])      // clear evidence from previous turn
    setRagSource(undefined)
    setTurns(p => [...p, { id: `m-${Date.now()}`, role: 'member', text: question, timestampMs: Date.now() }])

    let answerText = ''

    // Guard: reject stale responses if a new turn started while we were awaiting
    const isStale = () => controllerRef.current?.turnId !== myTurnId

    try {
      // Try real backend first
      const backendResult = await sendVoiceAgentQuestion(question, source, signal)

      if (isStale()) return  // new turn started; this response is discarded

      if (backendResult) {
        setUsedFallback(false)
        answerText = backendResult.answer
        setTurns(p => [...p, { id: `a-${Date.now()}`, role: 'assistant', text: answerText, timestampMs: Date.now() }])
        if (backendResult.composer_mode) setComposerMode(backendResult.composer_mode)
        setGuardPassed(backendResult.grounded)
        setPipeDetails(backendResult.pipeDetails)
        setEvidence(backendResult.evidence ?? [])
        setRagSource(backendResult.rag?.ragSource || undefined)
        // Relabel backends: rename Claude → Claude answer, STT → runtime-aware label
        const claudeStatus = backendResult.composer_mode === 'claude' ? 'connected' : 'demo'
        const sttLabel = useGeminiStt ? 'STT: Gemini Live' : 'STT: Browser'
        setBackends(backendResult.backends.map(b => {
          if (b.label === 'Claude') return { ...b, label: 'Claude answer', status: claudeStatus as LedStatus }
          if (b.label === 'STT')   return { ...b, label: sttLabel }
          return b
        }))
      } else {
        // Backend unavailable — local mock fallback
        setUsedFallback(true)
        const mockResult = runMockPipeline(question)
        answerText = mockResult.answer
        setTurns(p => [...p, { id: `a-${Date.now()}`, role: 'assistant', text: answerText, timestampMs: Date.now() }])
        setBackends(mockResult.backends.map(b => b.label === 'Voice Agent API'
          ? { ...b, detail: 'offline', status: 'offline' as LedStatus }
          : b
        ))
        setGuardPassed(mockResult.guard.passed)
        setPipeDetails(undefined)
      }
    } catch (err: unknown) {
      if (isStale()) return
      const isAbort = err instanceof Error && err.name === 'AbortError'
      const reason  = isAbort ? 'timeout' : 'fetch_error'
      ctrl.backendFailed(reason)
      setTurns(p => [...p, {
        id: `err-${Date.now()}`, role: 'assistant',
        text: "I'm having trouble reaching the server. Please try again.",
        timestampMs: Date.now(),
      }])
      ctrl.cleanup(`backend_error: ${reason}`)
      return
    }

    if (isStale()) return

    ctrl.backendSuccess()
    cvDebug('agent response received', { latencyMs: Date.now() - pipelineStart, answerLen: answerText.length })

    // ── TTS: Gemini Live → Google Cloud → browser voice ──────────────────────
    const onTtsDone = () => {
      cvDebug('speech playback ended')
      if (!isStale()) ctrl.cleanup('tts_done')
    }

    // 1. Gemini Live TTS (experimental, opt-in only)
    if (isGeminiRuntime && ENABLE_GEMINI_TTS) {
      cvDebug('attempting Gemini Live TTS')
      const geminiAudio = await synthesizeGeminiSpeech(answerText)
      if (isStale()) return
      if (geminiAudio?.audioBase64) {
        cvDebug('speech playback start', { provider: 'gemini-live' })
        setBackends(prev => prev.map(b =>
          isTtsBackendLabel(b.label)
            ? { ...b, label: 'Voice: Gemini Live', status: 'connected' as LedStatus, detail: 'Answer: Claude' }
            : b
        ))
        await ctrl.speakAudio(geminiAudio.audioBase64, geminiAudio.mimeType, onTtsDone, 'gemini-live')
        return
      }
      // Gemini TTS failed — fall through to browser fallback below
      cvDebug('Gemini Live TTS failed, fallback reason: gemini_speak_empty')
      console.warn('[ClaimVoice:TTS] Gemini Live speak failed, falling back to browser voice')
    } else if (isGeminiRuntime) {
      cvDebug('skipping Gemini Live TTS; exact-answer speech requires a dedicated TTS provider')
    }

    // 2. Dedicated TTS provider (Cartesia / Google / system)
    const ttsData = await synthesizeSpeech({ text: answerText })
    if (isStale()) return

    if (ttsData?.audioBase64) {
      const ttsLabel =
        ttsData.provider === 'cartesia' ? 'TTS: Cartesia Skylar'
          : ttsData.provider === 'google' ? 'TTS: Google'
          : ttsData.provider === 'system' ? 'TTS: macOS'
            : 'TTS: Audio'
      cvDebug('speech playback start', { provider: ttsData.provider })
      setBackends(prev => prev.map(b =>
        isTtsBackendLabel(b.label)
          ? { ...b, label: ttsLabel, status: 'connected' as LedStatus, detail: ttsData.voiceName }
          : b
      ))
      await ctrl.speakAudio(ttsData.audioBase64, ttsData.mimeType, onTtsDone, ttsData.provider)
    } else {
      // 3. Browser voice fallback
      const resolved = resolveBrowserVoice()
      cvDebug('speech playback start', { provider: 'browser', voice: resolved.label })
      setBackends(prev => prev.map(b =>
        isTtsBackendLabel(b.label)
          ? { ...b, label: 'TTS: Browser (fallback)', status: 'connected' as LedStatus, detail: resolved.label }
          : b
      ))
      ctrl.speakBrowser(answerText, resolved.voice, onTtsDone, { rate: 0.9, pitch: resolved.pitch })
    }
  }

  const isGeminiRuntime = runtimeStatus?.runtime === 'gemini-live-configured'
  const useGeminiStt = isGeminiRuntime && ENABLE_GEMINI_STT
  const isCartesiaTts = runtimeStatus?.tts_provider === 'cartesia'
  const displayVoiceLabel = isCartesiaTts
    ? `Voice: ${runtimeStatus?.tts_voice_name ?? 'Cartesia Skylar'}`
    : voiceLabel

  const handleMicClick = useCallback(() => {
    if (status === 'thinking' || status === 'finalizing_stt') return
    primeSpeechSynthesis('mic_click')

    if (status === 'speaking' || status === 'preparing_tts') {
      // Interrupt TTS and start a new turn
      if (useGeminiStt) {
        void startGeminiMic()
      } else {
        const ctrl = newController()
        const srOk = ctrl.startSTT()
        if (!srOk) {
          setStatus('error_recoverable')
          ctrl.cleanup('browser_stt_unavailable')
        }
      }
      return
    }

    if (status === 'listening') {
      // Stop whichever input path is active
      if (useGeminiStt) {
        stopGeminiMic()
        setStatus('ready')
      } else {
        controllerRef.current?.stopSTT()
      }
      return
    }

    // ready or error_recoverable → start new turn
    if (useGeminiStt) {
      void startGeminiMic()
    } else {
      const ctrl = newController()
      const srOk = ctrl.startSTT()
      if (!srOk) {
        setStatus('error_recoverable')
        ctrl.cleanup('browser_stt_unavailable')
      }
    }
  }, [primeSpeechSynthesis, status, useGeminiStt]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleReset() {
    setInterimText('')
    geminiClientRef.current?.cleanup()
    geminiClientRef.current = null
    // cleanup() calls transition('ready') → onStateChange → setStatus('ready')
    controllerRef.current?.cleanup('user_reset')
    controllerRef.current = null
    setStatus('ready')
  }

  function handleSend() {
    const text = input.trim()
    if (!text || status === 'thinking' || status === 'finalizing_stt' || status === 'preparing_tts') return
    primeSpeechSynthesis('typed_send')
    setInput('')
    // newController() calls cleanup() on any current controller (stops TTS/STT)
    newController()
    void runPipeline(text, 'typed')
  }

  const isInputBusy = status === 'thinking' || status === 'finalizing_stt' || status === 'preparing_tts'
  const latestAssistant = [...turns].reverse().find(t => t.role === 'assistant')
  const pipelineSteps   = getPipelineSteps(status, pipeDetails)

  const micLabel = status === 'listening' ? 'Stop recording' : 'Push to talk'
  const micStatusText =
    status === 'listening'         ? 'Listening — tap to stop'          :
    status === 'finalizing_stt'    ? 'Finalizing speech…'               :
    status === 'thinking'          ? 'Checking plan…'                   :
    status === 'preparing_tts'     ? 'Preparing Skylar voice…'          :
    status === 'speaking'          ? 'Speaking answer — tap to stop'    :
    status === 'error_recoverable' ? 'Error — tap to retry'             :
                                     'Tap mic to speak'

  return (
    <div className="flex gap-3 items-start">

      {/* ── main column ──────────────────────────────────────────────────── */}
      <div className="flex-1 min-w-0 flex flex-col gap-3">

        {/* 1. Header */}
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white leading-tight">Voice Assistant</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              AI telephone agent · Silver PPO 4500 · Maya Thompson
              {usedFallback && (
                <span className="ml-2 text-amber-500 font-medium">· demo fallback</span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleReset}
              title="Reset session"
              className="p-1.5 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label="Reset voice session"
            >
              <RotateCcw size={13} />
            </button>
            <StatusPill status={status} />
          </div>
        </div>

        {/* 2. Latest answer */}
        <div className={`rounded-lg border overflow-hidden ${
          latestAssistant
            ? guardPassed === false
              ? 'bg-white dark:bg-slate-900 border-red-200 dark:border-red-800/40'
              : 'bg-white dark:bg-slate-900 border-green-200 dark:border-green-800/40'
            : 'bg-slate-50 dark:bg-slate-900/40 border-slate-200 dark:border-slate-700'
        }`}>
          <div className="px-3 py-2 flex items-start gap-2">
            <ShieldCheck size={12} className={`mt-0.5 shrink-0 ${
              latestAssistant
                ? guardPassed === false ? 'text-red-500' : 'text-green-500'
                : 'text-slate-400'
            }`} />
            <div className="min-w-0">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 mr-2">
                {latestAssistant
                  ? guardPassed === false ? 'Guard flagged' : 'Guard passed'
                  : 'Latest answer'}
              </span>
              <span className={`text-xs leading-snug ${
                latestAssistant
                  ? 'text-slate-800 dark:text-slate-200'
                  : 'text-slate-400 dark:text-slate-500 italic'
              }`}>
                {latestAssistant?.text ?? 'No answer yet — ask a question to get started.'}
              </span>
            </div>
          </div>
        </div>

        {/* 2b. Evidence citations (Component 70) */}
        {evidence.length > 0 && (
          <EvidencePanel evidence={evidence} ragSource={ragSource} />
        )}

        {/* 3. Pipeline */}
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 overflow-x-auto">
          <div className="px-3 py-2 grid grid-cols-5 min-w-[400px]">
            {pipelineSteps.map(step => (
              <PipelineStep key={step.title} step={step} />
            ))}
          </div>
        </div>

        {/* 4. Agent Talk + Transcript */}
        <div className="grid grid-cols-2 gap-3 h-[calc(100vh-260px)] min-h-[480px]">

          {/* Agent Talk */}
          <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 flex flex-col min-h-0">
            <div className="px-3 py-2 border-b border-slate-100 dark:border-slate-800 shrink-0 flex items-center justify-between">
              <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Agent Talk</span>
              <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${
                composerMode === 'claude'
                  ? 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300'
                  : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
              }`}>
                {composerMode === 'claude' ? 'Claude answer' : 'Mock answer'}
              </span>
            </div>

            {/* Mic + waveform row */}
            <div className="px-4 py-4 flex items-center gap-4 shrink-0 border-b border-slate-100 dark:border-slate-800">
              <button
                onClick={handleMicClick}
                disabled={status === 'thinking' || status === 'finalizing_stt'}
                aria-label={micLabel}
                className={`shrink-0 w-14 h-14 rounded-full flex items-center justify-center transition-all shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${
                  status === 'listening' || status === 'finalizing_stt'
                    ? 'bg-red-500 hover:bg-red-600 scale-105 shadow-red-200 dark:shadow-red-900/50'
                    : status === 'thinking'
                    ? 'bg-slate-200 dark:bg-slate-700 cursor-not-allowed opacity-60'
                    : status === 'preparing_tts'
                    ? 'bg-violet-500 hover:bg-violet-600 active:scale-95 shadow-violet-200 dark:shadow-violet-900/50'
                    : status === 'speaking'
                    ? 'bg-amber-500 hover:bg-amber-600 active:scale-95 shadow-amber-200 dark:shadow-amber-900/50'
                    : status === 'error_recoverable'
                    ? 'bg-red-400 hover:bg-red-500 active:scale-95'
                    : 'bg-blue-500 hover:bg-blue-600 active:scale-95 shadow-blue-200 dark:shadow-blue-900/50'
                }`}
              >
                {status === 'listening' || status === 'finalizing_stt'
                  ? <MicOff size={22} className="text-white" />
                  : <Mic    size={22} className="text-white" />}
              </button>
              <div className="flex flex-col gap-1.5 min-w-0 flex-1">
                <Waveform active={status === 'listening' || status === 'speaking'} />
                <span className="text-[11px] text-slate-400 dark:text-slate-500 truncate">
                  {micStatusText}
                </span>
              </div>
            </div>

            {/* Voice selector + preview */}
            <div className="px-4 py-2 shrink-0 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2">
              <span className={`text-[10px] truncate flex-1 ${
                isCartesiaTts || selectedVoice ? 'text-slate-500 dark:text-slate-400' : 'text-amber-500 dark:text-amber-400'
              }`}>
                {displayVoiceLabel}
              </span>
              <button
                onClick={() => { void handlePreviewVoice() }}
                disabled={isPreviewing || status === 'preparing_tts' || status === 'speaking'}
                title="Preview voice"
                aria-label="Preview voice"
                className="shrink-0 flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:text-blue-600 hover:border-blue-300 dark:hover:text-blue-400 dark:hover:border-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {isPreviewing
                  ? <Loader2 size={10} className="animate-spin" />
                  : <Volume2 size={10} />}
                Preview
              </button>
            </div>

            {/* Live speech preview */}
            <div className={`px-4 py-2 min-h-[52px] shrink-0 border-b border-slate-100 dark:border-slate-800 transition-all ${
              status === 'listening' ? 'bg-blue-50 dark:bg-blue-900/10' : ''
            }`}>
              {status === 'listening' || status === 'finalizing_stt' ? (
                interimText ? (
                  <p className="text-xs text-blue-700 dark:text-blue-300 leading-snug italic">
                    &ldquo;{interimText}&rdquo;
                  </p>
                ) : (
                  <p className="text-xs text-slate-400 dark:text-slate-500 italic">Listening…</p>
                )
              ) : (
                <p className="text-xs text-slate-300 dark:text-slate-600 italic select-none">
                  Speech preview
                </p>
              )}
            </div>

            {/* Examples collapsible drawer */}
            <div className="pt-2 flex-1 overflow-y-auto min-h-0">
              <ExamplesDrawer
                onPick={q => {
                  if (status === 'ready' || status === 'error_recoverable') {
                    primeSpeechSynthesis('demo_question')
                    const ctrl = newController()
                    controllerRef.current = ctrl
                    void runPipeline(q, 'demo')
                  }
                }}
                disabled={isInputBusy}
              />
            </div>

            {/* Typed input */}
            <div className="px-3 pb-3 pt-2 border-t border-slate-100 dark:border-slate-800 flex gap-2 shrink-0">
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
                placeholder="Or type a question…"
                disabled={isInputBusy}
                className="flex-1 px-3 py-1.5 text-xs rounded-md border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isInputBusy}
                className="px-2.5 py-1.5 rounded-md bg-blue-500 hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed text-white transition-colors"
                aria-label="Send"
              >
                <Send size={13} />
              </button>
            </div>
          </div>

          {/* Transcript */}
          <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 flex flex-col min-h-0">
            <div className="px-3 py-2 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between shrink-0">
              <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Transcript</span>
              <span className="text-[10px] text-slate-400 dark:text-slate-500">
                {turns.length} msgs · {usedFallback ? 'demo fallback' : 'live'}
              </span>
            </div>
            <div
              ref={transcriptRef}
              className="flex-1 p-3 space-y-2.5 overflow-y-auto min-h-0"
            >
              {turns.length === 0 && status === 'ready' && (
                <div className="flex flex-col items-center justify-center h-full gap-2 text-center px-4">
                  <p className="text-xs text-slate-400 dark:text-slate-500">No conversation yet</p>
                  <p className="text-[10px] text-slate-300 dark:text-slate-600">Ask a question using the mic or type below</p>
                </div>
              )}
              {turns.map(turn => <Bubble key={turn.id} turn={turn} />)}
              {/* Live interim bubble */}
              {(status === 'listening' || status === 'finalizing_stt') && interimText && (
                <div className="flex items-end gap-1.5 flex-row-reverse opacity-60">
                  <div className="shrink-0 w-6 h-6 rounded-full flex items-center justify-center bg-blue-100 dark:bg-blue-900/40">
                    <User size={11} className="text-blue-600 dark:text-blue-400" />
                  </div>
                  <div className="max-w-[82%] px-3 py-2 rounded-2xl text-xs leading-relaxed bg-blue-400 text-white rounded-br-sm italic">
                    {interimText}…
                  </div>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>

      {/* 5. Backend connections rail */}
      <div className="hidden lg:flex flex-col w-32 shrink-0 gap-1 pt-[38px]">
        <p className="text-[9px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider px-1">Connections</p>
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 px-2.5 py-1.5">
          {backends.map(b => (
            <LedRow key={b.label} label={b.label} ledStatus={b.status} />
          ))}
        </div>
        {runtimeStatus && ENABLE_GEMINI_TTS && (
          <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 px-2.5 py-1.5 mt-1">
            <p className="text-[9px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Voice runtime</p>
            <RuntimeRow status={runtimeStatus} />
          </div>
        )}
        {runtimeStatus && (
          <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 px-2.5 py-1.5 mt-1">
            <p className="text-[9px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Plan RAG</p>
            <RagStatusRow status={runtimeStatus} />
          </div>
        )}
      </div>

    </div>
  )
}
