/**
 * Component 64 — TTS client tests.
 *
 * Covers synthesizeSpeech() and synthesizeGeminiSpeech():
 * - Cartesia success returns TtsSynthesizeResponse
 * - Server ok=false returns null (so caller falls back to browser voice)
 * - Network error returns null
 * - Timeout returns null
 * - Missing audioBase64 returns null
 * - CARTESIA_API_KEY never appears in request
 * - synthesizeGeminiSpeech returns null on failure (never throws)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { synthesizeSpeech, synthesizeGeminiSpeech } from '../tts-client'

// ── helpers ───────────────────────────────────────────────────────────────────

type FetchStub = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>

function mockFetch(status: number, body: unknown): void {
  const ok = status >= 200 && status < 300
  vi.stubGlobal('fetch', vi.fn<FetchStub>().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  } as Response))
}

function mockFetchReject(err: Error): void {
  vi.stubGlobal('fetch', vi.fn<FetchStub>().mockRejectedValue(err))
}

beforeEach(() => {
  vi.unstubAllGlobals()
})
afterEach(() => {
  vi.restoreAllMocks()
})

// ── synthesizeSpeech ─────────────────────────────────────────────────────────

describe('synthesizeSpeech', () => {
  it('returns response when Cartesia succeeds', async () => {
    mockFetch(200, {
      ok: true,
      provider: 'cartesia',
      voiceName: 'Skylar',
      mimeType: 'audio/wav',
      audioBase64: 'UklGRg==',
      reason: '',
      errorCode: '',
      fallback: 'browser',
    })
    const result = await synthesizeSpeech({ text: 'Your copay is $30.' })
    expect(result).not.toBeNull()
    expect(result?.ok).toBe(true)
    expect(result?.provider).toBe('cartesia')
    expect(result?.voiceName).toBe('Skylar')
    expect(result?.audioBase64).toBe('UklGRg==')
    expect(result?.errorCode).toBe('')
  })

  it('returns null when ok=false (server fallback signal)', async () => {
    mockFetch(200, {
      ok: false,
      provider: 'system',
      voiceName: '',
      mimeType: '',
      audioBase64: '',
      reason: 'cartesia_timeout',
      errorCode: 'cartesia_timeout',
      fallback: 'browser',
    })
    const result = await synthesizeSpeech({ text: 'test' })
    expect(result).toBeNull()
  })

  it('returns null when audioBase64 is empty', async () => {
    mockFetch(200, {
      ok: true,
      provider: 'cartesia',
      voiceName: 'Skylar',
      mimeType: 'audio/wav',
      audioBase64: '',
      reason: '',
      errorCode: '',
      fallback: 'browser',
    })
    const result = await synthesizeSpeech({ text: 'test' })
    expect(result).toBeNull()
  })

  it('returns null on network error', async () => {
    mockFetchReject(new Error('Failed to fetch'))
    const result = await synthesizeSpeech({ text: 'test' })
    expect(result).toBeNull()
  })

  it('returns null when HTTP status is not ok', async () => {
    mockFetch(500, { error: 'Internal Server Error' })
    const result = await synthesizeSpeech({ text: 'test' })
    expect(result).toBeNull()
  })

  it('returns null on timeout (AbortError)', async () => {
    const err = new DOMException('The operation was aborted.', 'AbortError')
    mockFetchReject(err)
    const result = await synthesizeSpeech({ text: 'test' })
    expect(result).toBeNull()
  })

  it('exposes errorCode from server response', async () => {
    mockFetch(200, {
      ok: true,
      provider: 'cartesia',
      voiceName: 'Skylar',
      mimeType: 'audio/wav',
      audioBase64: 'UklGRg==',
      reason: '',
      errorCode: '',
      fallback: 'browser',
    })
    const result = await synthesizeSpeech({ text: 'test' })
    expect(result?.errorCode).toBeDefined()
  })

  it('sends request to /api/voice-agent/tts endpoint', async () => {
    mockFetch(200, {
      ok: true,
      provider: 'cartesia',
      voiceName: 'Skylar',
      mimeType: 'audio/wav',
      audioBase64: 'UklGRg==',
      reason: '',
      errorCode: '',
      fallback: 'browser',
    })
    await synthesizeSpeech({ text: 'test' })
    const fetchMock = vi.mocked(global.fetch)
    expect(fetchMock).toHaveBeenCalledOnce()
    const [url] = fetchMock.mock.calls[0]
    expect(String(url)).toBe('/api/voice-agent/tts')
  })

  it('never sends cartesia_api_key in request body', async () => {
    mockFetch(200, {
      ok: true,
      provider: 'cartesia',
      voiceName: 'Skylar',
      mimeType: 'audio/wav',
      audioBase64: 'UklGRg==',
      reason: '',
      errorCode: '',
      fallback: 'browser',
    })
    await synthesizeSpeech({ text: 'test' })
    const fetchMock = vi.mocked(global.fetch)
    const [, init] = fetchMock.mock.calls[0]
    const body = init?.body as string
    expect(body).not.toContain('cartesia_api_key')
    expect(body).not.toContain('CARTESIA')
  })
})

// ── synthesizeGeminiSpeech ────────────────────────────────────────────────────

describe('synthesizeGeminiSpeech', () => {
  it('returns null on network error without throwing', async () => {
    mockFetchReject(new Error('Gemini unreachable'))
    const result = await synthesizeGeminiSpeech('test')
    expect(result).toBeNull()
  })

  it('returns null when HTTP error', async () => {
    mockFetch(503, {})
    const result = await synthesizeGeminiSpeech('test')
    expect(result).toBeNull()
  })

  it('returns null when ok=false', async () => {
    mockFetch(200, { ok: false, provider: 'browser', voiceName: '', mimeType: '', audioBase64: '', reason: 'gemini_error', errorCode: 'gemini_error', fallback: 'browser' })
    const result = await synthesizeGeminiSpeech('test')
    expect(result).toBeNull()
  })

  it('returns response when Gemini succeeds', async () => {
    mockFetch(200, {
      ok: true,
      provider: 'cartesia',
      voiceName: 'Gemini',
      mimeType: 'audio/wav',
      audioBase64: 'UklGRg==',
      reason: '',
      errorCode: '',
      fallback: 'browser',
    })
    const result = await synthesizeGeminiSpeech('Hello')
    expect(result).not.toBeNull()
    expect(result?.audioBase64).toBe('UklGRg==')
  })

  it('sends request to /api/voice-agent/gemini-speak endpoint', async () => {
    mockFetch(200, {
      ok: true,
      provider: 'cartesia',
      voiceName: 'Gemini',
      mimeType: 'audio/wav',
      audioBase64: 'UklGRg==',
      reason: '',
      errorCode: '',
      fallback: 'browser',
    })
    await synthesizeGeminiSpeech('test')
    const fetchMock = vi.mocked(global.fetch)
    const [url] = fetchMock.mock.calls[0]
    expect(String(url)).toBe('/api/voice-agent/gemini-speak')
  })
})
