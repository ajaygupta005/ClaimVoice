/**
 * WS-2 Providers API client.
 *
 * Calls go through /api/providers/* (Next.js proxy → providers service :8003).
 * The service URL never appears in browser-side code.
 *
 * Two search modes:
 *  - searchProviders: specialty + state/zip text search (no coords required)
 *  - searchProvidersNear: geo search with lat/lng (requires browser coords)
 */

import { apiFetch, demoResult } from './client'
import type { ApiResult } from './types'

// ── Backend response shapes (match providers service API v1) ──────────────────

export interface ProviderOut {
  id: string
  npi: string
  firstName: string | null
  lastName: string | null
  organizationName: string | null
  credentialText: string | null
  taxonomyCode: string | null
  taxonomyDescription: string | null
  addressLine1: string | null
  city: string | null
  state: string | null
  zip: string | null
  phone: string | null
  acceptingNewPatients: boolean | null
  qualityRating: number | null
  hospitalName: string | null
  specialtyCodes: string[] | null
}

export interface ProviderNearItem extends ProviderOut {
  distanceKm: number
  inNetwork: boolean
  specialty: string | null
}

export interface ProviderSearchResponse {
  total: number
  providers: ProviderOut[]
}

export interface ProviderNearResponse {
  total: number
  query: Record<string, unknown>
  providers: ProviderNearItem[]
}

// ── Normalized UI card shape ──────────────────────────────────────────────────

export interface ProviderCard {
  id: string
  npi: string
  displayName: string
  specialty: string
  address: string
  city: string
  state: string
  zip: string
  phone: string
  inNetwork: boolean
  acceptingPatients: boolean
  qualityRating: number | null
  distanceMi: number | null
  note: string | null
}

// ── Normalization helpers ─────────────────────────────────────────────────────

function formatName(p: ProviderOut): string {
  if (p.organizationName) return p.organizationName
  const parts = [p.firstName, p.lastName].filter(Boolean)
  const name = parts.join(' ')
  return name ? (p.credentialText ? `${name}, ${p.credentialText}` : name) : `NPI ${p.npi}`
}

function kmToMi(km: number): number {
  return Math.round((km / 1.60934) * 10) / 10
}

export function normalizeProviderOut(p: ProviderOut, inNetwork = false, distanceKm?: number): ProviderCard {
  return {
    id: p.id,
    npi: p.npi,
    displayName: formatName(p),
    specialty: p.taxonomyDescription ?? p.taxonomyCode ?? 'Unknown specialty',
    address: p.addressLine1 ?? '',
    city: p.city ?? '',
    state: p.state ?? '',
    zip: p.zip ?? '',
    phone: p.phone ?? '',
    inNetwork,
    acceptingPatients: p.acceptingNewPatients ?? false,
    qualityRating: p.qualityRating ?? null,
    distanceMi: distanceKm != null ? kmToMi(distanceKm) : null,
    note: p.hospitalName ? `Affiliated with ${p.hospitalName}` : null,
  }
}

export function normalizeNearItem(p: ProviderNearItem): ProviderCard {
  return {
    ...normalizeProviderOut(p, p.inNetwork, p.distanceKm),
    specialty: p.specialty ?? p.taxonomyDescription ?? p.taxonomyCode ?? 'Unknown specialty',
  }
}

// ── Demo data ─────────────────────────────────────────────────────────────────

const DEMO_SEARCH: ProviderSearchResponse = {
  total: 2,
  providers: [
    {
      id: 'demo-p1',
      npi: '0000000001',
      firstName: 'Demo',
      lastName: 'Provider',
      organizationName: null,
      credentialText: 'MD',
      taxonomyCode: '207Q00000X',
      taxonomyDescription: 'Primary Care (demo)',
      addressLine1: '123 Health St',
      city: 'Boston',
      state: 'MA',
      zip: '02101',
      phone: '555-000-0001',
      acceptingNewPatients: true,
      qualityRating: 4.5,
      hospitalName: null,
      specialtyCodes: null,
    },
    {
      id: 'demo-p2',
      npi: '0000000002',
      firstName: 'Demo',
      lastName: 'Specialist',
      organizationName: null,
      credentialText: 'DO',
      taxonomyCode: '207R00000X',
      taxonomyDescription: 'Internal Medicine (demo)',
      addressLine1: '456 Medical Ave',
      city: 'Boston',
      state: 'MA',
      zip: '02101',
      phone: '555-000-0002',
      acceptingNewPatients: false,
      qualityRating: 4.1,
      hospitalName: 'Demo Hospital',
      specialtyCodes: null,
    },
  ],
}

const DEMO_NEAR: ProviderNearResponse = {
  total: 1,
  query: { specialty: 'demo', lat: 0, lng: 0 },
  providers: [
    {
      id: 'demo-p1',
      npi: '0000000001',
      firstName: 'Demo',
      lastName: 'Provider',
      organizationName: null,
      credentialText: 'MD',
      taxonomyCode: '207Q00000X',
      taxonomyDescription: 'Primary Care (demo)',
      addressLine1: '123 Health St',
      city: 'Boston',
      state: 'MA',
      zip: '02101',
      phone: '555-000-0001',
      acceptingNewPatients: true,
      qualityRating: 4.5,
      hospitalName: null,
      specialtyCodes: null,
      distanceKm: 1.6,
      inNetwork: true,
      specialty: 'Primary Care (demo)',
    },
  ],
}

// ── Client functions ──────────────────────────────────────────────────────────

export interface ProviderSearchParams {
  specialty?: string
  state?: string
  zip?: string
  acceptingNewPatients?: boolean
  limit?: number
}

/** Search providers by specialty/state/zip (no coordinates required). */
export async function providersSearch(
  params: ProviderSearchParams,
  signal?: AbortSignal,
): Promise<ApiResult<ProviderSearchResponse>> {
  const qs = new URLSearchParams()
  if (params.specialty) qs.set('specialty', params.specialty)
  if (params.state) qs.set('state', params.state)
  if (params.zip) qs.set('zip', params.zip)
  if (params.acceptingNewPatients != null) qs.set('acceptingNewPatients', String(params.acceptingNewPatients))
  if (params.limit != null) qs.set('limit', String(params.limit))

  const path = `/providers/search${qs.toString() ? `?${qs}` : ''}`
  const result = await apiFetch<ProviderSearchResponse>('providers', path, { signal })
  if (!result.ok && result.isUnavailable) {
    return demoResult('providers', DEMO_SEARCH)
  }
  return result
}

export interface ProviderNearParams {
  specialty: string
  lat: number
  lng: number
  radiusKm?: number
  inNetworkOnly?: boolean
  acceptingNewOnly?: boolean
  planId?: string
  limit?: number
}

/** Search providers near a coordinate. */
export async function providersSearchNear(
  params: ProviderNearParams,
  signal?: AbortSignal,
): Promise<ApiResult<ProviderNearResponse>> {
  const qs = new URLSearchParams({ specialty: params.specialty, lat: String(params.lat), lng: String(params.lng) })
  if (params.radiusKm != null) qs.set('radiusKm', String(params.radiusKm))
  if (params.inNetworkOnly) qs.set('inNetworkOnly', 'true')
  if (params.acceptingNewOnly) qs.set('acceptingNewOnly', 'true')
  if (params.planId) qs.set('planId', params.planId)
  if (params.limit != null) qs.set('limit', String(params.limit))

  const result = await apiFetch<ProviderNearResponse>('providers', `/providers/near?${qs}`, { signal })
  if (!result.ok && result.isUnavailable) {
    return demoResult('providers', DEMO_NEAR)
  }
  return result
}

/** Get a single provider by NPI. */
export async function providersGetByNpi(
  npi: string,
  signal?: AbortSignal,
): Promise<ApiResult<ProviderOut>> {
  const result = await apiFetch<ProviderOut>('providers', `/providers/${encodeURIComponent(npi)}`, { signal })
  if (!result.ok && result.isUnavailable) {
    return demoResult('providers', DEMO_SEARCH.providers[0])
  }
  return result
}
