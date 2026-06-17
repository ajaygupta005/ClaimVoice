'use client'

import { useState, useMemo } from 'react'
import {
  Search, MapPin, Phone, Star, ShieldCheck, ShieldOff,
  UserCheck, UserX, ChevronRight, Info,
} from 'lucide-react'
import { mockProviders, SPECIALTIES, type Provider } from '@/lib/mock-data'

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

function ProviderCard({ p, selected, onSelect }: {
  p: Provider
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
          <p className="text-sm font-semibold text-slate-900 dark:text-white truncate">{p.name}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {p.specialty}{p.subspecialty ? ` · ${p.subspecialty}` : ''}
          </p>
        </div>
        <ChevronRight size={14} className={`shrink-0 mt-0.5 transition-colors ${selected ? 'text-blue-500' : 'text-slate-300 dark:text-slate-600'}`} />
      </div>

      <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5">
        {/* Network badge */}
        {p.inNetwork ? (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 dark:text-green-400">
            <ShieldCheck size={11} /> In-network
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-red-600 dark:text-red-400">
            <ShieldOff size={11} /> Out-of-network
          </span>
        )}

        {/* Accepting */}
        {p.acceptingPatients ? (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 dark:text-blue-400">
            <UserCheck size={11} /> Accepting patients
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-400 dark:text-slate-500">
            <UserX size={11} /> Not accepting
          </span>
        )}

        {/* Distance */}
        <span className="inline-flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
          <MapPin size={11} /> {p.distanceMi} mi
        </span>
      </div>

      <div className="mt-2 flex items-center gap-2">
        <Stars rating={p.rating} />
        <span className="text-xs text-slate-500 dark:text-slate-400">{p.rating} ({p.reviewCount})</span>
      </div>

      <p className="mt-1.5 text-xs text-slate-400 dark:text-slate-500 truncate">{p.neighborhood}</p>
    </button>
  )
}

// ── Detail panel ──────────────────────────────────────────────────────────────

function DetailPanel({ p }: { p: Provider }) {
  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden h-full">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800 bg-blue-50 dark:bg-blue-950/20">
        <p className="text-base font-bold text-slate-900 dark:text-white">{p.name}</p>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
          {p.specialty}{p.subspecialty ? ` · ${p.subspecialty}` : ''}
        </p>
        <div className="mt-2 flex items-center gap-2">
          <Stars rating={p.rating} />
          <span className="text-xs text-slate-500 dark:text-slate-400">{p.rating} · {p.reviewCount} reviews</span>
        </div>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Status badges */}
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

        {/* Details */}
        <div className="space-y-2.5 text-sm">
          <div className="flex items-start gap-2.5">
            <MapPin size={14} className="text-slate-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-slate-700 dark:text-slate-300">{p.address}</p>
              <p className="text-xs text-slate-400 dark:text-slate-500">{p.distanceMi} mi away · {p.neighborhood}</p>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <Phone size={14} className="text-slate-400 shrink-0" />
            <p className="text-slate-700 dark:text-slate-300">{p.phone}</p>
          </div>
          <div className="flex items-center gap-2.5">
            <Info size={14} className="text-slate-400 shrink-0" />
            <p className="text-xs text-slate-500 dark:text-slate-400">NPI {p.npi}</p>
          </div>
        </div>

        {/* Note */}
        {p.note && (
          <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800/50 text-xs text-amber-800 dark:text-amber-300">
            {p.note}
          </div>
        )}

        {/* Mock map */}
        <div className="rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
          <div className="h-36 bg-slate-100 dark:bg-slate-800 flex flex-col items-center justify-center gap-1.5">
            <MapPin size={20} className="text-slate-300 dark:text-slate-600" />
            <p className="text-xs text-slate-400 dark:text-slate-500 font-medium">Map — demo placeholder</p>
            <p className="text-xs text-slate-400 dark:text-slate-500">{p.lat.toFixed(4)}, {p.lng.toFixed(4)}</p>
          </div>
          <div className="px-3 py-2 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-700">
            <p className="text-xs text-slate-400 dark:text-slate-500">
              Interactive map (Leaflet + PostGIS) will be wired in WS-5
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ProviderSearchView() {
  const [query, setQuery]               = useState('')
  const [specialty, setSpecialty]       = useState('All specialties')
  const [maxDist, setMaxDist]           = useState(5)
  const [networkOnly, setNetworkOnly]   = useState(true)
  const [acceptingOnly, setAccepting]   = useState(false)
  const [selectedId, setSelectedId]     = useState<string | null>(mockProviders[0].id)

  const filtered = useMemo(() => mockProviders.filter(p => {
    if (networkOnly && !p.inNetwork) return false
    if (acceptingOnly && !p.acceptingPatients) return false
    if (p.distanceMi > maxDist) return false
    if (specialty !== 'All specialties' && p.specialty !== specialty) return false
    if (query) {
      const q = query.toLowerCase()
      return p.name.toLowerCase().includes(q) || p.specialty.toLowerCase().includes(q) || p.neighborhood.toLowerCase().includes(q)
    }
    return true
  }), [query, specialty, maxDist, networkOnly, acceptingOnly])

  const selected = mockProviders.find(p => p.id === selectedId) ?? null

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Find Providers</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
          In-network doctors near you · Silver PPO 4500 · NYC demo data
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
        <div className="flex flex-wrap gap-3">
          {/* Search */}
          <div className="relative flex-1 min-w-48">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Name, specialty, or neighborhood"
              value={query}
              onChange={e => setQuery(e.target.value)}
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

          {/* Distance */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400 shrink-0">Within</span>
            <select
              value={maxDist}
              onChange={e => setMaxDist(Number(e.target.value))}
              className="px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {[1, 2, 5, 10, 25].map(d => <option key={d} value={d}>{d} mi</option>)}
            </select>
          </div>

          {/* Toggles */}
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <button
              role="switch"
              aria-checked={networkOnly}
              onClick={() => setNetworkOnly(v => !v)}
              className={`relative w-9 h-5 rounded-full transition-colors ${networkOnly ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'}`}
            >
              <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${networkOnly ? 'translate-x-4' : 'translate-x-0'}`} />
            </button>
            <span className="text-xs font-medium text-slate-600 dark:text-slate-400">In-network only</span>
          </label>

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
        </div>
      </div>

      {/* Results + detail panel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        {/* Results list */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-slate-400 dark:text-slate-500 px-1">
            {filtered.length} provider{filtered.length !== 1 ? 's' : ''} found
          </p>
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700 py-12 bg-white dark:bg-slate-900">
              <MapPin size={28} className="text-slate-300 dark:text-slate-600 mb-2" strokeWidth={1.5} />
              <p className="text-sm text-slate-400 dark:text-slate-500">No providers match your filters</p>
            </div>
          ) : (
            filtered.map(p => (
              <ProviderCard
                key={p.id}
                p={p}
                selected={selectedId === p.id}
                onSelect={() => setSelectedId(p.id)}
              />
            ))
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
