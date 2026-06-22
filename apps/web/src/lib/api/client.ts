/**
 * Core fetch wrapper for WS-2 API clients.
 *
 * Wraps fetch so that:
 * - Network errors never propagate as unhandled exceptions.
 * - Non-2xx responses produce ApiError with the HTTP status code.
 * - AbortError is re-thrown so callers can detect user cancellation.
 * - API keys never appear in browser-side code (requests go through
 *   Next.js API proxy routes which hold the secrets server-side).
 */

import type { ApiResult, ApiError, ApiSuccess, ServiceName } from './types'

export const SERVICE_BASE_URLS: Record<ServiceName, string> = {
  'voice-agent':  '/api/voice-agent',
  'eligibility':  '/api/eligibility',
  'providers':    '/api/providers',
  'document-ai':  '/api/document-ai',
}

/** Default request timeout for all service calls (ms). */
export const DEFAULT_TIMEOUT_MS = 12_000

// ── Internal helpers ──────────────────────────────────────────────────────────

function makeError(
  service: ServiceName,
  code: string,
  message: string,
  statusCode = 0,
  isUnavailable = false,
): ApiError {
  return {
    ok: false,
    data: null,
    statusCode,
    source: isUnavailable ? 'unavailable' : 'real',
    service,
    isDemo: false,
    isUnavailable,
    error: message,
    code,
  }
}

function makeSuccess<T>(service: ServiceName, data: T, statusCode: number): ApiSuccess<T> {
  return {
    ok: true,
    data,
    statusCode,
    source: 'real',
    service,
    isDemo: false,
    isUnavailable: false,
  }
}

// ── Public fetch wrapper ───────────────────────────────────────────────────────

export async function apiFetch<T>(
  service: ServiceName,
  path: string,
  options?: RequestInit & { timeoutMs?: number },
): Promise<ApiResult<T>> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, signal: callerSignal, ...fetchOpts } = options ?? {}

  // Combine caller signal with our timeout signal
  const timeoutSignal = AbortSignal.timeout(timeoutMs)
  const signal =
    callerSignal
      ? AbortSignal.any([callerSignal, timeoutSignal])
      : timeoutSignal

  const base = SERVICE_BASE_URLS[service]
  const url = `${base}${path}`

  try {
    const res = await fetch(url, { ...fetchOpts, signal })

    if (!res.ok) {
      let detail = `HTTP ${res.status}`
      try {
        const body = await res.json() as { error?: string; detail?: string }
        detail = body.error ?? body.detail ?? detail
      } catch { /* response may not be JSON */ }
      return makeError(
        service,
        res.status === 503 ? 'service_unavailable' : 'upstream_error',
        detail,
        res.status,
        res.status === 503,
      )
    }

    const data = await res.json() as T
    return makeSuccess(service, data, res.status)
  } catch (err) {
    // Re-throw abort so callers can detect cancellation
    if (err instanceof Error && err.name === 'AbortError') throw err

    const isTimeout = err instanceof Error && err.name === 'TimeoutError'
    return makeError(
      service,
      isTimeout ? 'timeout' : 'network_error',
      err instanceof Error ? err.message : String(err),
      0,
      true,
    )
  }
}

// ── Demo result builder ────────────────────────────────────────────────────────

export function demoResult<T>(service: ServiceName, data: T): ApiResult<T> {
  return {
    ok: true,
    data,
    statusCode: 0,
    source: 'demo',
    service,
    isDemo: true,
    isUnavailable: false,
  }
}
