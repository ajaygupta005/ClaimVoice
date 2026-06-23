/**
 * Frontend client adapter for the voice-agent backend (Component 36).
 *
 * Calls /api/voice-agent/respond (Next.js proxy → voice-agent service).
 * Normalises the backend response into UI state shapes:
 *   - BackendStatus[] for the LED rail
 *   - PipeStep details for the pipeline display
 *
 * Falls back to null on any network/parse error so the caller can
 * decide to use the local mock pipeline instead.
 */

import type { BackendStatus, LedStatus } from '@/lib/mock-pipeline'

// ── Backend response types (mirrors voice-agent schemas) ─────────────────────

export interface AgentToolTrace {
  tool: string
  args: Record<string, unknown>
  result: string
  ok: boolean
}

export interface AgentBackendStatus {
  label: string
  detail: string
  status: string
}

/** Normalised SBC evidence item for UI rendering (Component 70). */
export interface EvidenceItem {
  text: string
  sectionName: string
  sourceFile: string
  distance: number
}

/** RAG + guard metadata from WS-7 (Component 68/69/70). */
export interface RagMeta {
  ragAttempted: boolean
  ragAvailable: boolean
  ragChunksCount: number
  ragFallbackReason: string
  ragSource: string
  guardPassed: boolean
  guardReasonCode: string
  supportedBy: string[]
  unsupportedClaims: string[]
  ragFactsUsed: number
}

export interface AgentRespondResponse {
  question: string
  answer: string
  intent: string
  grounded: boolean
  guard_reason: string
  tool_trace: AgentToolTrace[]
  composer_mode: string
  backend_statuses: AgentBackendStatus[]
  rag?: RagMeta
}

// ── Normalised UI result ──────────────────────────────────────────────────────

export interface BackendPipelineResult {
  answer: string
  intent: string
  grounded: boolean
  guard_reason: string
  tool: string
  tool_result: string
  composer_mode: string
  backends: BackendStatus[]
  /** Per-step details for the pipeline row */
  pipeDetails: {
    identify: string
    understand: string
    check: string
    guard: string
    respond: string
  }
  /** SBC evidence items for citation panel (Component 70). Empty when RAG was not used. */
  evidence: EvidenceItem[]
  rag?: RagMeta
}

// ── LED status mapping ────────────────────────────────────────────────────────

function toLedStatus(raw: string): LedStatus {
  if (raw === 'connected') return 'connected'
  if (raw === 'degraded')  return 'degraded'
  if (raw === 'offline')   return 'offline'
  return 'demo'
}

function normalisedBackends(raw: AgentBackendStatus[]): BackendStatus[] {
  return raw.map(b => ({
    label:  b.label,
    detail: b.detail,
    status: toLedStatus(b.status),
  }))
}

// ── Pipeline step detail builder ──────────────────────────────────────────────

function pipeDetails(res: AgentRespondResponse) {
  const toolName = res.tool_trace[0]?.tool ?? '—'
  const toolResult = res.tool_trace[0]?.result ?? '—'
  const guardOk = res.grounded

  return {
    identify:   'Member verified',
    understand: `Intent: ${res.intent}`,
    check:      `${toolName} · ${toolResult.slice(0, 40)}${toolResult.length > 40 ? '…' : ''}`,
    guard:      guardOk ? 'All grounded ✓' : `Flagged — ${res.guard_reason.slice(0, 40)}`,
    respond:    res.composer_mode === 'claude' ? 'Claude answer' : 'Mock answer',
  }
}

// ── Runtime status ────────────────────────────────────────────────────────────

export type VoiceRuntimeKind =
  | 'browser'
  | 'gemini-live-configured'
  | 'gemini-live-unavailable'
  | 'fallback'

export type RagStatusKind =
  | 'ready'
  | 'key_missing'
  | 'table_missing'
  | 'empty'
  | 'no_plan_links'
  | 'db_error'
  | 'unreachable'

export interface VoiceRuntimeStatus {
  runtime: VoiceRuntimeKind
  model: string
  voice: string
  note: string
  tts_provider?: string    // "cartesia", "google", "system", "browser"
  tts_voice_name?: string  // display name, e.g. "Skylar"
  // RAG readiness fields (Component 71)
  rag_status?: RagStatusKind
  rag_reason?: string
  rag_chunks_count?: number
  voyage_configured?: boolean
  pgvector_available?: boolean
}

/**
 * Fetch the server-side voice runtime classification.
 * Returns a safe fallback on any network error — never throws.
 */
export async function fetchRuntimeStatus(): Promise<VoiceRuntimeStatus> {
  try {
    const res = await fetch('/api/voice-agent/runtime', {
      // Longer than the proxy's own upstream timeout so we don't abort a
      // near-complete call while the backend is warming up (cold-start RAG count).
      signal: AbortSignal.timeout(12_000),
    })
    if (!res.ok) throw new Error(`status ${res.status}`)
    return await res.json() as VoiceRuntimeStatus
  } catch {
    return { runtime: 'fallback', model: '', voice: '', note: 'Backend unavailable.' }
  }
}

// ── Evidence extraction ───────────────────────────────────────────────────────

/** Extract display-safe evidence items from the backend response (Component 70).
 *  Returns [] when RAG was not used or produced no chunks — never creates fake citations.
 */
function extractEvidence(data: AgentRespondResponse): EvidenceItem[] {
  if (!data.rag?.ragAvailable || !data.rag.ragChunksCount) return []
  const rawEvidence = (data as unknown as Record<string, unknown>)['evidence']
  if (!Array.isArray(rawEvidence) || rawEvidence.length === 0) return []
  return rawEvidence.map((item: unknown) => {
    const e = item as Record<string, unknown>
    return {
      text:        typeof e['text'] === 'string' ? e['text'] : '',
      sectionName: typeof e['sectionName'] === 'string' ? e['sectionName'] : '',
      sourceFile:  typeof e['sourceFile'] === 'string' ? e['sourceFile'] : '',
      distance:    typeof e['distance'] === 'number' ? e['distance'] : 1.0,
    }
  }).filter(e => e.text.length > 0)
}

// ── Public entry point ────────────────────────────────────────────────────────

/**
 * Send a question to the voice-agent backend pipeline.
 * Returns null if the backend is unavailable — caller falls back to mock.
 */
export async function sendVoiceAgentQuestion(
  question: string,
  source: 'typed' | 'voice' | 'demo' = 'typed',
  signal?: AbortSignal,
): Promise<BackendPipelineResult | null> {
  try {
    const res = await fetch('/api/voice-agent/respond', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, source }),
      signal: signal ?? AbortSignal.timeout(35_000),
    })

    if (!res.ok) {
      console.warn('[voice-agent-client] upstream error', res.status)
      return null
    }

    const data = await res.json() as AgentRespondResponse

    if (!data.answer) return null

    return {
      answer:        data.answer,
      intent:        data.intent,
      grounded:      data.grounded,
      guard_reason:  data.guard_reason,
      tool:          data.tool_trace[0]?.tool ?? '—',
      tool_result:   data.tool_trace[0]?.result ?? '—',
      composer_mode: data.composer_mode,
      backends:      normalisedBackends(data.backend_statuses),
      pipeDetails:   pipeDetails(data),
      evidence:      extractEvidence(data),
      rag:           data.rag,
    }
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') throw err
    console.warn('[voice-agent-client] fetch failed:', err)
    return null
  }
}
