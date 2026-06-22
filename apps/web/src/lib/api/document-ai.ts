/**
 * WS-2 Document AI API client.
 *
 * Calls go through /api/document-ai/* (Next.js proxy → document-ai service :8001).
 *
 * The backend accepts base64-encoded images as JSON, not multipart form-data.
 * Image-to-base64 conversion happens in the browser before the call so the
 * proxy can forward a plain JSON body without any special streaming handling.
 *
 * No image bytes ever appear in UI state or logs — only extracted text fields.
 */

import { apiFetch, demoResult } from './client'
import type { ApiResult } from './types'

// ── Request / response shapes (match document-ai service API v1) ──────────────

export interface CardOcrRequest {
  image_base64: string  // base64 PNG/JPEG, no data-URI prefix
  card_id: string       // opaque identifier, echoed in response
}

export interface OcrField {
  field_name: string
  value: string
  confidence: number    // 0.0–1.0
  bbox: [number, number, number, number] | null
}

export interface CardOcrResult {
  card_id: string
  fields: OcrField[]
  low_confidence_fields: string[]  // field_names below 0.80 confidence
  model_version: string
}

export interface CardClassifyResult {
  payor_label: string   // Aetna | UHC | Cigna | BCBS | Humana | Kaiser | Anthem | Other
  confidence: number    // 0.0–1.0
  source_model: string
}

// ── Normalized UI shape ───────────────────────────────────────────────────────

export interface NormalizedCardFields {
  memberId: string
  memberName: string
  groupNumber: string
  planName: string
  payorName: string
  rxBin: string
  rxPcn: string
  fields: Array<{
    label: string
    value: string
    /** 0–100 integer for display */
    confidence: number
    status: 'confirmed' | 'review' | 'missing'
    source: string
  }>
  lowConfidenceFields: string[]
  modelVersion: string
}

export interface NormalizedPayorClassification {
  payorLabel: string
  /** 0–100 integer for display */
  confidence: number
  sourceModel: string
}

// ── Field name → display label map ───────────────────────────────────────────

const FIELD_LABELS: Record<string, string> = {
  member_id:      'Member ID',
  member_name:    'Member Name',
  group_number:   'Group Number',
  plan_name:      'Plan Name',
  payor_name:     'Carrier',
  rx_bin:         'RX BIN',
  rx_pcn:         'RX PCN',
  rx_group:       'RX Group',
  effective_date: 'Effective Date',
  copay_pcp:      'PCP Copay',
  copay_specialist: 'Specialist Copay',
  copay_er:       'ER Copay',
}

function fieldStatus(confidence: number, value: string): 'confirmed' | 'review' | 'missing' {
  if (!value) return 'missing'
  if (confidence >= 0.90) return 'confirmed'
  return 'review'
}

/** Convert a raw CardOcrResult into a shape the UI can render directly. */
export function normalizeOcrResult(raw: CardOcrResult): NormalizedCardFields {
  const byName: Record<string, OcrField> = {}
  for (const f of raw.fields) byName[f.field_name] = f

  const get = (key: string) => byName[key]?.value ?? ''
  const conf = (key: string) => byName[key]?.confidence ?? 0

  const fields = raw.fields.map(f => ({
    label:      FIELD_LABELS[f.field_name] ?? f.field_name,
    value:      f.value,
    confidence: Math.round(f.confidence * 100),
    status:     fieldStatus(f.confidence, f.value),
    source:     raw.model_version,
  }))

  return {
    memberId:           get('member_id'),
    memberName:         get('member_name'),
    groupNumber:        get('group_number'),
    planName:           get('plan_name'),
    payorName:          get('payor_name'),
    rxBin:              get('rx_bin'),
    rxPcn:              get('rx_pcn'),
    fields,
    lowConfidenceFields: raw.low_confidence_fields,
    modelVersion:        raw.model_version,
  }
}

/** Convert a raw CardClassifyResult into a display-ready shape. */
export function normalizeClassifyResult(raw: CardClassifyResult): NormalizedPayorClassification {
  return {
    payorLabel:  raw.payor_label,
    confidence:  Math.round(raw.confidence * 100),
    sourceModel: raw.source_model,
  }
}

// ── Demo fallback data ────────────────────────────────────────────────────────

const DEMO_OCR: CardOcrResult = {
  card_id: 'demo',
  fields: [
    { field_name: 'member_id',    value: 'DEMO-001',             confidence: 0.98, bbox: null },
    { field_name: 'member_name',  value: 'Demo Member',          confidence: 0.96, bbox: null },
    { field_name: 'group_number', value: 'GRP-DEMO',             confidence: 0.91, bbox: null },
    { field_name: 'plan_name',    value: 'Silver PPO 4500 (demo)', confidence: 0.94, bbox: null },
    { field_name: 'payor_name',   value: 'Demo Health Plan',     confidence: 0.88, bbox: null },
    { field_name: 'rx_bin',       value: '000000',               confidence: 0.82, bbox: null },
    { field_name: 'rx_pcn',       value: 'DEMO',                 confidence: 0.85, bbox: null },
  ],
  low_confidence_fields: ['rx_bin', 'payor_name'],
  model_version: 'demo',
}

const DEMO_CLASSIFY: CardClassifyResult = {
  payor_label: 'Other',
  confidence: 0,
  source_model: 'demo',
}

// ── Image helper ──────────────────────────────────────────────────────────────

/** Read a File/Blob as a base64 string (no data-URI prefix). */
export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      // Strip "data:image/jpeg;base64," prefix if present
      const comma = result.indexOf(',')
      resolve(comma >= 0 ? result.slice(comma + 1) : result)
    }
    reader.onerror = () => reject(new Error('FileReader failed'))
    reader.readAsDataURL(file)
  })
}

// ── Client functions ──────────────────────────────────────────────────────────

/**
 * Extract fields from an insurance card image.
 * Converts the File to base64 then posts JSON to the Document AI service.
 */
export async function documentAiOcrCard(
  imageFile: File,
  signal?: AbortSignal,
): Promise<ApiResult<CardOcrResult>> {
  let image_base64: string
  try {
    image_base64 = await fileToBase64(imageFile)
  } catch {
    return demoResult('document-ai', DEMO_OCR)
  }

  const card_id = `web-${Date.now()}`
  const result = await apiFetch<CardOcrResult>('document-ai', '/card_ocr', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_base64, card_id }),
    signal,
    timeoutMs: 30_000,  // OCR can be slow
  })
  if (!result.ok && result.isUnavailable) {
    return demoResult('document-ai', DEMO_OCR)
  }
  return result
}

/**
 * Classify the insurance payor from a card image.
 */
export async function documentAiClassifyCard(
  imageFile: File,
  signal?: AbortSignal,
): Promise<ApiResult<CardClassifyResult>> {
  let image_base64: string
  try {
    image_base64 = await fileToBase64(imageFile)
  } catch {
    return demoResult('document-ai', DEMO_CLASSIFY)
  }

  const result = await apiFetch<CardClassifyResult>('document-ai', '/payor_classify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_base64 }),
    signal,
    timeoutMs: 15_000,
  })
  if (!result.ok && result.isUnavailable) {
    return demoResult('document-ai', DEMO_CLASSIFY)
  }
  return result
}
