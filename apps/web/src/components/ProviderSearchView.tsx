'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Search, MapPin, Phone, Star, ShieldCheck, ShieldOff,
  UserCheck, UserX, ChevronRight, Info, AlertTriangle, RefreshCw, Loader2,
} from 'lucide-react'
import {
  providersSearch,
  normalizeProviderOut,
  type ProviderCard,
} from '@/lib/api/providers'

// ── Constants ─────────────────────────────────────────────────────────────────

const SPECIALTIES = [
  'All specialties',
  'Primary Care',
  'Internal Medicine',
  'Cardiology',
  'Dermatology',
  'Orthopedic Surgery',
  'Psychiatry',
  'Radiology',
  'Obstetrics & Gynecology',
  'Ophthalmology',
]

const US_STATES = [
  '', 'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
  'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
  'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
  'VA','WA','WV','WI','WY',
]

// ── Source badge ──────────────────────────────────────────────────────────────

function SourceBadge({ isDemo }: { isDemo: boolean }) {
  if (!isDemo) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-700">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
        Providers service
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-700">
      Demo fallback
    </span>
  )
}

// ── Star rating ───────────────────────────────────────────────────────────────

function Stars({ rating }: { rating: number }) {
  return (
    <span className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map(n => (
        <Star
          key={n}
          size={11}
          className={n <= Math.round(rating)
            ? 'text-amber-400 fill-amber-400'
            : 'text-slate-300 dark:text-slate-600'}
        />
      ))}
    </span>
  )
}

// ── Provider card ─────────────────────────────────────────────────────────────

function ProviderCardItem({ p, selected, onSelect }: {
  p: ProviderCard
  selected: boolean
  onSelect: () => void
}) {
  return (
    <button
      onClick={onSelect}
      className={[
        'w-full text-left rounded-xl border p-4 transition-all',
        selected
          ? 'border-blue-400 bg-blue-50 dark:bg-blue-950/30 dark:border-blue-600 shadow-sm'
          : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-600 hover:shadow-sm',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-900 dark:text-white truncate">{p.displayName}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{p.specialty}</p>
        </div>
        <ChevronRight size={14} className={`shrink-0 mt-0.5 transition-colors ${selected ? 'text-blue-500' : 'text-slate-300 dark:text-slate-600'}`} />
      </div>

      <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5">
        {p.inNetwork ? (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 dark:text-green-400">
            <ShieldCheck size={11} /> In-network
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-red-600 dark:text-red-400">
            <ShieldOff size={11} /> Out-of-network
          </span>
        )}

        {p.acceptingPatients ? (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 dark:text-blue-400">
            <UserCheck size={11} /> Accepting patients
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-400 dark:text-slate-500">
            <UserX size={11} /> Not accepting
          </span>
        )}

        {p.distanceMi != null && (
          <span className="inline-flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
            <MapPin size={11} /> {p.distanceMi} mi
          </span>
        )}
      </div>

      {p.qualityRating != null && (
        <div className="mt-2 flex items-center gap-2">
          <Stars rating={p.qualityRating} />
          <span className="text-xs text-slate-500 dark:text-slate-400">{p.qualityRating.toFixed(1)}</span>
        </div>
      )}

      {p.city && (
        <p className="mt-1.5 text-xs text-slate-400 dark:text-slate-500 truncate">
          {p.city}{p.state ? `, ${p.state}` : ''}
        </p>
      )}
    </button>
  )
}

// ── Detail panel ──────────────────────────────────────────────────────────────

function DetailPanel({ p }: { p: ProviderCard }) {
  const fullAddress = [p.address, p.city, p.state, p.zip].filter(Boolean).join(', ')

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden h-full">
      <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800 bg-blue-50 dark:bg-blue-950/20">
        <p className="text-base font-bold text-slate-900 dark:text-white">{p.displayName}</p>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{p.specialty}</p>
        {p.qualityRating != null && (
          <div className="mt-2 flex items-center gap-2">
            <Stars rating={p.qualityRating} />
            <span className="text-xs text-slate-500 dark:text-slate-400">{p.qualityRating.toFixed(1)}</span>
          </div>
        )}
      </div>

      <div className="px-5 py-4 space-y-4">
        <div className="flex gap-2 flex-wrap">
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
            p.inNetwork
              ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
              : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
          }`}>
            {p.inNetwork ? <ShieldCheck size={11} /> : <ShieldOff size={11} />}
            {p.inNetwork ? 'In-network' : 'Out-of-network'}
          </span>
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
            p.acceptingPatients
              ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
              : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
          }`}>
            {p.acceptingPatients ? <UserCheck size={11} /> : <UserX size={11} />}
            {p.acceptingPatients ? 'Accepting patients' : 'Not accepting'}
          </span>
        </div>

        <div className="space-y-2.5 text-sm">
          {fullAddress && (
            <div className="flex items-start gap-2.5">
              <MapPin size={14} className="text-slate-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-slate-700 dark:text-slate-300">{fullAddress}</p>
                {p.distanceMi != null && (
                  <p className="text-xs text-slate-400 dark:text-slate-500">{p.distanceMi} mi away</p>
                )}
              </div>
            </div>
          )}
          {p.phone && (
            <div className="flex items-center gap-2.5">
              <Phone size={14} className="text-slate-400 shrink-0" />
              <p className="text-slate-700 dark:text-slate-300">{p.phone}</p>
            </div>
          )}
          <div className="flex items-center gap-2.5">
            <Info size={14} className="text-slate-400 shrink-0" />
            <p className="text-xs text-slate-500 dark:text-slate-400">NPI {p.npi}</p>
          </div>
        </div>

        {p.note && (
          <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800/50 text-xs text-amber-800 dark:text-amber-300">
            {p.note}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

type SearchState = 'idle' | 'loading' | 'loaded' | 'error'

interface SearchResult {
  providers: ProviderCard[]
  total: number
  isDemo: boolean
}

export default function ProviderSearchView() {
  const [query, setQuery]             = useState('')
  const [specialty, setSpecialty]     = useState('All specialties')
  const [stateFilter, setStateFilter] = useState('')
  const [acceptingOnly, setAccepting] = useState(false)
  const [selectedId, setSelectedId]   = useState<string | null>(null)
  const [searchState, setSearchState] = useState<SearchState>('idle')
  const [result, setResult]           = useState<SearchResult | null>(null)
  const [errorMsg, setErrorMsg]       = useState('')
  const abortRef = useRef<AbortController | null>(null)

  const runSearch = useCallback(async () => {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl

    setSearchState('loading')
    setErrorMsg('')

    let apiResult: Awaited<ReturnType<typeof providersSearch>>
    try {
      apiResult = await providersSearch(
        {
          specialty: specialty !== 'All specialties' ? specialty : undefined,
          state: stateFilter || undefined,
          acceptingNewPatients: acceptingOnly || undefined,
          limit: 50,
        },
        ctrl.signal,
      )
    } catch (err) {
      // apiFetch re-throws AbortError on cancellation (StrictMode remount in dev,
      // a superseding search, or navigating away). That's expected — exit quietly
      // so it never surfaces as an unhandled rejection / full-screen dev overlay.
      if (err instanceof Error && err.name === 'AbortError') return
      setSearchState('error')
      setErrorMsg(err instanceof Error ? err.message : 'Search failed.')
      return
    }

    if (ctrl.signal.aborted) return

    if (!apiResult.ok) {
      setSearchState('error')
      setErrorMsg(apiResult.error ?? 'Search failed.')
      return
    }

    // Client-side name filter (the backend doesn't support free-text name search)
    let cards = apiResult.data.providers.map(p => normalizeProviderOut(p))
    if (query.trim()) {
      const q = query.toLowerCase()
      cards = cards.filter(p =>
        p.displayName.toLowerCase().includes(q) ||
        p.specialty.toLowerCase().includes(q) ||
        p.city.toLowerCase().includes(q)
      )
    }

    setResult({ providers: cards, total: cards.length, isDemo: apiResult.isDemo })
    setSelectedId(cards[0]?.id ?? null)
    setSearchState('loaded')
  }, [specialty, stateFilter, acceptingOnly, query])

  // Initial search on mount
  useEffect(() => {
    runSearch()
    return () => abortRef.current?.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const selected = result?.providers.find(p => p.id === selectedId) ?? null

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Find Providers</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Search in-network doctors and specialists
          </p>
        </div>
        {result && <SourceBadge isDemo={result.isDemo} />}
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
        <div className="flex flex-wrap gap-3">
          {/* Name / text search */}
          <div className="relative flex-1 min-w-48">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Name, specialty, or city"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && runSearch()}
              className="w-full pl-8 pr-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Specialty */}
          <select
            value={specialty}
            onChange={e => setSpecialty(e.target.value)}
            className="px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {SPECIALTIES.map(s => <option key={s}>{s}</option>)}
          </select>

          {/* State */}
          <select
            value={stateFilter}
            onChange={e => setStateFilter(e.target.value)}
            className="px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All states</option>
            {US_STATES.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
          </select>

          {/* Accepting patients toggle */}
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <button
              role="switch"
              aria-checked={acceptingOnly}
              onClick={() => setAccepting(v => !v)}
              className={`relative w-9 h-5 rounded-full transition-colors ${acceptingOnly ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'}`}
            >
              <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${acceptingOnly ? 'translate-x-4' : 'translate-x-0'}`} />
            </button>
            <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Accepting patients</span>
          </label>

          {/* Search button */}
          <button
            onClick={runSearch}
            disabled={searchState === 'loading'}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {searchState === 'loading'
              ? <><Loader2 size={14} className="animate-spin" /> Searching…</>
              : <><Search size={14} /> Search</>}
          </button>
        </div>
      </div>

      {/* Error state */}
      {searchState === 'error' && (
        <div className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/20 px-5 py-4 flex items-start gap-3">
          <AlertTriangle size={16} className="text-red-500 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-red-800 dark:text-red-300">Search failed</p>
            <p className="text-xs text-red-600 dark:text-red-400 mt-0.5">{errorMsg}</p>
          </div>
          <button
            onClick={runSearch}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-red-700 dark:text-red-400 hover:underline shrink-0"
          >
            <RefreshCw size={12} /> Retry
          </button>
        </div>
      )}

      {/* Results + detail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        {/* List */}
        <div className="space-y-2">
          {searchState === 'loading' && (
            <div className="flex items-center justify-center py-12 gap-2 text-slate-400">
              <Loader2 size={20} className="animate-spin" />
              <span className="text-sm">Searching providers…</span>
            </div>
          )}

          {searchState === 'loaded' && result && (
            <>
              <p className="text-xs font-medium text-slate-400 dark:text-slate-500 px-1">
                {result.total} provider{result.total !== 1 ? 's' : ''} found
              </p>
              {result.providers.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700 py-12 bg-white dark:bg-slate-900">
                  <MapPin size={28} className="text-slate-300 dark:text-slate-600 mb-2" strokeWidth={1.5} />
                  <p className="text-sm text-slate-400 dark:text-slate-500">No providers match your filters</p>
                  <button onClick={runSearch} className="mt-3 text-xs text-blue-500 hover:underline">Clear and retry</button>
                </div>
              ) : (
                result.providers.map(p => (
                  <ProviderCardItem
                    key={p.id}
                    p={p}
                    selected={selectedId === p.id}
                    onSelect={() => setSelectedId(p.id)}
                  />
                ))
              )}
            </>
          )}

          {searchState === 'idle' && (
            <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700 py-12 bg-white dark:bg-slate-900">
              <Search size={28} className="text-slate-300 dark:text-slate-600 mb-2" strokeWidth={1.5} />
              <p className="text-sm text-slate-400 dark:text-slate-500">Use the filters above to search</p>
            </div>
          )}
        </div>

        {/* Detail panel */}
        <div className="sticky top-4">
          {selected ? (
            <DetailPanel p={selected} />
          ) : (
            <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700 py-16 bg-white dark:bg-slate-900">
              <MapPin size={28} className="text-slate-300 dark:text-slate-600 mb-2" strokeWidth={1.5} />
              <p className="text-sm text-slate-400 dark:text-slate-500">Select a provider to see details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
