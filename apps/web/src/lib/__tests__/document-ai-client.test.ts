/**
 * Unit tests for Document AI client and normalization helpers (Component 59).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  normalizeOcrResult,
  normalizeClassifyResult,
  type CardOcrResult,
  type CardClassifyResult,
} from '../api/document-ai'

// ── normalizeOcrResult ────────────────────────────────────────────────────────

const SAMPLE_OCR: CardOcrResult = {
  card_id: 'test-001',
  fields: [
    { field_name: 'member_id',    value: 'TST-0001',       confidence: 0.98, bbox: null },
    { field_name: 'member_name',  value: 'Test Member',    confidence: 0.95, bbox: null },
    { field_name: 'group_number', value: 'GRP-1234',       confidence: 0.91, bbox: null },
    { field_name: 'plan_name',    value: 'Bronze HMO 3000', confidence: 0.94, bbox: null },
    { field_name: 'payor_name',   value: 'Aetna',          confidence: 0.87, bbox: null },
    { field_name: 'rx_bin',       value: '610011',         confidence: 0.75, bbox: null },
    { field_name: 'rx_pcn',       value: 'RXPCN',          confidence: 0.82, bbox: null },
    { field_name: 'effective_date', value: '',             confidence: 0.00, bbox: null },
  ],
  low_confidence_fields: ['rx_bin', 'payor_name'],
  model_version: 'layoutlmv3-v1.2',
}

describe('normalizeOcrResult', () => {
  it('converts field confidences from 0-1 to 0-100 integers', () => {
    const result = normalizeOcrResult(SAMPLE_OCR)
    const memberId = result.fields.find(f => f.label === 'Member ID')
    expect(memberId?.confidence).toBe(98)
  })

  it('marks fields above 90% as confirmed', () => {
    const result = normalizeOcrResult(SAMPLE_OCR)
    const memberId = result.fields.find(f => f.label === 'Member ID')
    expect(memberId?.status).toBe('confirmed')
  })

  it('marks fields between 80-90% as review', () => {
    const result = normalizeOcrResult(SAMPLE_OCR)
    const rxPcn = result.fields.find(f => f.label === 'RX PCN')
    expect(rxPcn?.status).toBe('review')
  })

  it('marks empty-value fields as missing regardless of confidence', () => {
    const result = normalizeOcrResult(SAMPLE_OCR)
    const effDate = result.fields.find(f => f.label === 'Effective Date')
    expect(effDate?.status).toBe('missing')
  })

  it('exposes top-level convenience fields', () => {
    const result = normalizeOcrResult(SAMPLE_OCR)
    expect(result.memberId).toBe('TST-0001')
    expect(result.memberName).toBe('Test Member')
    expect(result.groupNumber).toBe('GRP-1234')
    expect(result.planName).toBe('Bronze HMO 3000')
    expect(result.payorName).toBe('Aetna')
  })

  it('preserves low_confidence_fields list', () => {
    const result = normalizeOcrResult(SAMPLE_OCR)
    expect(result.lowConfidenceFields).toEqual(['rx_bin', 'payor_name'])
  })

  it('passes through model version', () => {
    const result = normalizeOcrResult(SAMPLE_OCR)
    expect(result.modelVersion).toBe('layoutlmv3-v1.2')
  })

  it('uses field_name as label when not in the label map', () => {
    const raw: CardOcrResult = {
      card_id: 'x',
      fields: [{ field_name: 'some_unknown_field', value: 'val', confidence: 0.9, bbox: null }],
      low_confidence_fields: [],
      model_version: 'v1',
    }
    const result = normalizeOcrResult(raw)
    expect(result.fields[0].label).toBe('some_unknown_field')
  })
})

// ── normalizeClassifyResult ───────────────────────────────────────────────────

describe('normalizeClassifyResult', () => {
  it('converts confidence from 0-1 to 0-100 integer', () => {
    const raw: CardClassifyResult = { payor_label: 'BCBS', confidence: 0.934, source_model: 'resnet50-v2' }
    const result = normalizeClassifyResult(raw)
    expect(result.confidence).toBe(93)
    expect(result.payorLabel).toBe('BCBS')
    expect(result.sourceModel).toBe('resnet50-v2')
  })

  it('passes through Other label when confidence is low', () => {
    const raw: CardClassifyResult = { payor_label: 'Other', confidence: 0.42, source_model: 'resnet50-v2' }
    const result = normalizeClassifyResult(raw)
    expect(result.payorLabel).toBe('Other')
    expect(result.confidence).toBe(42)
  })
})

// ── documentAiOcrCard — network responses ─────────────────────────────────────

function mockFetch(status: number, body: unknown, ok = status >= 200 && status < 300): void {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  }))
}

beforeEach(() => vi.unstubAllGlobals())
afterEach(() => vi.restoreAllMocks())

describe('documentAiOcrCard — network responses', () => {
  it('returns ok=true with real data on 200', async () => {
    mockFetch(200, SAMPLE_OCR)

    const { documentAiOcrCard } = await import('../api/document-ai')
    const fakeFile = new Blob(['fake-img'], { type: 'image/jpeg' }) as unknown as File

    // fileToBase64 uses FileReader which isn't available in Node — stub it
    vi.stubGlobal('FileReader', class {
      result = 'data:image/jpeg;base64,ZmFrZQ=='
      onload: (() => void) | null = null
      onerror: (() => void) | null = null
      readAsDataURL() { this.onload?.() }
    })

    const result = await documentAiOcrCard(fakeFile)
    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(false)
    if (result.ok) {
      expect(result.data.card_id).toBe('test-001')
    }
  })

  it('returns demo fallback on 503 (model not loaded)', async () => {
    mockFetch(503, { detail: 'Card OCR model is not loaded.' }, false)

    const { documentAiOcrCard } = await import('../api/document-ai')
    const fakeFile = new Blob(['fake'], { type: 'image/jpeg' }) as unknown as File

    vi.stubGlobal('FileReader', class {
      result = 'data:image/jpeg;base64,ZmFrZQ=='
      onload: (() => void) | null = null
      readAsDataURL() { this.onload?.() }
    })

    const result = await documentAiOcrCard(fakeFile)
    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(true)
    if (result.ok) {
      expect(result.data.card_id).toBe('demo')
    }
  })

  it('returns ok=false error on 422 (invalid image)', async () => {
    mockFetch(422, { detail: 'image_base64 is not valid base64' }, false)

    const { documentAiOcrCard } = await import('../api/document-ai')
    const fakeFile = new Blob(['bad'], { type: 'image/jpeg' }) as unknown as File

    vi.stubGlobal('FileReader', class {
      result = 'data:image/jpeg;base64,YmFk'
      onload: (() => void) | null = null
      readAsDataURL() { this.onload?.() }
    })

    const result = await documentAiOcrCard(fakeFile)
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.statusCode).toBe(422)
      expect(result.isUnavailable).toBe(false)
    }
  })

  it('returns demo fallback when FileReader fails', async () => {
    const { documentAiOcrCard } = await import('../api/document-ai')
    const fakeFile = new Blob(['fake'], { type: 'image/jpeg' }) as unknown as File

    vi.stubGlobal('FileReader', class {
      result = null
      onload: (() => void) | null = null
      onerror: (() => void) | null = null
      readAsDataURL() { this.onerror?.() }
    })

    const result = await documentAiOcrCard(fakeFile)
    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(true)
  })
})

// ── documentAiClassifyCard ────────────────────────────────────────────────────

describe('documentAiClassifyCard — network responses', () => {
  it('returns demo fallback on network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('ECONNREFUSED')))

    const { documentAiClassifyCard } = await import('../api/document-ai')
    const fakeFile = new Blob(['fake'], { type: 'image/jpeg' }) as unknown as File

    vi.stubGlobal('FileReader', class {
      result = 'data:image/jpeg;base64,ZmFrZQ=='
      onload: (() => void) | null = null
      readAsDataURL() { this.onload?.() }
    })

    const result = await documentAiClassifyCard(fakeFile)
    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(true)
    if (result.ok) {
      expect(result.data.payor_label).toBe('Other')
    }
  })
})
