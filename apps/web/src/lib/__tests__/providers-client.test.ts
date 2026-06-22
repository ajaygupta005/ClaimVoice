/**
 * Unit tests for the Providers API client and normalization helpers (Component 61).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  normalizeProviderOut,
  normalizeNearItem,
  type ProviderOut,
  type ProviderNearItem,
  type ProviderSearchResponse,
} from '../api/providers'

// ── normalizeProviderOut ──────────────────────────────────────────────────────

const SAMPLE_PROVIDER: ProviderOut = {
  id: 'abc-123',
  npi: '1234567890',
  firstName: 'Jane',
  lastName: 'Smith',
  organizationName: null,
  credentialText: 'MD',
  taxonomyCode: '207Q00000X',
  taxonomyDescription: 'Primary Care',
  addressLine1: '100 Main St',
  city: 'Boston',
  state: 'MA',
  zip: '02101',
  phone: '617-555-0100',
  acceptingNewPatients: true,
  qualityRating: 4.7,
  hospitalName: 'General Hospital',
  specialtyCodes: null,
}

describe('normalizeProviderOut', () => {
  it('formats individual name with credential', () => {
    const card = normalizeProviderOut(SAMPLE_PROVIDER)
    expect(card.displayName).toBe('Jane Smith, MD')
  })

  it('uses organizationName when set', () => {
    const card = normalizeProviderOut({ ...SAMPLE_PROVIDER, organizationName: 'Boston Medical Group' })
    expect(card.displayName).toBe('Boston Medical Group')
  })

  it('falls back to NPI when no name fields', () => {
    const card = normalizeProviderOut({
      ...SAMPLE_PROVIDER,
      firstName: null,
      lastName: null,
      organizationName: null,
      credentialText: null,
    })
    expect(card.displayName).toBe('NPI 1234567890')
  })

  it('maps taxonomyDescription to specialty', () => {
    const card = normalizeProviderOut(SAMPLE_PROVIDER)
    expect(card.specialty).toBe('Primary Care')
  })

  it('falls back to taxonomyCode when description is null', () => {
    const card = normalizeProviderOut({ ...SAMPLE_PROVIDER, taxonomyDescription: null })
    expect(card.specialty).toBe('207Q00000X')
  })

  it('converts distanceKm to miles', () => {
    const card = normalizeProviderOut(SAMPLE_PROVIDER, false, 1.60934)
    expect(card.distanceMi).toBe(1.0)
  })

  it('sets distanceMi to null when no coords', () => {
    const card = normalizeProviderOut(SAMPLE_PROVIDER)
    expect(card.distanceMi).toBeNull()
  })

  it('generates hospital note', () => {
    const card = normalizeProviderOut(SAMPLE_PROVIDER)
    expect(card.note).toBe('Affiliated with General Hospital')
  })

  it('note is null when no hospital', () => {
    const card = normalizeProviderOut({ ...SAMPLE_PROVIDER, hospitalName: null })
    expect(card.note).toBeNull()
  })

  it('passes acceptingNewPatients correctly', () => {
    const card = normalizeProviderOut(SAMPLE_PROVIDER)
    expect(card.acceptingPatients).toBe(true)
  })

  it('defaults acceptingPatients to false when null', () => {
    const card = normalizeProviderOut({ ...SAMPLE_PROVIDER, acceptingNewPatients: null })
    expect(card.acceptingPatients).toBe(false)
  })
})

// ── normalizeNearItem ─────────────────────────────────────────────────────────

describe('normalizeNearItem', () => {
  const NEAR_ITEM: ProviderNearItem = {
    ...SAMPLE_PROVIDER,
    distanceKm: 3.21868,  // exactly 2 miles
    inNetwork: true,
    specialty: 'Cardiology',
  }

  it('uses near item specialty over taxonomyDescription', () => {
    const card = normalizeNearItem(NEAR_ITEM)
    expect(card.specialty).toBe('Cardiology')
  })

  it('converts distance km to miles', () => {
    const card = normalizeNearItem(NEAR_ITEM)
    expect(card.distanceMi).toBe(2.0)
  })

  it('passes inNetwork from near item', () => {
    const card = normalizeNearItem(NEAR_ITEM)
    expect(card.inNetwork).toBe(true)
  })
})

// ── providersSearch — network ─────────────────────────────────────────────────

function mockFetch(status: number, body: unknown, ok = status >= 200 && status < 300): void {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  }))
}

beforeEach(() => vi.unstubAllGlobals())
afterEach(() => vi.restoreAllMocks())

const REAL_SEARCH: ProviderSearchResponse = {
  total: 1,
  providers: [SAMPLE_PROVIDER],
}

describe('providersSearch — success', () => {
  it('returns ok=true with provider list on 200', async () => {
    mockFetch(200, REAL_SEARCH)

    const { providersSearch } = await import('../api/providers')
    const result = await providersSearch({ specialty: 'Primary Care', state: 'MA' })

    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(false)
    if (result.ok) {
      expect(result.data.total).toBe(1)
      expect(result.data.providers[0].npi).toBe('1234567890')
    }
  })

  it('builds query string correctly', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => REAL_SEARCH })
    vi.stubGlobal('fetch', fetchSpy)

    const { providersSearch } = await import('../api/providers')
    await providersSearch({ specialty: 'Cardiology', state: 'NY', acceptingNewPatients: true, limit: 10 })

    const calledUrl = fetchSpy.mock.calls[0][0] as string
    expect(calledUrl).toContain('specialty=Cardiology')
    expect(calledUrl).toContain('state=NY')
    expect(calledUrl).toContain('acceptingNewPatients=true')
    expect(calledUrl).toContain('limit=10')
  })
})

describe('providersSearch — service unavailable', () => {
  it('returns demo fallback on 503', async () => {
    mockFetch(503, { error: 'down' }, false)

    const { providersSearch } = await import('../api/providers')
    const result = await providersSearch({ specialty: 'Primary Care' })

    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(true)
    if (result.ok) {
      expect(result.data.providers.length).toBeGreaterThan(0)
    }
  })

  it('returns demo fallback on network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('ECONNREFUSED')))

    const { providersSearch } = await import('../api/providers')
    const result = await providersSearch({ specialty: 'Primary Care' })

    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(true)
  })
})

describe('providersSearch — empty results', () => {
  it('returns ok=true with empty list', async () => {
    mockFetch(200, { total: 0, providers: [] })

    const { providersSearch } = await import('../api/providers')
    const result = await providersSearch({ specialty: 'Very Rare Specialty' })

    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.data.total).toBe(0)
      expect(result.data.providers).toHaveLength(0)
    }
  })
})
