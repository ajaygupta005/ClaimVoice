'use client'

import { useEffect, useState } from 'react'
import { ShieldCheck, AlertTriangle, MessageCircle, ChevronDown, ChevronUp } from 'lucide-react'
import {
  mockMember, mockPlan, mockCostSummary,
  mockCoverageHighlights, mockPriorAuthNotes, mockExampleQuestions,
} from '@/lib/mock-data'

const MEMBER_ID = 'CVX-0042-MT'  // demo member until auth-based member context lands
const usd = (cents: number) => '$' + Math.round((cents ?? 0) / 100).toLocaleString()

// ── Deductible progress bar ───────────────────────────────────────────────────

function DeductibleBar({ used, max }: { used: string; max: string }) {
  const usedN = parseFloat(used.replace(/[$,]/g, ''))
  const maxN  = parseFloat(max.replace(/[$,]/g, ''))
  const pct   = Math.min(100, Math.round((usedN / maxN) * 100))
  return (
    <div className="mt-2 space-y-1">
      <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>{used} used</span>
        <span>{max} max</span>
      </div>
      <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden">
        <div className="h-full rounded-full bg-blue-500 transition-all" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-slate-400 dark:text-slate-500">{pct}% of limit reached</p>
    </div>
  )
}

// ── Section wrapper ───────────────────────────────────────────────────────────

function Section({ title, icon, children }: {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2">
        <span className="text-slate-400 dark:text-slate-500">{icon}</span>
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">{title}</h2>
      </div>
      {children}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function PlanDetailsView() {
  const [paExpanded, setPaExpanded] = useState(false)

  // Live data with mock as the initial value + graceful fallback (offline / API down).
  const [member, setMember]           = useState(mockMember)
  const [plan, setPlan]               = useState(mockPlan)
  const [costSummary, setCostSummary] = useState(mockCostSummary)
  const [live, setLive]               = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const s = await fetch(`/api/eligibility/members/${MEMBER_ID}/summary`)
          .then(r => (r.ok ? r.json() : null))
        if (!cancelled && s?.member && s?.plan) {
          setMember({
            name: s.member.name ?? mockMember.name,
            plan: s.plan.name ?? mockMember.plan,
            status: s.member.eligibilityStatus ?? mockMember.status,
            memberId: s.member.memberId ?? mockMember.memberId,
          })
          setPlan({
            ...mockPlan,
            planName: s.plan.name ?? mockPlan.planName,
            carrier: s.plan.issuer ?? mockPlan.carrier,
            planType: s.plan.type ?? mockPlan.planType,
            metalLevel: s.plan.metalLevel ?? mockPlan.metalLevel,
            planYear: s.plan.year ?? mockPlan.planYear,
          })
          setLive(true)
        }

        const c = await fetch('/api/eligibility/cost/estimate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ memberId: MEMBER_ID, costType: 'deductible' }),
        }).then(r => (r.ok ? r.json() : null))
        if (!cancelled && c && c.deductibleTotalCents != null) {
          setCostSummary([
            {
              label: 'Individual Deductible',
              value: usd(c.deductibleTotalCents),
              used: usd(c.deductibleSpentCents),
              max: usd(c.deductibleTotalCents),
              note: 'In-network, applied this plan year',
            },
            {
              label: 'Out-of-Pocket Maximum',
              value: usd(c.oopMaxCents),
              used: usd(c.oopSpentCents),
              max: usd(c.oopMaxCents),
              note: 'In-network',
            },
          ])
        }
      } catch {
        /* keep mock fallback */
      }
    })()
    return () => { cancelled = true }
  }, [])

  return (
    <div className="space-y-6">

      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Plan Details</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
          Coverage summary for {member.name} · {plan.planYear}
          {live && <span className="ml-2 text-xs text-green-600 dark:text-green-400">● live</span>}
        </p>
      </div>

      {/* Member + plan summary */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-1">Member</p>
            <p className="text-lg font-bold text-slate-900 dark:text-white">{member.name}</p>
            <p className="text-sm text-slate-500 dark:text-slate-400">{member.memberId} · Group {plan.groupNumber}</p>
          </div>
          <div className="text-right">
            <p className="text-xs font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-1">Plan</p>
            <p className="text-lg font-bold text-slate-900 dark:text-white">{plan.planName}</p>
            <p className="text-sm text-slate-500 dark:text-slate-400">{plan.carrier} · {plan.planType}</p>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex gap-3 flex-wrap">
          {[
            { label: 'Metal Level', value: plan.metalLevel },
            { label: 'Network',     value: plan.network },
            { label: 'Effective',   value: plan.effectiveDate },
            { label: 'Status',      value: member.status },
          ].map(({ label, value }) => (
            <div key={label} className="px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <p className="text-xs text-slate-400 dark:text-slate-500">{label}</p>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">{value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Cost summary */}
      <Section title="Deductibles, Copays & Out-of-Pocket" icon={<ShieldCheck size={15} />}>
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {costSummary.map(row => (
            <div key={row.label} className="px-5 py-3 flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{row.label}</p>
                {row.note && <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{row.note}</p>}
                {row.used && row.max && <DeductibleBar used={row.used} max={row.max} />}
              </div>
              <p className="text-sm font-bold text-slate-900 dark:text-white shrink-0">{row.value}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Coverage highlights */}
      <Section title="Coverage Highlights" icon={<ShieldCheck size={15} />}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800">
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Service</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">In-Network</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Out-of-Network</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Prior Auth</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {mockCoverageHighlights.map(row => (
                <tr key={row.service} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                  <td className="px-5 py-3 font-medium text-slate-800 dark:text-slate-200">{row.service}</td>
                  <td className="px-5 py-3 text-slate-600 dark:text-slate-400">{row.inNetwork}</td>
                  <td className="px-5 py-3 text-slate-500 dark:text-slate-500">{row.outOfNetwork}</td>
                  <td className="px-5 py-3">
                    {row.requiresPriorAuth ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                        <AlertTriangle size={10} /> Required
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400 dark:text-slate-600">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      {/* Prior authorization */}
      <Section title="Prior Authorization Notes" icon={<AlertTriangle size={15} />}>
        <div className="px-5 py-4 space-y-2">
          {(paExpanded ? mockPriorAuthNotes : mockPriorAuthNotes.slice(0, 3)).map((note, i) => (
            <div key={i} className="flex items-start gap-2.5">
              <AlertTriangle size={13} className="text-amber-400 mt-0.5 shrink-0" />
              <p className="text-sm text-slate-700 dark:text-slate-300">{note}</p>
            </div>
          ))}
          {mockPriorAuthNotes.length > 3 && (
            <button
              onClick={() => setPaExpanded(v => !v)}
              className="flex items-center gap-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline mt-1"
            >
              {paExpanded ? <><ChevronUp size={12} /> Show less</> : <><ChevronDown size={12} /> Show {mockPriorAuthNotes.length - 3} more</>}
            </button>
          )}
        </div>
      </Section>

      {/* Example questions */}
      <Section title="Questions You Can Ask" icon={<MessageCircle size={15} />}>
        <div className="px-5 py-4 grid grid-cols-1 sm:grid-cols-2 gap-2">
          {mockExampleQuestions.map(({ q, hint }) => (
            <div
              key={q}
              className="flex items-start gap-2.5 p-3 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700"
            >
              <MessageCircle size={13} className="text-blue-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm text-slate-700 dark:text-slate-200">{q}</p>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{hint}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>

    </div>
  )
}
