'use client'

import { useState } from 'react'
import { Phone, Clock, Calendar, ShieldCheck, Mic, Bot, User, Play, ChevronRight, AlertCircle } from 'lucide-react'
import { mockCallHistory, type CallRecord, type CallStatus, type ConsentStatus, type VoiceTurn } from '@/lib/mock-data'

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDuration(sec: number): string {
  if (sec === 0) return '—'
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

function fmtDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function fmtTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: CallStatus }) {
  const map: Record<CallStatus, { label: string; cls: string }> = {
    completed:   { label: 'Completed',    cls: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' },
    no_answer:   { label: 'No answer',    cls: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400' },
    transferred: { label: 'Transferred',  cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' },
    in_progress: { label: 'In progress',  cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' },
  }
  const { label, cls } = map[status]
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${cls}`}>{label}</span>
  )
}

// ── Consent badge ─────────────────────────────────────────────────────────────

function ConsentBadge({ status }: { status: ConsentStatus }) {
  const map: Record<ConsentStatus, { label: string; cls: string }> = {
    recorded_with_consent: { label: 'Recorded · consent',    cls: 'text-green-600 dark:text-green-400' },
    not_recorded:          { label: 'Not recorded',          cls: 'text-slate-400 dark:text-slate-500' },
    pending:               { label: 'Consent pending',       cls: 'text-amber-600 dark:text-amber-400' },
  }
  const { label, cls } = map[status]
  return (
    <span className={`flex items-center gap-1 text-xs ${cls}`}>
      <ShieldCheck size={11} /> {label}
    </span>
  )
}

// ── Transcript bubble ─────────────────────────────────────────────────────────

function Bubble({ turn }: { turn: VoiceTurn }) {
  const isMember = turn.role === 'member'
  return (
    <div className={`flex items-start gap-2 ${isMember ? 'flex-row-reverse' : ''}`}>
      <div className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${
        isMember ? 'bg-blue-100 dark:bg-blue-900/40' : 'bg-slate-100 dark:bg-slate-800'
      }`}>
        {isMember
          ? <User size={11} className="text-blue-600 dark:text-blue-400" />
          : <Bot  size={11} className="text-slate-500 dark:text-slate-400" />}
      </div>
      <div className={`max-w-[80%] px-3 py-2 rounded-xl text-xs leading-relaxed ${
        isMember
          ? 'bg-blue-500 text-white rounded-tr-sm'
          : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 rounded-tl-sm'
      }`}>
        {turn.text}
      </div>
    </div>
  )
}

// ── Call list item ────────────────────────────────────────────────────────────

function CallListItem({
  call,
  selected,
  onClick,
}: {
  call: CallRecord
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={[
        'w-full text-left px-4 py-3.5 border-b border-slate-100 dark:border-slate-800 last:border-0 transition-colors',
        selected
          ? 'bg-blue-50 dark:bg-blue-950/30'
          : 'hover:bg-slate-50 dark:hover:bg-slate-800/50',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-slate-400 dark:text-slate-500">{call.id}</span>
            <StatusBadge status={call.status} />
          </div>
          <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">
            {call.mainQuestion}
          </p>
          <div className="flex items-center gap-3 mt-1 text-xs text-slate-400 dark:text-slate-500">
            <span className="flex items-center gap-1"><Calendar size={10} /> {fmtDate(call.dateIso)}</span>
            <span className="flex items-center gap-1"><Clock size={10} /> {fmtDuration(call.durationSec)}</span>
          </div>
        </div>
        <ChevronRight size={14} className={`shrink-0 mt-1 transition-colors ${selected ? 'text-blue-500' : 'text-slate-300 dark:text-slate-600'}`} />
      </div>
    </button>
  )
}

// ── Detail panel ──────────────────────────────────────────────────────────────

function DetailPanel({ call }: { call: CallRecord }) {
  return (
    <div className="flex flex-col gap-5">

      {/* Header */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-mono text-slate-400 dark:text-slate-500">{call.id}</span>
              <StatusBadge status={call.status} />
            </div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-white mb-1">{call.mainQuestion}</h2>
            <ConsentBadge status={call.consentStatus} />
          </div>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-4 text-xs">
          {[
            { label: 'Date',     value: fmtDate(call.dateIso) },
            { label: 'Time',     value: fmtTime(call.dateIso) },
            { label: 'Duration', value: fmtDuration(call.durationSec) },
          ].map(({ label, value }) => (
            <div key={label}>
              <p className="text-slate-400 dark:text-slate-500 mb-0.5">{label}</p>
              <p className="font-medium text-slate-800 dark:text-slate-200">{value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Summary */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2">
          <Bot size={13} className="text-slate-500 dark:text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Assistant summary</h3>
        </div>
        <p className="px-5 py-4 text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
          {call.assistantSummary}
        </p>
        {call.toolOutcome && (
          <div className="px-5 pb-4">
            <span className="inline-flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/20 border border-green-100 dark:border-green-800/40 px-2.5 py-1 rounded-full">
              <ShieldCheck size={11} />
              {call.toolOutcome}
            </span>
          </div>
        )}
      </div>

      {/* Playback placeholder */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2">
          <Mic size={13} className="text-slate-500 dark:text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Recording</h3>
        </div>
        {call.consentStatus === 'recorded_with_consent' ? (
          <div className="px-5 py-4 flex items-center gap-4">
            <button className="flex items-center justify-center w-9 h-9 rounded-full bg-blue-500 hover:bg-blue-600 transition-colors shrink-0">
              <Play size={14} className="text-white ml-0.5" />
            </button>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1.5">
                <div className="flex-1 h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                  <div className="w-0 h-full bg-blue-400 rounded-full" />
                </div>
                <span className="text-xs text-slate-400 dark:text-slate-500 shrink-0">
                  {fmtDuration(call.durationSec)}
                </span>
              </div>
              <p className="text-xs text-slate-400 dark:text-slate-500">Playback available · encrypted at rest · demo placeholder</p>
            </div>
          </div>
        ) : (
          <div className="px-5 py-4 flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
            <AlertCircle size={13} />
            {call.consentStatus === 'not_recorded' ? 'No recording for this call.' : 'Recording pending consent.'}
          </div>
        )}
      </div>

      {/* Transcript */}
      {call.transcript.length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Phone size={13} className="text-slate-500 dark:text-slate-400" />
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Transcript</h3>
            </div>
            <span className="text-xs text-slate-400 dark:text-slate-500">{call.transcript.length} messages</span>
          </div>
          <div className="p-4 space-y-2.5 max-h-64 overflow-y-auto">
            {call.transcript.map(turn => <Bubble key={turn.id} turn={turn} />)}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function CallHistoryView() {
  const [selectedId, setSelectedId] = useState<string>(mockCallHistory[0]?.id ?? '')
  const selected = mockCallHistory.find(c => c.id === selectedId) ?? null

  return (
    <div className="space-y-5">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Call History</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
          Past voice sessions for {mockCallHistory[0]?.memberName} · {mockCallHistory.length} calls
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5 items-start">

        {/* Call list */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100 dark:border-slate-800">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">All calls</h2>
          </div>
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {mockCallHistory.map(call => (
              <CallListItem
                key={call.id}
                call={call}
                selected={call.id === selectedId}
                onClick={() => setSelectedId(call.id)}
              />
            ))}
          </div>
        </div>

        {/* Detail */}
        <div className="lg:col-span-3">
          {selected
            ? <DetailPanel call={selected} />
            : <div className="flex items-center justify-center h-48 text-sm text-slate-400 dark:text-slate-500">Select a call to view details</div>
          }
        </div>
      </div>
    </div>
  )
}
