/**
 * Unit tests for the WS-2 shared API client layer (Component 58).
 *
 * Uses vitest's fetch mock — no real network calls are made.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { apiFetch, demoResult, SERVICE_BASE_URLS } from '../api/client'
import type { ApiResult } from '../api/types'

// ── Helpers ───────────────────────────────────────────────────────────────────

function mockFetch(status: number, body: unknown, ok = status >= 200 && status < 300): void {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  }))
}

function mockFetchReject(err: Error): void {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(err))
}

beforeEach(() => {
  vi.unstubAllGlobals()
})
afterEach(() => {
  vi.restoreAllMocks()
})

// ── apiFetch: successful response ─────────────────────────────────────────────

describe('apiFetch — success', () => {
  it('returns ok=true with data on 200', async () => {
    mockFetch(200, { answer: 'Your copay is $30.' })

    const result = await apiFetch<{ answer: string }>('voice-agent', '/respond', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: 'What is my copay?' }),
    })

    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.data.answer).toBe('Your copay is $30.')
      expect(result.statusCode).toBe(200)
      expect(result.source).toBe('real')
      expect(result.service).toBe('voice-agent')
      expect(result.isDemo).toBe(false)
      expect(result.isUnavailable).toBe(false)
    }
  })

  it('builds the URL from SERVICE_BASE_URLS + path', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) })
    vi.stubGlobal('fetch', fetchSpy)

    await apiFetch('eligibility', '/coverage', { method: 'POST', body: '{}' })

    const calledUrl = fetchSpy.mock.calls[0][0] as string
    expect(calledUrl).toBe(`${SERVICE_BASE_URLS['eligibility']}/coverage`)
  })
})

// ── apiFetch: non-2xx responses ────────────────────────────────────────────────

describe('apiFetch — HTTP errors', () => {
  it('returns ok=false with upstream_error code on 422', async () => {
    mockFetch(422, { error: 'validation_error' }, false)

    const result = await apiFetch('voice-agent', '/respond')

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.statusCode).toBe(422)
      expect(result.code).toBe('upstream_error')
      expect(result.isUnavailable).toBe(false)
    }
  })

  it('returns ok=false with service_unavailable on 503', async () => {
    mockFetch(503, { error: 'backend down' }, false)

    const result = await apiFetch('eligibility', '/coverage')

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.code).toBe('service_unavailable')
      expect(result.isUnavailable).toBe(true)
      expect(result.source).toBe('unavailable')
    }
  })
})

// ── apiFetch: network failures ─────────────────────────────────────────────────

describe('apiFetch — network failure', () => {
  it('returns ok=false with network_error on fetch rejection', async () => {
    mockFetchReject(new Error('Failed to fetch'))

    const result = await apiFetch('providers', '/near')

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.code).toBe('network_error')
      expect(result.isUnavailable).toBe(true)
      expect(result.data).toBeNull()
    }
  })

  it('re-throws AbortError so callers can detect cancellation', async () => {
    const abortErr = new Error('aborted')
    abortErr.name = 'AbortError'
    mockFetchReject(abortErr)

    await expect(apiFetch('document-ai', '/card/ocr')).rejects.toMatchObject({ name: 'AbortError' })
  })

  it('returns ok=false with timeout code on TimeoutError', async () => {
    const timeoutErr = new Error('timeout')
    timeoutErr.name = 'TimeoutError'
    mockFetchReject(timeoutErr)

    const result = await apiFetch('voice-agent', '/respond')

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.code).toBe('timeout')
      expect(result.isUnavailable).toBe(true)
    }
  })
})

// ── demoResult ────────────────────────────────────────────────────────────────

describe('demoResult', () => {
  it('marks result as demo with ok=true', () => {
    const result: ApiResult<{ msg: string }> = demoResult('eligibility', { msg: 'demo' })

    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(true)
    expect(result.isUnavailable).toBe(false)
    expect(result.source).toBe('demo')
    expect(result.statusCode).toBe(0)
    if (result.ok) {
      expect(result.data.msg).toBe('demo')
    }
  })
})

// ── Service-specific demo fallbacks ───────────────────────────────────────────

describe('voiceAgentRespond — demo fallback', () => {
  it('returns a demo result when the backend is unavailable', async () => {
    mockFetch(503, { error: 'down' }, false)

    const { voiceAgentRespond } = await import('../api/voice-agent')
    const result = await voiceAgentRespond({ question: 'What is my copay?' })

    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(true)
    if (result.ok) {
      expect(result.data.answer).toBeTruthy()
      expect(result.data.question).toBe('What is my copay?')
    }
  })
})

describe('eligibilityCheckCoverage — demo fallback', () => {
  it('returns a demo result when the service is unavailable', async () => {
    mockFetch(503, {}, false)

    const { eligibilityCheckCoverage } = await import('../api/eligibility')
    const result = await eligibilityCheckCoverage({ service: 'MRI' })

    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(true)
    if (result.ok) {
      expect(result.data.source).toBe('demo')
    }
  })
})

describe('providersSearch — demo fallback', () => {
  it('returns a demo result when the service is unavailable', async () => {
    mockFetch(503, {}, false)

    const { providersSearch } = await import('../api/providers')
    const result = await providersSearch({ specialty: 'Cardiologist' })

    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(true)
    if (result.ok) {
      expect(result.data.providers.length).toBeGreaterThan(0)
    }
  })
})

describe('documentAiOcrCard — demo fallback', () => {
  it('returns a demo result when the service is unavailable', async () => {
    mockFetch(503, {}, false)

    const { documentAiOcrCard } = await import('../api/document-ai')
    const fakeFile = new Blob(['fake'], { type: 'image/jpeg' }) as unknown as File

    // FileReader isn't in Node — stub it so fileToBase64 resolves
    vi.stubGlobal('FileReader', class {
      result = 'data:image/jpeg;base64,ZmFrZQ=='
      onload: (() => void) | null = null
      readAsDataURL() { this.onload?.() }
    })

    const result = await documentAiOcrCard(fakeFile)
    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(true)
    if (result.ok) {
      // updated shape: card_id instead of member_id at top level
      expect(result.data.card_id).toBe('demo')
    }
  })
})

// ── Service status helpers ────────────────────────────────────────────────────

describe('checkAllServices', () => {
  it('marks services as real when health probes return 200', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) }))

    const { checkAllServices } = await import('../api/status')
    const statuses = await checkAllServices()

    expect(statuses.voiceAgent.dataMode).toBe('real')
    expect(statuses.eligibility.dataMode).toBe('real')
    expect(statuses.providers.dataMode).toBe('real')
    expect(statuses.documentAi.dataMode).toBe('real')
  })

  it('marks services as unavailable when health probes fail', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('ECONNREFUSED')))

    const { checkAllServices } = await import('../api/status')
    const statuses = await checkAllServices()

    expect(statuses.voiceAgent.dataMode).toBe('unavailable')
    expect(statuses.eligibility.dataMode).toBe('unavailable')
    expect(statuses.providers.dataMode).toBe('unavailable')
    expect(statuses.documentAi.dataMode).toBe('unavailable')
  })
})

describe('toLedStatus', () => {
  it('maps real → connected, demo → demo, unavailable → offline', async () => {
    const { toLedStatus } = await import('../api/status')

    expect(toLedStatus({ service: 'voice-agent', displayLabel: 'Voice Agent', dataMode: 'real',        checkedAt: '' })).toBe('connected')
    expect(toLedStatus({ service: 'eligibility',  displayLabel: 'Eligibility',  dataMode: 'demo',        checkedAt: '' })).toBe('demo')
    expect(toLedStatus({ service: 'providers',    displayLabel: 'Providers',    dataMode: 'unavailable', checkedAt: '' })).toBe('offline')
  })
})
