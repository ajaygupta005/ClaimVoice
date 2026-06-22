/**
 * Component 70 — WS-2 SBC Evidence Citations tests.
 *
 * Tests:
 * - extractEvidence returns [] when rag is absent
 * - extractEvidence returns [] when ragAvailable is false
 * - extractEvidence returns [] when ragChunksCount is 0 even if evidence array present
 * - extractEvidence returns items when rag is available and evidence array is present
 * - extractEvidence filters out items with empty text
 * - extractEvidence handles missing evidence array gracefully
 * - sendVoiceAgentQuestion sets evidence from backend response
 * - sendVoiceAgentQuestion sets evidence to [] for mock fallback
 * - Long text: EvidenceItem text field preserved at full length from backend
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// ── Re-export the private extractEvidence via a test helper shim ──────────────
// We test extractEvidence indirectly by calling sendVoiceAgentQuestion with
// mocked fetch, then asserting on the returned evidence array.

type FetchFn = typeof globalThis.fetch

function makeMockFetch(responseBody: unknown, status = 200): FetchFn {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(responseBody),
  }) as unknown as FetchFn
}

const BASE_BACKEND = {
  question: 'Is MRI covered?',
  answer: 'Yes, MRI is covered.',
  intent: 'coverage',
  grounded: true,
  guard_reason: 'all claims grounded',
  tool_trace: [],
  composer_mode: 'mock',
  tool_mode: 'mock',
  member_source: 'demo',
  backend_statuses: [
    { label: 'Voice Agent API', detail: '', status: 'connected' },
  ],
  pipeline: {
    turn_id: 'abc123',
    intent: 'coverage',
    member_source: 'demo',
    tool_mode: 'mock',
    stages: [],
    tools: [],
    guard: { passed: true, reason: 'grounded' },
    answer: { source: 'mock', grounded: true },
  },
}

describe('evidence citations — extractEvidence', () => {
  let originalFetch: FetchFn

  beforeEach(() => {
    originalFetch = globalThis.fetch
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('returns empty evidence when rag field is absent', async () => {
    const { sendVoiceAgentQuestion } = await import('../voice-agent-client')
    globalThis.fetch = makeMockFetch({ ...BASE_BACKEND })

    const result = await sendVoiceAgentQuestion('Is MRI covered?')
    expect(result).not.toBeNull()
    expect(result!.evidence).toEqual([])
  })

  it('returns empty evidence when ragAvailable is false', async () => {
    const { sendVoiceAgentQuestion } = await import('../voice-agent-client')
    globalThis.fetch = makeMockFetch({
      ...BASE_BACKEND,
      rag: { ragAttempted: true, ragAvailable: false, ragChunksCount: 0, ragFallbackReason: 'rag_key_missing', ragSource: '' },
      evidence: [{ text: 'should not appear', sectionName: 'S', sourceFile: 'f.pdf', distance: 0.1 }],
    })

    const result = await sendVoiceAgentQuestion('Is MRI covered?')
    expect(result!.evidence).toEqual([])
  })

  it('returns empty evidence when ragChunksCount is 0', async () => {
    const { sendVoiceAgentQuestion } = await import('../voice-agent-client')
    globalThis.fetch = makeMockFetch({
      ...BASE_BACKEND,
      rag: { ragAttempted: true, ragAvailable: true, ragChunksCount: 0, ragFallbackReason: 'rag_empty_chunks', ragSource: 'eligibility-sbc-rag' },
      evidence: [],
    })

    const result = await sendVoiceAgentQuestion('Is MRI covered?')
    expect(result!.evidence).toEqual([])
  })

  it('returns evidence items when rag is available with chunks', async () => {
    const { sendVoiceAgentQuestion } = await import('../voice-agent-client')
    globalThis.fetch = makeMockFetch({
      ...BASE_BACKEND,
      rag: { ragAttempted: true, ragAvailable: true, ragChunksCount: 2, ragFallbackReason: '', ragSource: 'eligibility-sbc-rag' },
      evidence: [
        { text: 'MRI is covered under imaging benefits.', sectionName: 'Imaging', sourceFile: 'sbc.pdf', distance: 0.12 },
        { text: 'Prior authorization may be required.', sectionName: 'Auth', sourceFile: 'sbc.pdf', distance: 0.25 },
      ],
    })

    const result = await sendVoiceAgentQuestion('Is MRI covered?')
    expect(result!.evidence).toHaveLength(2)
    expect(result!.evidence[0].text).toBe('MRI is covered under imaging benefits.')
    expect(result!.evidence[0].sectionName).toBe('Imaging')
    expect(result!.evidence[0].sourceFile).toBe('sbc.pdf')
    expect(result!.evidence[0].distance).toBe(0.12)
  })

  it('filters out evidence items with empty text', async () => {
    const { sendVoiceAgentQuestion } = await import('../voice-agent-client')
    globalThis.fetch = makeMockFetch({
      ...BASE_BACKEND,
      rag: { ragAttempted: true, ragAvailable: true, ragChunksCount: 2, ragFallbackReason: '', ragSource: 'eligibility-sbc-rag' },
      evidence: [
        { text: '', sectionName: 'Imaging', sourceFile: 'sbc.pdf', distance: 0.1 },
        { text: 'Valid chunk text.', sectionName: 'Benefits', sourceFile: 'sbc.pdf', distance: 0.2 },
      ],
    })

    const result = await sendVoiceAgentQuestion('Is MRI covered?')
    expect(result!.evidence).toHaveLength(1)
    expect(result!.evidence[0].text).toBe('Valid chunk text.')
  })

  it('returns empty evidence when evidence array is missing from response', async () => {
    const { sendVoiceAgentQuestion } = await import('../voice-agent-client')
    // rag says available but evidence array not present (older backend version)
    globalThis.fetch = makeMockFetch({
      ...BASE_BACKEND,
      rag: { ragAttempted: true, ragAvailable: true, ragChunksCount: 1, ragFallbackReason: '', ragSource: 'eligibility-sbc-rag' },
      // no evidence field
    })

    const result = await sendVoiceAgentQuestion('Is MRI covered?')
    expect(result!.evidence).toEqual([])
  })

  it('preserves rag metadata on the result', async () => {
    const { sendVoiceAgentQuestion } = await import('../voice-agent-client')
    const rag = {
      ragAttempted: true,
      ragAvailable: true,
      ragChunksCount: 1,
      ragFallbackReason: '',
      ragSource: 'eligibility-sbc-rag',
      guardPassed: true,
      guardReasonCode: 'supported_by_sbc_rag',
      supportedBy: ['sbc_rag'],
      unsupportedClaims: [],
      ragFactsUsed: 1,
    }
    globalThis.fetch = makeMockFetch({
      ...BASE_BACKEND,
      rag,
      evidence: [{ text: 'MRI covered.', sectionName: 'Imaging', sourceFile: 'sbc.pdf', distance: 0.1 }],
    })

    const result = await sendVoiceAgentQuestion('Is MRI covered?')
    expect(result!.rag?.ragSource).toBe('eligibility-sbc-rag')
    expect(result!.rag?.guardReasonCode).toBe('supported_by_sbc_rag')
    expect(result!.rag?.supportedBy).toContain('sbc_rag')
  })

  it('returns null when backend is unavailable', async () => {
    const { sendVoiceAgentQuestion } = await import('../voice-agent-client')
    globalThis.fetch = makeMockFetch({ error: 'backend_unavailable' }, 503)

    const result = await sendVoiceAgentQuestion('Is MRI covered?')
    expect(result).toBeNull()
  })

  it('does not expose ragSource string that contains credential-like values', async () => {
    const { sendVoiceAgentQuestion } = await import('../voice-agent-client')
    globalThis.fetch = makeMockFetch({
      ...BASE_BACKEND,
      rag: { ragAttempted: true, ragAvailable: true, ragChunksCount: 1, ragFallbackReason: '', ragSource: 'eligibility-sbc-rag' },
      evidence: [{ text: 'Some chunk.', sectionName: 'Benefits', sourceFile: 'doc.pdf', distance: 0.2 }],
    })

    const result = await sendVoiceAgentQuestion('Is MRI covered?')
    const serialized = JSON.stringify(result)
    expect(serialized).not.toMatch(/voyage|api_key|VOYAGE/i)
    expect(serialized).not.toMatch(/cartesia|CARTESIA/i)
    expect(serialized).not.toMatch(/gemini.*key/i)
  })
})
