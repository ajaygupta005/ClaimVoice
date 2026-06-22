/**
 * Service health-check helpers for WS-2 dashboard.
 *
 * Probes each service's health endpoint through the Next.js proxy and
 * normalises the result into ServiceStatus so UI components can render
 * a consistent badge without knowing per-service response shapes.
 *
 * Health checks are best-effort and silent on failure — a failing health
 * check sets dataMode to "unavailable", never throws.
 */

import type { ServiceStatus, AllServiceStatus } from './types'

// ── Health probe ──────────────────────────────────────────────────────────────

const HEALTH_PATHS: Record<string, string> = {
  'voice-agent': '/api/voice-agent/runtime',
  'eligibility': '/api/eligibility/health',
  'providers':   '/api/providers/health',
  'document-ai': '/api/document-ai/health',
}

const DISPLAY_LABELS: Record<string, string> = {
  'voice-agent': 'Voice Agent',
  'eligibility': 'Eligibility',
  'providers':   'Providers',
  'document-ai': 'Document AI',
}

async function probeService(serviceKey: keyof typeof HEALTH_PATHS): Promise<ServiceStatus> {
  const checkedAt = new Date().toISOString()
  const service = serviceKey as ServiceStatus['service']
  const displayLabel = DISPLAY_LABELS[serviceKey]

  try {
    const res = await fetch(HEALTH_PATHS[serviceKey], {
      signal: AbortSignal.timeout(4_000),
    })

    if (res.ok) {
      return { service, displayLabel, dataMode: 'real', checkedAt }
    }

    if (res.status === 503) {
      return {
        service, displayLabel, dataMode: 'unavailable', checkedAt,
        note: `Service returned ${res.status}`,
      }
    }

    // Any other non-OK status (404 on health path, etc.) — treat as unavailable
    return {
      service, displayLabel, dataMode: 'unavailable', checkedAt,
      note: `HTTP ${res.status}`,
    }
  } catch {
    return {
      service, displayLabel, dataMode: 'unavailable', checkedAt,
      note: 'Unreachable',
    }
  }
}

// ── Public API ────────────────────────────────────────────────────────────────

/** Check all four services in parallel. Never throws. */
export async function checkAllServices(): Promise<AllServiceStatus> {
  const [voiceAgent, eligibility, providers, documentAi] = await Promise.all([
    probeService('voice-agent'),
    probeService('eligibility'),
    probeService('providers'),
    probeService('document-ai'),
  ])
  return { voiceAgent, eligibility, providers, documentAi }
}

/** Check a single service. Never throws. */
export async function checkService(
  serviceKey: 'voice-agent' | 'eligibility' | 'providers' | 'document-ai',
): Promise<ServiceStatus> {
  return probeService(serviceKey)
}

/**
 * Map a ServiceStatus to an LED status string compatible with the existing
 * BackendStatus / LedStatus type in mock-pipeline.ts.
 */
export function toLedStatus(s: ServiceStatus): 'connected' | 'demo' | 'degraded' | 'offline' {
  if (s.dataMode === 'real') return 'connected'
  if (s.dataMode === 'demo') return 'demo'
  return 'offline'
}
