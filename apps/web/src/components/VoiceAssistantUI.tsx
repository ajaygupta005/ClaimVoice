'use client'

import { useEffect, useRef, useState } from 'react'
import {
  Mic, MicOff, Send, CheckCircle2, Loader2, Circle,
  ShieldCheck, Bot, User, Wifi, WifiOff,
  UserCheck, MessageSquare, Search, ShieldAlert, MessageCircle,
} from 'lucide-react'
import {
  mockVoiceTranscript,
  type VoiceTurn, type VoiceStatus,
} from '@/lib/mock-data'

// ── Waveform animation ────────────────────────────────────────────────────────

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
        @keyframes wave {
          from { transform: scaleY(0.3); }
          to   { transform: scaleY(1);   }
        }
      `}</style>
    </div>
  )
}

// ── Status pill ───────────────────────────────────────────────────────────────

function StatusPill({ status }: { status: VoiceStatus }) {
  const map: Record<VoiceStatus, { label: string; cls: string; dot: string }> = {
    idle:       { label: 'Ready',       cls: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',        dot: 'bg-slate-400' },
    listening:  { label: 'Listening',   cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',          dot: 'bg-blue-500 animate-pulse' },
    processing: { label: 'Processing',  cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',      dot: 'bg-amber-500 animate-pulse' },
    speaking:   { label: 'Speaking',    cls: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',      dot: 'bg-green-500 animate-pulse' },
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
        isMember
          ? 'bg-blue-100 dark:bg-blue-900/40'
          : 'bg-slate-100 dark:bg-slate-800'
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

// ── Agent pipeline step ───────────────────────────────────────────────────────

type PipelineState = 'completed' | 'running' | 'pending'

interface PipelineStep {
  icon: React.ReactNode
  title: string
  detail: string
  state: PipelineState
}

function PipelineStepRow({
  step,
  isLast,
}: {
  step: PipelineStep
  isLast: boolean
}) {
  return (
    <div className="flex gap-3">
      {/* connector column */}
      <div className="flex flex-col items-center">
        <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
          step.state === 'completed'
            ? 'bg-green-100 dark:bg-green-900/30'
            : step.state === 'running'
            ? 'bg-blue-100 dark:bg-blue-900/30'
            : 'bg-slate-100 dark:bg-slate-800'
        }`}>
          {step.state === 'completed' && <CheckCircle2 size={14} className="text-green-500" />}
          {step.state === 'running'   && <Loader2      size={14} className="text-blue-500 animate-spin" />}
          {step.state === 'pending'   && <Circle       size={14} className="text-slate-300 dark:text-slate-600" />}
        </div>
        {!isLast && (
          <div className={`w-px flex-1 mt-1 mb-1 ${
            step.state === 'completed'
              ? 'bg-green-200 dark:bg-green-800/40'
              : 'bg-slate-200 dark:bg-slate-700'
          }`} style={{ minHeight: '16px' }} />
        )}
      </div>

      {/* content */}
      <div className={`pb-4 min-w-0 flex-1 ${isLast ? 'pb-0' : ''}`}>
        <div className="flex items-center gap-1.5 mb-0.5">
          <span className={`${
            step.state === 'completed'
              ? 'text-slate-700 dark:text-slate-200'
              : step.state === 'running'
              ? 'text-blue-700 dark:text-blue-300'
              : 'text-slate-400 dark:text-slate-500'
          } text-xs font-semibold`}>{step.title}</span>
        </div>
        <p className="text-xs text-slate-400 dark:text-slate-500 leading-relaxed">{step.detail}</p>
      </div>
    </div>
  )
}

// ── LED connection row ────────────────────────────────────────────────────────

type LedStatus = 'connected' | 'demo' | 'degraded' | 'offline'

function LedRow({
  label,
  detail,
  ledStatus,
}: {
  label: string
  detail: string
  ledStatus: LedStatus
}) {
  const dotCls: Record<LedStatus, string> = {
    connected: 'bg-green-500',
    demo:      'bg-slate-400 dark:bg-slate-500',
    degraded:  'bg-amber-400 animate-pulse',
    offline:   'bg-red-500',
  }
  const tagCls: Record<LedStatus, string> = {
    connected: 'text-green-600 dark:text-green-400',
    demo:      'text-slate-500 dark:text-slate-400',
    degraded:  'text-amber-600 dark:text-amber-400',
    offline:   'text-red-600 dark:text-red-400',
  }
  const tagLabel: Record<LedStatus, string> = {
    connected: 'connected',
    demo:      'mock',
    degraded:  'degraded',
    offline:   'offline',
  }
  return (
    <div className="flex items-center gap-2.5 py-1.5">
      <span className={`shrink-0 w-2 h-2 rounded-full ${dotCls[ledStatus]}`} />
      <div className="min-w-0 flex-1">
        <span className="text-xs font-medium text-slate-700 dark:text-slate-300">{label}</span>
        <span className="text-xs text-slate-400 dark:text-slate-500 ml-1.5">{detail}</span>
      </div>
      <span className={`shrink-0 text-[10px] font-semibold uppercase tracking-wide ${tagCls[ledStatus]}`}>
        {tagLabel[ledStatus]}
      </span>
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

function nextAnswer() {
  return MOCK_ANSWERS[answerIdx++ % MOCK_ANSWERS.length]
}

// ── Derive pipeline steps from status ────────────────────────────────────────

function getPipelineSteps(status: VoiceStatus): PipelineStep[] {
  const done  = (title: string, detail: string, icon: React.ReactNode): PipelineStep =>
    ({ icon, title, detail, state: 'completed' })
  const run   = (title: string, detail: string, icon: React.ReactNode): PipelineStep =>
    ({ icon, title, detail, state: 'running' })
  const pend  = (title: string, detail: string, icon: React.ReactNode): PipelineStep =>
    ({ icon, title, detail, state: 'pending' })

  if (status === 'idle') return [
    done('Identify member',         'Member ID verified',                           <UserCheck    size={12} />),
    done('Understand question',     'Intent extracted',                              <MessageSquare size={12} />),
    done('Check coverage',          'Eligibility service queried',                  <Search       size={12} />),
    done('Hallucination guard',     'All claims grounded',                          <ShieldAlert  size={12} />),
    done('Prepare response',        'Answer delivered',                             <MessageCircle size={12} />),
  ]
  if (status === 'listening') return [
    run( 'Identify member',         'Listening for speech…',                        <UserCheck    size={12} />),
    pend('Understand question',     'Waiting for input',                             <MessageSquare size={12} />),
    pend('Check coverage',          'Waiting',                                      <Search       size={12} />),
    pend('Hallucination guard',     'Waiting',                                      <ShieldAlert  size={12} />),
    pend('Prepare response',        'Waiting',                                      <MessageCircle size={12} />),
  ]
  if (status === 'processing') return [
    done('Identify member',         'Member ID verified',                           <UserCheck    size={12} />),
    run( 'Understand question',     'Extracting intent…',                            <MessageSquare size={12} />),
    run( 'Check coverage',          'Querying eligibility…',                        <Search       size={12} />),
    pend('Hallucination guard',     'Waiting',                                      <ShieldAlert  size={12} />),
    pend('Prepare response',        'Waiting',                                      <MessageCircle size={12} />),
  ]
  // speaking
  return [
    done('Identify member',         'Member ID verified',                           <UserCheck    size={12} />),
    done('Understand question',     'Intent extracted',                              <MessageSquare size={12} />),
    done('Check coverage',          'Eligibility service queried',                  <Search       size={12} />),
    done('Hallucination guard',     'All claims grounded ✓',                        <ShieldAlert  size={12} />),
    run( 'Prepare response',        'Streaming answer to caller…',                  <MessageCircle size={12} />),
  ]
}

// ── Main component ────────────────────────────────────────────────────────────

export default function VoiceAssistantUI() {
  const [status, setStatus]   = useState<VoiceStatus>('idle')
  const [turns, setTurns]     = useState<VoiceTurn[]>(mockVoiceTranscript)
  const [input, setInput]     = useState('')
  const transcriptRef         = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
    }
  }, [turns])

  function handlePushToTalk() {
    if (status === 'processing' || status === 'speaking') return
    if (status === 'listening') { setStatus('idle'); return }

    setStatus('listening')
    setTimeout(() => {
      setStatus('processing')
      setTurns(prev => [...prev, {
        id: `m-${Date.now()}`, role: 'member',
        text: '(voice input — simulated)', timestampMs: Date.now(),
      }])
      setTimeout(() => {
        setStatus('speaking')
        setTurns(prev => [...prev, {
          id: `a-${Date.now()}`, role: 'assistant',
          text: nextAnswer(), timestampMs: Date.now(),
        }])
        setTimeout(() => setStatus('idle'), 2200)
      }, 1600)
    }, 2000)
  }

  function handleSend() {
    const text = input.trim()
    if (!text || status !== 'idle') return
    setInput('')
    setStatus('processing')
    setTurns(prev => [...prev, {
      id: `m-${Date.now()}`, role: 'member', text, timestampMs: Date.now(),
    }])
    setTimeout(() => {
      setStatus('speaking')
      setTurns(prev => [...prev, {
        id: `a-${Date.now()}`, role: 'assistant',
        text: nextAnswer(), timestampMs: Date.now(),
      }])
      setTimeout(() => setStatus('idle'), 2200)
    }, 1300)
  }

  const latestAssistant = [...turns].reverse().find(t => t.role === 'assistant')
  const pipelineSteps   = getPipelineSteps(status)

  return (
    <div className="flex flex-col gap-5 h-full">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Voice Assistant</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            AI telephone agent · ask coverage questions by voice or text
          </p>
        </div>
        <StatusPill status={status} />
      </div>

      {/* ── Body: two-column ────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-5 items-start">

        {/* ── LEFT: main interaction area ─────────────────────────────── */}
        <div className="flex flex-col gap-4 min-w-0">

          {/* Latest answer */}
          <div className={`rounded-xl border overflow-hidden transition-colors ${
            latestAssistant
              ? 'bg-white dark:bg-slate-900 border-green-200 dark:border-green-800/50'
              : 'bg-slate-50 dark:bg-slate-900/50 border-slate-200 dark:border-slate-700'
          }`}>
            <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2">
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
              {latestAssistant
                ? latestAssistant.text
                : 'No answer yet — ask a question to get started.'}
            </p>
          </div>

          {/* Agent talk panel */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700">
            <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800">
              <h2 className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">
                Agent Talk
              </h2>
            </div>
            <div className="p-5 flex flex-col items-center gap-4">
              {/* big PTT button */}
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

              {/* waveform + label */}
              <div className="flex flex-col items-center gap-2">
                <Waveform active={status === 'listening'} />
                <span className="text-xs font-medium text-slate-400 dark:text-slate-500">
                  {status === 'listening'  ? 'Recording — tap to stop'   :
                   status === 'processing' ? 'Processing your question…' :
                   status === 'speaking'   ? 'Agent is speaking…'        :
                                             'Push to talk'}
                </span>
              </div>
            </div>
          </div>

          {/* Typed input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              placeholder="Or type your question here…"
              disabled={status !== 'idle'}
              className="flex-1 px-4 py-2.5 text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || status !== 'idle'}
              className="px-4 py-2.5 rounded-lg bg-blue-500 hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed text-white transition-colors"
              aria-label="Send"
            >
              <Send size={15} />
            </button>
          </div>

          {/* Transcript */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <h2 className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">
                Transcript
              </h2>
              <span className="text-xs text-slate-400 dark:text-slate-500">
                {turns.length} message{turns.length !== 1 ? 's' : ''} · simulated
              </span>
            </div>
            <div
              ref={transcriptRef}
              className="p-4 space-y-3 max-h-72 overflow-y-auto"
            >
              {turns.map(turn => <Bubble key={turn.id} turn={turn} />)}
            </div>
          </div>
        </div>

        {/* ── RIGHT: pipeline + backend status ────────────────────────── */}
        <div className="flex flex-col gap-4">

          {/* Linear agent pipeline */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800">
              <h2 className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">
                Agent Pipeline
              </h2>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Current turn · step-by-step</p>
            </div>
            <div className="px-4 py-4">
              {pipelineSteps.map((step, i) => (
                <PipelineStepRow
                  key={step.title}
                  step={step}
                  isLast={i === pipelineSteps.length - 1}
                />
              ))}
            </div>
          </div>

          {/* Backend connections */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800">
              <h2 className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">
                Backend Connections
              </h2>
            </div>
            <div className="px-4 py-2 divide-y divide-slate-100 dark:divide-slate-800">
              <LedRow label="Voice Agent API"     detail="localhost:8004"           ledStatus="demo" />
              <LedRow label="STT"                 detail="Deepgram Nova-2"          ledStatus="demo" />
              <LedRow label="TTS"                 detail="Cartesia Sonic"           ledStatus="demo" />
              <LedRow label="Hallucination guard" detail="guards/hallucination.py"  ledStatus="demo" />
              <LedRow label="Telephony bridge"    detail="Twilio Media Streams"     ledStatus="demo" />
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
