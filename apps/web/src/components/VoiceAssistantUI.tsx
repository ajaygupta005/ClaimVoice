'use client'

import { useEffect, useRef, useState } from 'react'
import {
  Mic, MicOff, Send, CheckCircle2, Loader2, Circle, ShieldCheck, Bot, User,
} from 'lucide-react'
import { mockVoiceTranscript, type VoiceTurn, type VoiceStatus } from '@/lib/mock-data'
import { runMockPipeline, type BackendStatus, type LedStatus } from '@/lib/mock-pipeline'

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
    idle:       { label: 'Ready',      cls: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',    dot: 'bg-slate-400' },
    listening:  { label: 'Listening',  cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',     dot: 'bg-blue-500 animate-pulse' },
    processing: { label: 'Processing', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300', dot: 'bg-amber-500 animate-pulse' },
    speaking:   { label: 'Speaking',   cls: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300', dot: 'bg-green-500 animate-pulse' },
  }
  const { label, cls, dot } = map[status]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {status === 'processing' && <Loader2 size={10} className="animate-spin -ml-0.5" />}
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

// ── Horizontal pipeline (grid-cols-5) ─────────────────────────────────────────

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

function getPipelineSteps(status: VoiceStatus): PipeStep[] {
  if (status === 'idle') return [
    { title: 'Identify', detail: 'Member verified',    state: 'completed' },
    { title: 'Understand', detail: 'Intent extracted', state: 'completed' },
    { title: 'Check',    detail: 'Eligibility queried',state: 'completed' },
    { title: 'Guard',    detail: 'Claims grounded',    state: 'completed' },
    { title: 'Respond',  detail: 'Answer delivered',   state: 'completed' },
  ]
  if (status === 'listening') return [
    { title: 'Identify', detail: 'Listening…',         state: 'running'   },
    { title: 'Understand', detail: 'Waiting',           state: 'pending'   },
    { title: 'Check',    detail: 'Waiting',             state: 'pending'   },
    { title: 'Guard',    detail: 'Waiting',             state: 'pending'   },
    { title: 'Respond',  detail: 'Waiting',             state: 'pending'   },
  ]
  if (status === 'processing') return [
    { title: 'Identify', detail: 'Member verified',    state: 'completed' },
    { title: 'Understand', detail: 'Extracting…',      state: 'running'   },
    { title: 'Check',    detail: 'Querying…',           state: 'running'   },
    { title: 'Guard',    detail: 'Waiting',             state: 'pending'   },
    { title: 'Respond',  detail: 'Waiting',             state: 'pending'   },
  ]
  return [
    { title: 'Identify', detail: 'Member verified',    state: 'completed' },
    { title: 'Understand', detail: 'Intent extracted', state: 'completed' },
    { title: 'Check',    detail: 'Eligibility queried',state: 'completed' },
    { title: 'Guard',    detail: 'All grounded ✓',     state: 'completed' },
    { title: 'Respond',  detail: 'Streaming…',         state: 'running'   },
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

// ── Constants ─────────────────────────────────────────────────────────────────

const VOICE_QUESTIONS = [
  'Is an MRI of the brain covered?',
  'What is my urgent care copay?',
  'Is lisinopril on my formulary?',
  'Find a cardiologist near me who is in network',
  'Do I need prior authorization for an MRI?',
  'My claim was denied — can you help?',
]
let voiceQIdx = 0
function nextVoiceQuestion() { return VOICE_QUESTIONS[voiceQIdx++ % VOICE_QUESTIONS.length] }

const DEFAULT_BACKENDS: BackendStatus[] = [
  { label: 'Voice Agent API',     detail: '', status: 'demo' },
  { label: 'STT',                 detail: '', status: 'demo' },
  { label: 'TTS',                 detail: '', status: 'demo' },
  { label: 'Hallucination guard', detail: '', status: 'demo' },
  { label: 'Telephony bridge',    detail: '', status: 'demo' },
]

// ── Main component ────────────────────────────────────────────────────────────

export default function VoiceAssistantUI() {
  const [status,      setStatus]      = useState<VoiceStatus>('idle')
  const [turns,       setTurns]       = useState<VoiceTurn[]>(mockVoiceTranscript)
  const [input,       setInput]       = useState('')
  const [backends,    setBackends]    = useState<BackendStatus[]>(DEFAULT_BACKENDS)
  const [guardPassed, setGuardPassed] = useState<boolean | null>(null)
  const transcriptRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (transcriptRef.current)
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
  }, [turns])

  function runPipeline(question: string) {
    setStatus('processing')
    setTurns(p => [...p, { id: `m-${Date.now()}`, role: 'member', text: question, timestampMs: Date.now() }])
    setTimeout(() => {
      const result = runMockPipeline(question)
      setStatus('speaking')
      setTurns(p => [...p, { id: `a-${Date.now()}`, role: 'assistant', text: result.answer, timestampMs: Date.now() }])
      setBackends(result.backends)
      setGuardPassed(result.guard.passed)
      setTimeout(() => setStatus('idle'), Math.min(result.tts.durationEstimateMs || 2200, 3000))
    }, 1400)
  }

  function handlePushToTalk() {
    if (status === 'processing' || status === 'speaking') return
    if (status === 'listening') { runPipeline(nextVoiceQuestion()); return }
    setStatus('listening')
  }

  function handleSend() {
    const text = input.trim()
    if (!text || status !== 'idle') return
    setInput('')
    runPipeline(text)
  }

  const latestAssistant = [...turns].reverse().find(t => t.role === 'assistant')
  const pipelineSteps   = getPipelineSteps(status)

  return (
    // outer flex: main column + slim right rail
    <div className="flex gap-3 items-start">

      {/* ── main column ──────────────────────────────────────────────────── */}
      <div className="flex-1 min-w-0 flex flex-col gap-3">

        {/* 1. Header */}
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white leading-tight">Voice Assistant</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              AI telephone agent · Silver PPO 4500 · Maya Thompson
            </p>
          </div>
          <StatusPill status={status} />
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

        {/* 3. Pipeline — directly below latest answer, above conversation panels */}
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 overflow-x-auto">
          <div className="px-3 py-2 grid grid-cols-5 min-w-[400px]">
            {pipelineSteps.map(step => (
              <PipelineStep key={step.title} step={step} />
            ))}
          </div>
        </div>

        {/* 4. Agent Talk + Transcript — equal-height side by side */}
        <div className="grid grid-cols-2 gap-3 h-[calc(100vh-260px)] min-h-[480px]">

          {/* Agent Talk */}
          <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 flex flex-col min-h-0">
            {/* header */}
            <div className="px-3 py-2 border-b border-slate-100 dark:border-slate-800 shrink-0">
              <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Agent Talk</span>
            </div>

            {/* mic + waveform */}
            <div className="px-4 py-4 flex items-center gap-4 shrink-0 border-b border-slate-100 dark:border-slate-800">
              <button
                onClick={handlePushToTalk}
                disabled={status === 'processing' || status === 'speaking'}
                aria-label={status === 'listening' ? 'Stop recording' : 'Push to talk'}
                className={`shrink-0 w-14 h-14 rounded-full flex items-center justify-center transition-all shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${
                  status === 'listening'
                    ? 'bg-red-500 hover:bg-red-600 scale-105 shadow-red-200 dark:shadow-red-900/50'
                    : status === 'processing' || status === 'speaking'
                    ? 'bg-slate-200 dark:bg-slate-700 cursor-not-allowed opacity-60'
                    : 'bg-blue-500 hover:bg-blue-600 active:scale-95 shadow-blue-200 dark:shadow-blue-900/50'
                }`}
              >
                {status === 'listening'
                  ? <MicOff size={22} className="text-white" />
                  : <Mic    size={22} className="text-white" />}
              </button>
              <div className="flex flex-col gap-1.5">
                <Waveform active={status === 'listening'} />
                <span className="text-[11px] text-slate-400 dark:text-slate-500">
                  {status === 'listening'  ? 'Recording — tap to stop'   :
                   status === 'processing' ? 'Processing your question…' :
                   status === 'speaking'   ? 'Agent is speaking…'        :
                                             'Push to talk'}
                </span>
              </div>
            </div>

            {/* demo question chips — scrollable area */}
            <div className="flex-1 px-3 py-3 overflow-y-auto min-h-0">
              <p className="text-[10px] font-medium text-slate-400 dark:text-slate-500 mb-2 uppercase tracking-wider">Demo questions</p>
              <div className="flex flex-col gap-1.5">
                {VOICE_QUESTIONS.map(q => (
                  <button
                    key={q}
                    onClick={() => { if (status === 'idle') runPipeline(q) }}
                    disabled={status !== 'idle'}
                    className="text-left text-xs px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-blue-50 hover:border-blue-200 dark:hover:bg-blue-900/20 dark:hover:border-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>

            {/* typed input — pinned to bottom */}
            <div className="px-3 pb-3 pt-2 border-t border-slate-100 dark:border-slate-800 flex gap-2 shrink-0">
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
                placeholder="Type a question…"
                disabled={status !== 'idle'}
                className="flex-1 px-3 py-1.5 text-xs rounded-md border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || status !== 'idle'}
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
              <span className="text-[10px] text-slate-400 dark:text-slate-500">{turns.length} msgs · simulated</span>
            </div>
            <div
              ref={transcriptRef}
              className="flex-1 p-3 space-y-2.5 overflow-y-auto min-h-0"
            >
              {turns.map(turn => <Bubble key={turn.id} turn={turn} />)}
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
      </div>

    </div>
  )
}
