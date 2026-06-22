/**
 * WS-2 Voice Agent API client.
 *
 * All calls go through Next.js proxy routes at /api/voice-agent/*.
 * The voice-agent service URL and any credentials stay server-side.
 */

import { apiFetch, demoResult } from './client'
import type { ApiResult } from './types'

// ── Request / response shapes ─────────────────────────────────────────────────

export interface AgentRespondRequest {
  question: string
  source?: 'typed' | 'voice' | 'demo'
}

export interface AgentEvidenceItem {
  text: string
  sectionName: string
  sourceFile: string
  distance: number
}

export interface AgentRagMeta {
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

export interface AgentRespondResult {
  question: string
  answer: string
  intent: string
  grounded: boolean
  guard_reason: string
  composer_mode: string
  tool_trace: Array<{ tool: string; args: Record<string, unknown>; result: string; ok: boolean }>
  backend_statuses: Array<{ label: string; detail: string; status: string }>
  rag?: AgentRagMeta
  evidence?: AgentEvidenceItem[]
}

export interface VoiceRuntimeStatusResult {
  runtime: string
  model: string
  voice: string
  note: string
  tts_provider?: string
  tts_voice_name?: string
}

// ── Demo fallback data ────────────────────────────────────────────────────────

const DEMO_RESPOND: AgentRespondResult = {
  question: '',
  answer: 'This is a demo answer. Connect the voice-agent backend to get real responses.',
  intent: 'demo',
  grounded: false,
  guard_reason: 'demo mode',
  composer_mode: 'demo',
  tool_trace: [],
  backend_statuses: [
    { label: 'Voice Agent API', detail: 'offline', status: 'offline' },
    { label: 'Claude answer',   detail: 'demo',    status: 'demo'    },
  ],
}

// ── Client functions ──────────────────────────────────────────────────────────

/**
 * Send a question to the voice-agent pipeline.
 * Returns a demo result if the backend is unreachable.
 */
export async function voiceAgentRespond(
  req: AgentRespondRequest,
  signal?: AbortSignal,
): Promise<ApiResult<AgentRespondResult>> {
  const result = await apiFetch<AgentRespondResult>('voice-agent', '/respond', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  })
  if (!result.ok && result.isUnavailable) {
    return demoResult('voice-agent', { ...DEMO_RESPOND, question: req.question })
  }
  return result
}

/**
 * Fetch the server-side voice runtime classification (safe metadata only).
 * Never throws — returns a fallback on any network error.
 */
export async function voiceAgentRuntimeStatus(): Promise<ApiResult<VoiceRuntimeStatusResult>> {
  return apiFetch<VoiceRuntimeStatusResult>('voice-agent', '/runtime', { timeoutMs: 4_000 })
}
