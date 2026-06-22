/**
 * Shared API result and service-status types for WS-2 dashboard pages.
 *
 * Every service client returns ApiResult<T> so UI components get a uniform
 * shape: typed data on success, a structured error on failure, and an explicit
 * flag for demo/mock data vs. real backend data.
 */

// ── API result ─────────────────────────────────────────────────────────────────

/** The named ClaimVoice backend service that produced this result. */
export type ServiceName =
  | 'voice-agent'
  | 'eligibility'
  | 'providers'
  | 'document-ai'

/** Where the data came from. */
export type DataSource = 'real' | 'demo' | 'unavailable'

export interface ApiSuccess<T> {
  ok: true
  data: T
  statusCode: number
  source: DataSource
  service: ServiceName
  isDemo: false
  isUnavailable: false
}

export interface ApiDemo<T> {
  ok: true
  data: T
  statusCode: 0
  source: 'demo'
  service: ServiceName
  isDemo: true
  isUnavailable: false
}

export interface ApiError {
  ok: false
  data: null
  statusCode: number
  source: DataSource
  service: ServiceName
  isDemo: false
  isUnavailable: boolean
  error: string
  /** Short machine-readable code, e.g. "network_error", "upstream_error" */
  code: string
}

export type ApiResult<T> = ApiSuccess<T> | ApiDemo<T> | ApiError

// ── Service status ─────────────────────────────────────────────────────────────

/** Live health of a single backend service. */
export interface ServiceStatus {
  service: ServiceName
  /** Human-readable display label, e.g. "Voice Agent" */
  displayLabel: string
  dataMode: DataSource
  /** ISO timestamp of the last status check (empty string if never checked) */
  checkedAt: string
  /** Optional diagnostic note shown in the connections panel */
  note?: string
}

/** All four services checked together. */
export interface AllServiceStatus {
  voiceAgent: ServiceStatus
  eligibility: ServiceStatus
  providers: ServiceStatus
  documentAi: ServiceStatus
}
