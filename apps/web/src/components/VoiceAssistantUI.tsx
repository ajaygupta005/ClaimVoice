'use client'

import { useEffect, useRef, useState } from 'react'
import {
  Mic, MicOff, Send, CheckCircle2, Loader2,
  Clock, ShieldCheck, Bot, User,
} from 'lucide-react'
import {
  mockVoiceTranscript, mockToolStages,
  type VoiceTurn, type ToolCall, type VoiceStatus,
} from '@/lib/mock-data'

// ── Waveform animation (pure CSS bars) ───────────────────────────────────────

function Waveform({ active }: { active: boolean }) {
  return (
    <div className="flex items-center gap-[3px] h-5">
      {[0.6, 1, 0.75, 1, 0.5, 0.85, 0.65].map((h, i) => (
        <div
          key={i}
          className={`w-[3px] rounded-full transition-all duration-300 ${active ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'}`}
          style={{
            height: active ? `${h * 20}px` : '4px',
            animationDelay: `${i * 80}ms`,
            animation: active ? `wave 0.8s ease-in-out ${i * 80}ms infinite alternate` : 'none',
          }}
        />
      ))}
      <style>{`@keyframes wave { from { transform: scaleY(0.4); } to { transform: scaleY(1); } }`}</style>
    </div>
  )
}

// ── Status pill ───────────────────────────────────────────────────────────────

function StatusPill({ status }: { status: VoiceStatus }) {
  const map: Record<VoiceStatus, { label: string; cls: string }> = {
    idle:       { label: 'Ready',       cls: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400' },
    listening:  { label: 'Listening…',  cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' },
    processing: { label: 'Processing…', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' },
    speaking:   { label: 'Speaking…',   cls: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' },
  }
  const { label, cls } = map[status]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${cls}`}>
      {status === 'processing' && <Loader2 size={10} className="animate-spin" />}
      {label}
    </span>
  )
}

// ── Tool stage row ────────────────────────────────────────────────────────────

function ToolStageRow({ tc }: { tc: ToolCall }) {
  const icon =
    tc.status === 'completed' ? <CheckCircle2 size={13} className="text-green-500 shrink-0" /> :
    tc.status === 'running'   ? <Loader2      size={13} className="text-blue-500 animate-spin shrink-0" /> :
                                <Clock        size={13} className="text-slate-400 shrink-0" />
  return (
    <div className="flex items-start gap-2.5 py-2.5 border-b border-slate-100 dark:border-slate-800 last:border-0">
      {icon}
      <div className="min-w-0">
        <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">{tc.label}</p>
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5 truncate">{tc.detail}</p>
      </div>
    </div>
  )
}

// ── Transcript bubble ─────────────────────────────────────────────────────────

function Bubble({ turn }: { turn: VoiceTurn }) {
  const isMember = turn.role === 'member'
  return (
    <div className={`flex items-start gap-2.5 ${isMember ? 'flex-row-reverse' : ''}`}>
      <div className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${
        isMember
          ? 'bg-blue-100 dark:bg-blue-900/40'
          : 'bg-slate-100 dark:bg-slate-800'
      }`}>
        {isMember
          ? <User size={13} className="text-blue-600 dark:text-blue-400" />
          : <Bot  size={13} className="text-slate-500 dark:text-slate-400" />}
      </div>
      <div className={`max-w-[80%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed ${
        isMember
          ? 'bg-blue-500 text-white rounded-tr-sm'
          : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 rounded-tl-sm'
      }`}>
        {turn.text}
      </div>
    </div>
  )
}

// ── Mock answer responses ─────────────────────────────────────────────────────

const MOCK_ANSWERS = [
  'Your annual physical is covered at $0 as preventive care when seen by an in-network provider.',
  'Telehealth visits are covered at $0 copay under your Silver PPO 4500 plan.',
  'Mental health therapy is covered at a $40 copay per in-network session.',
  'You will pay 20% coinsurance after your deductible for outpatient surgery.',
  'Your urgent care copay is $75 per visit in-network.',
]
let answerIdx = 0

// ── Main component ────────────────────────────────────────────────────────────

export default function VoiceAssistantUI() {
  const [status, setStatus]       = useState<VoiceStatus>('idle')
  const [turns, setTurns]         = useState<VoiceTurn[]>(mockVoiceTranscript)
  const [input, setInput]         = useState('')
  const transcriptRef             = useRef<HTMLDivElement>(null)

  // Auto-scroll transcript to bottom when new turns arrive
  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
    }
  }, [turns])

  function handlePushToTalk() {
    if (status !== 'idle') { setStatus('idle'); return }
    setStatus('listening')
    setTimeout(() => {
      setStatus('processing')
      const memberTurn: VoiceTurn = {
        id: `m-${Date.now()}`, role: 'member',
        text: '(voice input — simulated)', timestampMs: Date.now(),
      }
      setTurns(prev => [...prev, memberTurn])
      setTimeout(() => {
        setStatus('speaking')
        const assistantTurn: VoiceTurn = {
          id: `a-${Date.now()}`, role: 'assistant',
          text: MOCK_ANSWERS[answerIdx++ % MOCK_ANSWERS.length],
          timestampMs: Date.now(),
        }
        setTurns(prev => [...prev, assistantTurn])
        setTimeout(() => setStatus('idle'), 2000)
      }, 1500)
    }, 2000)
  }

  function handleSend() {
    const text = input.trim()
    if (!text) return
    setInput('')
    setStatus('processing')
    const memberTurn: VoiceTurn = {
      id: `m-${Date.now()}`, role: 'member', text, timestampMs: Date.now(),
    }
    setTurns(prev => [...prev, memberTurn])
    setTimeout(() => {
      setStatus('speaking')
      const assistantTurn: VoiceTurn = {
        id: `a-${Date.now()}`, role: 'assistant',
        text: MOCK_ANSWERS[answerIdx++ % MOCK_ANSWERS.length],
        timestampMs: Date.now(),
      }
      setTurns(prev => [...prev, assistantTurn])
      setTimeout(() => setStatus('idle'), 2000)
    }, 1200)
  }

  const latestAssistant = [...turns].reverse().find(t => t.role === 'assistant')

  return (
    <div className="space-y-5">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Voice Assistant</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Ask coverage questions by voice or text · mock demo
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusPill status={status} />
        </div>
      </div>

      {/* Status indicators row */}
      <div className="flex gap-2 flex-wrap">
        {[
          { label: 'STT',     value: 'Deepgram Nova-2', active: status === 'listening'  },
          { label: 'Agent',   value: 'LangGraph + Claude', active: status === 'processing' },
          { label: 'TTS',     value: 'Cartesia Sonic',  active: status === 'speaking'   },
        ].map(({ label, value, active }) => (
          <div key={label} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs transition-colors ${
            active
              ? 'border-blue-300 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-700'
              : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-blue-500 animate-pulse' : 'bg-slate-300 dark:bg-slate-600'}`} />
            <span className="font-medium text-slate-600 dark:text-slate-400">{label}</span>
            <span className="text-slate-400 dark:text-slate-500">{value}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Left: push-to-talk + transcript */}
        <div className="lg:col-span-2 space-y-4">

          {/* Latest answer */}
          {latestAssistant && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-green-200 dark:border-green-800/60 overflow-hidden">
              <div className="px-4 py-3 border-b border-green-100 dark:border-green-800/40 flex items-center gap-2">
                <ShieldCheck size={14} className="text-green-500" />
                <span className="text-xs font-semibold text-green-700 dark:text-green-400">Latest answer · hallucination guard passed</span>
              </div>
              <p className="px-4 py-3 text-sm text-slate-800 dark:text-slate-200 leading-relaxed">
                {latestAssistant.text}
              </p>
            </div>
          )}

          {/* Push-to-talk */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-5 flex flex-col items-center gap-4">
            <button
              onClick={handlePushToTalk}
              disabled={status === 'processing' || status === 'speaking'}
              className={`w-16 h-16 rounded-full flex items-center justify-center transition-all shadow-md ${
                status === 'listening'
                  ? 'bg-red-500 hover:bg-red-600 scale-110 shadow-red-200 dark:shadow-red-900/50'
                  : status === 'processing' || status === 'speaking'
                  ? 'bg-slate-300 dark:bg-slate-700 cursor-not-allowed'
                  : 'bg-blue-500 hover:bg-blue-600 hover:scale-105 shadow-blue-200 dark:shadow-blue-900/50'
              }`}
            >
              {status === 'listening'
                ? <MicOff size={24} className="text-white" />
                : <Mic    size={24} className="text-white" />}
            </button>
            <div className="flex items-center gap-3">
              <Waveform active={status === 'listening'} />
              <span className="text-xs text-slate-400 dark:text-slate-500">
                {status === 'listening' ? 'Tap to stop' : 'Push to talk'}
              </span>
            </div>
          </div>

          {/* Typed fallback */}
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
            >
              <Send size={15} />
            </button>
          </div>

          {/* Transcript */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Transcript</h2>
              <span className="text-xs text-slate-400 dark:text-slate-500">{turns.length} messages · simulated</span>
            </div>
            <div
              ref={transcriptRef}
              className="p-4 space-y-3 max-h-72 overflow-y-auto"
            >
              {turns.map(turn => <Bubble key={turn.id} turn={turn} />)}
            </div>
          </div>
        </div>

        {/* Right: tool/safety stages */}
        <div className="space-y-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-100 dark:border-slate-800">
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Agent pipeline</h2>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Tool calls · last turn</p>
            </div>
            <div className="px-5 divide-y divide-slate-100 dark:divide-slate-800">
              {mockToolStages.map(tc => <ToolStageRow key={tc.stage} tc={tc} />)}
            </div>
          </div>

          {/* Connection info */}
          <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700 p-4 space-y-2">
            <p className="text-xs font-semibold text-slate-600 dark:text-slate-400">Backend connections</p>
            {[
              { label: 'Voice Agent API',  value: 'ws://localhost:8004', status: 'demo' },
              { label: 'Deepgram STT',     value: 'Nova-2 (streaming)',  status: 'demo' },
              { label: 'Cartesia TTS',     value: 'Sonic',               status: 'demo' },
              { label: 'Hallucination guard', value: 'guards/hallucination.py', status: 'demo' },
            ].map(({ label, value, status: s }) => (
              <div key={label} className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-slate-700 dark:text-slate-300 truncate">{label}</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 truncate">{value}</p>
                </div>
                <span className="shrink-0 px-1.5 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                  {s}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
