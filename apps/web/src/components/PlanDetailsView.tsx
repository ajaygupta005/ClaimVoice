'use client'

import { useState, useEffect, useCallback } from 'react'
import { ShieldCheck, AlertTriangle, MessageCircle, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'
import {
  eligibilityGetMemberSummary,
  eligibilityGetPlanBenefits,
  type MemberSummaryResponse,
  type BenefitsResponse,
  type BenefitOut,
} from '@/lib/api/eligibility'
import { mockExampleQuestions } from '@/lib/mock-data'

// Demo member used when no authenticated session is available.
// Replace with session-derived member ID when auth is wired.
const DEMO_MEMBER_ID = 'CVX-0042-MT'

// ── Helpers ───────────────────────────────────────────────────────────────────

function centsToDisplay(cents: number | null | undefined): string {
  if (cents == null) return '—'
  return `$${(cents / 100).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

function pctToDisplay(pct: number | null | undefined): string {
  if (pct == null) return '—'
  return `${pct}%`
}

function costShareDisplay(benefit: BenefitOut): string {
  if (benefit.copayAmountCents != null) {
    return `${centsToDisplay(benefit.copayAmountCents)} copay`
  }
  if (benefit.coinsurancePercentage != null) {
    return `${pctToDisplay(benefit.coinsurancePercentage)} after deductible`
  }
  return '—'
}

function isAbortError(err: unknown): boolean {
  if (err instanceof Error && err.name === 'AbortError') return true
  return (
    typeof err === 'object' &&
    err !== null &&
    'name' in err &&
    (err as { name?: unknown }).name === 'AbortError'
  )
}

// ── Source badge ──────────────────────────────────────────────────────────────

function SourceBadge({ isDemo }: { isDemo: boolean }) {
  if (!isDemo) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-700">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
        Eligibility
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-700">
      Demo fallback
    </span>
  )
}

// ── Loading skeleton ──────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-slate-200 dark:bg-slate-700 ${className ?? ''}`} />
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading plan details">
      <div>
        <Skeleton className="h-8 w-48 mb-2" />
        <Skeleton className="h-4 w-72" />
      </div>
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-5 space-y-4">
        <div className="flex justify-between flex-wrap gap-4">
          <div className="space-y-2">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-4 w-56" />
          </div>
          <div className="space-y-2 text-right">
            <Skeleton className="h-3 w-12 ml-auto" />
            <Skeleton className="h-6 w-44 ml-auto" />
            <Skeleton className="h-4 w-36 ml-auto" />
          </div>
        </div>
        <div className="flex gap-3 flex-wrap pt-4 border-t border-slate-100 dark:border-slate-800">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-12 w-24 rounded-lg" />)}
        </div>
      </div>
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <Skeleton className="h-12 w-full" />
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-14 w-full mt-px" />)}
      </div>
    </div>
  )
}

// ── Deductible progress bar ───────────────────────────────────────────────────

function DeductibleBar({ usedCents, maxCents }: { usedCents: number; maxCents: number }) {
  const pct = maxCents > 0 ? Math.min(100, Math.round((usedCents / maxCents) * 100)) : 0
  return (
    <div className="mt-2 space-y-1">
      <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>{centsToDisplay(usedCents)} used</span>
        <span>{centsToDisplay(maxCents)} max</span>
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

// ── Unavailable state ─────────────────────────────────────────────────────────

function UnavailableState({ onRetry, loading }: { onRetry: () => void; loading: boolean }) {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-6 py-10 text-center space-y-4">
      <AlertTriangle size={32} className="mx-auto text-amber-400" />
      <div>
        <p className="font-semibold text-slate-800 dark:text-slate-200">Eligibility service unavailable</p>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Could not reach the eligibility service. Retry or continue with demo data below.
        </p>
      </div>
      <button
        onClick={onRetry}
        disabled={loading}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        {loading ? 'Retrying…' : 'Retry'}
      </button>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

type LoadState = 'loading' | 'loaded' | 'unavailable' | 'not_found'

interface PlanData {
  summary: MemberSummaryResponse
  benefits: BenefitsResponse
  isDemo: boolean
}

export default function PlanDetailsView() {
  const [state, setState] = useState<LoadState>('loading')
  const [retrying, setRetrying] = useState(false)
  const [data, setData] = useState<PlanData | null>(null)
  const [paExpanded, setPaExpanded] = useState(false)

  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      setState('loading')
      setData(null)

      const summaryResult = await eligibilityGetMemberSummary(DEMO_MEMBER_ID, signal)
      if (signal?.aborted) return

      if (!summaryResult.ok) {
        if (summaryResult.statusCode === 404) {
          setState('not_found')
        } else {
          setState('unavailable')
        }
        return
      }

      const planId = summaryResult.data.plan.id
      const benefitsResult = await eligibilityGetPlanBenefits(planId, signal)
      if (signal?.aborted) return

      if (!benefitsResult.ok) {
        setState('unavailable')
        return
      }

      setData({
        summary: summaryResult.data,
        benefits: benefitsResult.data,
        isDemo: summaryResult.isDemo || benefitsResult.isDemo,
      })
      setState('loaded')
    } catch (err) {
      if (signal?.aborted || isAbortError(err)) return
      console.warn('[ClaimVoice:PlanDetails] load failed', err)
      setState('unavailable')
    }
  }, [])

  useEffect(() => {
    const ctrl = new AbortController()
    void load(ctrl.signal)
    return () => ctrl.abort()
  }, [load])

  if (state === 'loading') return <LoadingSkeleton />

  if (state === 'unavailable') {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Plan Details</h1>
        </div>
        <UnavailableState
          onRetry={async () => { setRetrying(true); await load(); setRetrying(false) }}
          loading={retrying}
        />
      </div>
    )
  }

  if (state === 'not_found' || data === null) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Plan Details</h1>
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-6 py-10 text-center">
          <p className="font-semibold text-slate-800 dark:text-slate-200">Member not found</p>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            No eligibility record found for this member.
          </p>
        </div>
      </div>
    )
  }

  const { summary, benefits, isDemo } = data
  const { member, plan } = summary

  // Benefits split by network type for the highlights table
  const inNetworkBenefits = benefits.benefits.filter(b => b.networkType === 'in_network' || b.networkType == null)

  // Prior auth services
  const priorAuthBenefits = benefits.benefits.filter(b => b.requiresPriorAuth)

  return (
    <div className="space-y-6">

      {/* Page header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Plan Details</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Coverage summary for {member.name} · {plan.year ?? '—'}
          </p>
        </div>
        <SourceBadge isDemo={isDemo} />
      </div>

      {/* Member + plan summary */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-1">Member</p>
            <p className="text-lg font-bold text-slate-900 dark:text-white">{member.name}</p>
            <p className="text-sm text-slate-500 dark:text-slate-400">{member.memberId}</p>
          </div>
          <div className="text-right">
            <p className="text-xs font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-1">Plan</p>
            <p className="text-lg font-bold text-slate-900 dark:text-white">{plan.name}</p>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {plan.issuer ? `${plan.issuer} · ` : ''}{plan.type ?? '—'}
            </p>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex gap-3 flex-wrap">
          {[
            { label: 'Metal Level',  value: plan.metalLevel ?? '—' },
            { label: 'Plan Type',    value: plan.type ?? '—' },
            { label: 'Plan Year',    value: plan.year ? String(plan.year) : '—' },
            { label: 'Status',       value: member.eligibilityStatus },
          ].map(({ label, value }) => (
            <div key={label} className="px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <p className="text-xs text-slate-400 dark:text-slate-500">{label}</p>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200 capitalize">{value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Deductible / OOP progress */}
      <Section title="Deductible &amp; Out-of-Pocket" icon={<ShieldCheck size={15} />}>
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          <div className="px-5 py-3">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Individual Deductible (YTD)</p>
            <DeductibleBar
              usedCents={member.deductibleYtdCents}
              maxCents={
                inNetworkBenefits.find(b => b.individualDeductibleCents != null)?.individualDeductibleCents
                ?? member.deductibleYtdCents
              }
            />
          </div>
          <div className="px-5 py-3">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Out-of-Pocket (YTD)</p>
            <DeductibleBar
              usedCents={member.oopYtdCents}
              maxCents={
                inNetworkBenefits.find(b => b.outOfPocketMaxCents != null)?.outOfPocketMaxCents
                ?? member.oopYtdCents
              }
            />
          </div>
        </div>
      </Section>

      {/* Benefits table */}
      {inNetworkBenefits.length > 0 && (
        <Section title="Coverage Highlights" icon={<ShieldCheck size={15} />}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800">
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Service</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Cost Share</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Prior Auth</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {inNetworkBenefits.map(b => (
                  <tr key={b.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="px-5 py-3 font-medium text-slate-800 dark:text-slate-200">
                      {b.benefitName ?? b.serviceCategory ?? '—'}
                    </td>
                    <td className="px-5 py-3 text-slate-600 dark:text-slate-400">{costShareDisplay(b)}</td>
                    <td className="px-5 py-3">
                      {b.requiresPriorAuth ? (
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
      )}

      {/* Prior auth services */}
      {priorAuthBenefits.length > 0 && (
        <Section title="Prior Authorization Required" icon={<AlertTriangle size={15} />}>
          <div className="px-5 py-4 space-y-2">
            {(paExpanded ? priorAuthBenefits : priorAuthBenefits.slice(0, 3)).map(b => (
              <div key={b.id} className="flex items-start gap-2.5">
                <AlertTriangle size={13} className="text-amber-400 mt-0.5 shrink-0" />
                <p className="text-sm text-slate-700 dark:text-slate-300">
                  {b.benefitName ?? b.serviceCategory ?? 'Service'} requires prior authorization.
                </p>
              </div>
            ))}
            {priorAuthBenefits.length > 3 && (
              <button
                onClick={() => setPaExpanded(v => !v)}
                className="flex items-center gap-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline mt-1"
              >
                {paExpanded
                  ? <><ChevronUp size={12} /> Show less</>
                  : <><ChevronDown size={12} /> Show {priorAuthBenefits.length - 3} more</>}
              </button>
            )}
          </div>
        </Section>
      )}

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
