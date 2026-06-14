'use client'

import { useEffect, useRef, useState } from 'react'
import {
  Mic, MicOff, Send, CheckCircle2, Loader2, Circle,
  ShieldCheck, Bot, User,
} from 'lucide-react'
import {
  mockVoiceTranscript,
  type VoiceTurn, type VoiceStatus,
} from '@/lib/mock-data'

// ── Waveform ──────────────────────────────────────────────────────────────────

function Waveform({ active }: { active: boolean }) {
  return (
    <div className="flex items-end gap-[3px] h-6">
      {[0.4, 0.7, 1, 0.6, 0.9, 0.5, 0.8, 0.45, 0.7, 1, 0.6].map((h, i) => (
        <div
          key={i}
          className={`w-[3px] rounded-full transition-all duration-300 ${
            active ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'
          }`}
          style={{
            height: active ? `${h * 24}px` : '4px',
            animation: active
              ? `wave 0.8s ease-in-out ${i * 70}ms infinite alternate`
              : 'none',
          }}
        />
      ))}
      <style>{`
        @keyframes wave { from { transform: scaleY(0.3); } to { transform: scaleY(1); } }
      `}</style>
    </div>
  )
}

// ── Status pill ───────────────────────────────────────────────────────────────

function StatusPill({ status }: { status: VoiceStatus }) {
  const map: Record<VoiceStatus, { label: string; cls: string; dot: string }> = {
    idle:       { label: 'Ready',      cls: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',   dot: 'bg-slate-400' },
    listening:  { label: 'Listening',  cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',    dot: 'bg-blue-500 animate-pulse' },
    processing: { label: 'Processing', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300', dot: 'bg-amber-500 animate-pulse' },
    speaking:   { label: 'Speaking',   cls: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300', dot: 'bg-green-500 animate-pulse' },
  }
  const { label, cls, dot } = map[status]
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${cls}`}>
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
    <div className={`flex items-end gap-2 ${isMember ? 'flex-row-reverse' : ''}`}>
      <div className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${
        isMember ? 'bg-blue-100 dark:bg-blue-900/40' : 'bg-slate-100 dark:bg-slate-800'
      }`}>
        {isMember
          ? <User size={13} className="text-blue-600 dark:text-blue-400" />
          : <Bot  size={13} className="text-slate-500 dark:text-slate-400" />}
      </div>
      <div className={`max-w-[78%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed ${
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

interface PipeStep {
  title: string
  detail: string
  state: StepState
}

function PipelineStep({ step, isLast }: { step: PipeStep; isLast: boolean }) {
  return (
    <div className="flex items-center flex-1 min-w-0">
      {/* step block */}
      <div className="flex flex-col items-center min-w-0 flex-1">
        {/* dot + title row */}
        <div className="flex items-center gap-1.5 mb-1">
          {step.state === 'completed' && (
            <CheckCircle2 size={13} className="text-green-500 shrink-0" />
          )}
          {step.state === 'running' && (
            <Loader2 size={13} className="text-blue-500 animate-spin shrink-0" />
          )}
          {step.state === 'pending' && (
            <Circle size={13} className="text-slate-300 dark:text-slate-600 shrink-0" />
          )}
          <span className={`text-xs font-semibold truncate ${
            step.state === 'completed' ? 'text-slate-700 dark:text-slate-200' :
            step.state === 'running'   ? 'text-blue-700 dark:text-blue-300'   :
                                         'text-slate-400 dark:text-slate-500'
          }`}>{step.title}</span>
        </div>
        <p className="text-[10px] text-slate-400 dark:text-slate-500 text-center leading-snug px-1 truncate w-full">
          {step.detail}
        </p>
      </div>
      {/* connector */}
      {!isLast && (
        <div className={`shrink-0 h-px w-6 mx-1 ${
          step.state === 'completed'
            ? 'bg-green-300 dark:bg-green-700'
            : 'bg-slate-200 dark:bg-slate-700'
        }`} />
      )}
    </div>
  )
}

function getPipelineSteps(status: VoiceStatus): PipeStep[] {
  if (status === 'idle') return [
    { title: 'Identify member',    detail: 'Member ID verified',          state: 'completed' },
    { title: 'Understand question',detail: 'Intent extracted',             state: 'completed' },
    { title: 'Check coverage',     detail: 'Eligibility queried',         state: 'completed' },
    { title: 'Hallucination guard',detail: 'All claims grounded',         state: 'completed' },
    { title: 'Prepare response',   detail: 'Answer delivered',            state: 'completed' },
  ]
  if (status === 'listening') return [
    { title: 'Identify member',    detail: 'Listening for speech…',       state: 'running'   },
    { title: 'Understand question',detail: 'Waiting for input',            state: 'pending'   },
    { title: 'Check coverage',     detail: 'Waiting',                     state: 'pending'   },
    { title: 'Hallucination guard',detail: 'Waiting',                     state: 'pending'   },
    { title: 'Prepare response',   detail: 'Waiting',                     state: 'pending'   },
  ]
  if (status === 'processing') return [
    { title: 'Identify member',    detail: 'Member ID verified',          state: 'completed' },
    { title: 'Understand question',detail: 'Extracting intent…',           state: 'running'   },
    { title: 'Check coverage',     detail: 'Querying eligibility…',       state: 'running'   },
    { title: 'Hallucination guard',detail: 'Waiting',                     state: 'pending'   },
    { title: 'Prepare response',   detail: 'Waiting',                     state: 'pending'   },
  ]
  return [
    { title: 'Identify member',    detail: 'Member ID verified',          state: 'completed' },
    { title: 'Understand question',detail: 'Intent extracted',             state: 'completed' },
    { title: 'Check coverage',     detail: 'Eligibility queried',         state: 'completed' },
    { title: 'Hallucination guard',detail: 'All claims grounded ✓',       state: 'completed' },
    { title: 'Prepare response',   detail: 'Streaming answer…',           state: 'running'   },
  ]
}

// ── Backend connections rail ──────────────────────────────────────────────────

type LedStatus = 'connected' | 'demo' | 'degraded' | 'offline'

function LedRow({ label, ledStatus }: { label: string; ledStatus: LedStatus }) {
  const dot: Record<LedStatus, string> = {
    connected: 'bg-green-500',
    demo:      'bg-slate-400 dark:bg-slate-500',
    degraded:  'bg-amber-400 animate-pulse',
    offline:   'bg-red-500',
  }
  return (
    <div className="flex items-center gap-1.5 py-1">
      <span className={`shrink-0 w-1.5 h-1.5 rounded-full ${dot[ledStatus]}`} />
      <span className="text-[11px] text-slate-500 dark:text-slate-400 truncate">{label}</span>
    </div>
  )
}

// ── Mock answers ──────────────────────────────────────────────────────────────

const MOCK_ANSWERS = [
  'Your annual physical is covered at $0 as preventive care when seen by an in-network provider.',
  'Telehealth visits are covered at $0 copay under your Silver PPO 4500 plan.',
  'Mental health therapy is covered at a $40 copay per in-network session.',
  'You will pay 20% coinsurance after your deductible for outpatient surgery.',
  'Your urgent care copay is $75 per visit in-network.',
]
let answerIdx = 0
function nextAnswer() { return MOCK_ANSWERS[answerIdx++ % MOCK_ANSWERS.length] }

// ── Main component ────────────────────────────────────────────────────────────

export default function VoiceAssistantUI() {
  const [status, setStatus] = useState<VoiceStatus>('idle')
  const [turns, setTurns]   = useState<VoiceTurn[]>(mockVoiceTranscript)
  const [input, setInput]   = useState('')
  const transcriptRef       = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (transcriptRef.current)
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
  }, [turns])

  function handlePushToTalk() {
    if (status === 'processing' || status === 'speaking') return
    if (status === 'listening') { setStatus('idle'); return }
    setStatus('listening')
    setTimeout(() => {
      setStatus('processing')
      setTurns(p => [...p, { id: `m-${Date.now()}`, role: 'member', text: '(voice input — simulated)', timestampMs: Date.now() }])
      setTimeout(() => {
        setStatus('speaking')
        setTurns(p => [...p, { id: `a-${Date.now()}`, role: 'assistant', text: nextAnswer(), timestampMs: Date.now() }])
        setTimeout(() => setStatus('idle'), 2200)
      }, 1600)
    }, 2000)
  }

  function handleSend() {
    const text = input.trim()
    if (!text || status !== 'idle') return
    setInput('')
    setStatus('processing')
    setTurns(p => [...p, { id: `m-${Date.now()}`, role: 'member', text, timestampMs: Date.now() }])
    setTimeout(() => {
      setStatus('speaking')
      setTurns(p => [...p, { id: `a-${Date.now()}`, role: 'assistant', text: nextAnswer(), timestampMs: Date.now() }])
      setTimeout(() => setStatus('idle'), 2200)
    }, 1300)
  }

  const latestAssistant = [...turns].reverse().find(t => t.role === 'assistant')
  const pipelineSteps   = getPipelineSteps(status)

  return (
    /* outer row: main content + slim right rail */
    <div className="flex gap-4 items-start">

      {/* ── main content column ─────────────────────────────────────────── */}
      <div className="flex-1 min-w-0 flex flex-col gap-4">

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Voice Assistant</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              AI telephone agent · ask coverage questions by voice or text
            </p>
          </div>
          <StatusPill status={status} />
        </div>

        {/* Latest answer */}
        <div className={`rounded-xl border overflow-hidden ${
          latestAssistant
            ? 'bg-white dark:bg-slate-900 border-green-200 dark:border-green-800/50'
            : 'bg-slate-50 dark:bg-slate-900/50 border-slate-200 dark:border-slate-700'
        }`}>
          <div className="px-4 py-2.5 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2">
            <ShieldCheck size={13} className={latestAssistant ? 'text-green-500' : 'text-slate-400'} />
            <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">
              {latestAssistant ? 'Latest answer · hallucination guard passed' : 'Latest answer'}
            </span>
          </div>
          <p className={`px-4 py-3 text-sm leading-relaxed ${
            latestAssistant
              ? 'text-slate-800 dark:text-slate-200'
              : 'text-slate-400 dark:text-slate-500 italic'
          }`}>
            {latestAssistant?.text ?? 'No answer yet — ask a question to get started.'}
          </p>
        </div>

        {/* Agent Talk + Transcript side by side */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

          {/* Agent Talk */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 flex flex-col">
            <div className="px-4 py-2.5 border-b border-slate-100 dark:border-slate-800">
              <h2 className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">
                Agent Talk
              </h2>
            </div>
            <div className="flex-1 flex flex-col items-center justify-center gap-4 p-6">
              <button
                onClick={handlePushToTalk}
                disabled={status === 'processing' || status === 'speaking'}
                aria-label={status === 'listening' ? 'Stop recording' : 'Push to talk'}
                className={`w-20 h-20 rounded-full flex items-center justify-center transition-all shadow-lg focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-400 ${
                  status === 'listening'
                    ? 'bg-red-500 hover:bg-red-600 scale-110 shadow-red-200 dark:shadow-red-900/50'
                    : status === 'processing' || status === 'speaking'
                    ? 'bg-slate-200 dark:bg-slate-700 cursor-not-allowed opacity-60'
                    : 'bg-blue-500 hover:bg-blue-600 active:scale-95 shadow-blue-200 dark:shadow-blue-900/50'
                }`}
              >
                {status === 'listening'
                  ? <MicOff size={28} className="text-white" />
                  : <Mic    size={28} className="text-white" />}
              </button>
              <div className="flex flex-col items-center gap-2">
                <Waveform active={status === 'listening'} />
                <span className="text-xs font-medium text-slate-400 dark:text-slate-500">
                  {status === 'listening'  ? 'Recording — tap to stop'    :
                   status === 'processing' ? 'Processing your question…'  :
                   status === 'speaking'   ? 'Agent is speaking…'         :
                                             'Push to talk'}
                </span>
              </div>
            </div>
            {/* typed input */}
            <div className="px-4 pb-4 flex gap-2">
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
                placeholder="Or type your question…"
                disabled={status !== 'idle'}
                className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || status !== 'idle'}
                className="px-3 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed text-white transition-colors"
                aria-label="Send"
              >
                <Send size={14} />
              </button>
            </div>
          </div>

          {/* Transcript */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 flex flex-col">
            <div className="px-4 py-2.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <h2 className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">
                Transcript
              </h2>
              <span className="text-xs text-slate-400 dark:text-slate-500">
                {turns.length} msg{turns.length !== 1 ? 's' : ''} · simulated
              </span>
            </div>
            <div
              ref={transcriptRef}
              className="flex-1 p-4 space-y-3 overflow-y-auto"
              style={{ minHeight: '240px', maxHeight: '340px' }}
            >
              {turns.map(turn => <Bubble key={turn.id} turn={turn} />)}
            </div>
          </div>
        </div>

        {/* Horizontal agent pipeline */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="px-4 py-2.5 border-b border-slate-100 dark:border-slate-800">
            <h2 className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">
              Agent Pipeline
            </h2>
          </div>
          <div className="px-4 py-4 flex items-start">
            {pipelineSteps.map((step, i) => (
              <PipelineStep
                key={step.title}
                step={step}
                isLast={i === pipelineSteps.length - 1}
              />
            ))}
          </div>
        </div>

      </div>

      {/* ── slim right rail: backend connections ────────────────────────── */}
      <div className="hidden lg:flex flex-col w-36 shrink-0 pt-[68px]">
        <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-1 px-1">
          Connections
        </p>
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-2">
          <LedRow label="Voice Agent API"     ledStatus="demo" />
          <LedRow label="STT"                 ledStatus="demo" />
          <LedRow label="TTS"                 ledStatus="demo" />
          <LedRow label="Hallucination guard" ledStatus="demo" />
          <LedRow label="Telephony bridge"    ledStatus="demo" />
        </div>
      </div>

    </div>
  )
}
