/**
 * WS-2 Eligibility API client.
 *
 * Calls go through /api/eligibility/* (Next.js proxy → eligibility service :8002).
 * The service URL never appears in browser-side code.
 */

import { apiFetch, demoResult } from './client'
import type { ApiResult } from './types'

// ── Member summary / plan benefits shapes ────────────────────────────────────

export interface MemberOut {
  memberId: string
  name: string
  eligibilityStatus: string
  deductibleYtdCents: number
  oopYtdCents: number
}

export interface PlanOut {
  id: string
  name: string
  issuer: string | null
  year: number | null
  type: string | null
  metalLevel: string | null
  hsaEligible: boolean | null
  state: string | null
}

export interface MemberSummaryResponse {
  member: MemberOut
  plan: PlanOut
}

export interface BenefitOut {
  id: string
  benefitName: string | null
  serviceCategory: string | null
  networkType: string | null
  individualDeductibleCents: number | null
  familyDeductibleCents: number | null
  copayAmountCents: number | null
  coinsurancePercentage: number | null
  outOfPocketMaxCents: number | null
  requiresPriorAuth: boolean
}

export interface BenefitsResponse {
  planId: string
  benefits: BenefitOut[]
}

// ── Request / response shapes ─────────────────────────────────────────────────

export interface CoverageCheckRequest {
  service: string
  condition?: string
  member_id?: string
}

export interface CoverageCheckResult {
  covered: boolean
  benefit_name: string
  cost_share: string
  notes: string
  source: string
}

export interface CostEstimateRequest {
  service: string
  in_network?: boolean
  member_id?: string
}

export interface CostEstimateResult {
  service: string
  in_network_cost_cents: number
  out_of_network_cost_cents: number
  deductible_remaining_cents: number
  out_of_pocket_remaining_cents: number
  notes: string
}

export interface FormularyLookupRequest {
  drug: string
  member_id?: string
}

export interface FormularyLookupResult {
  covered: boolean
  drug_name: string
  tier: number
  copay_cents: number
  prior_auth_required: boolean
  notes: string
}

// ── Demo fallback data ────────────────────────────────────────────────────────

const DEMO_COVERAGE: CoverageCheckResult = {
  covered: true,
  benefit_name: 'Outpatient Services (demo)',
  cost_share: '$30 copay (demo)',
  notes: 'Demo data — connect the eligibility service for real plan details.',
  source: 'demo',
}

const DEMO_COST: CostEstimateResult = {
  service: 'demo',
  in_network_cost_cents: 3000,
  out_of_network_cost_cents: 10000,
  deductible_remaining_cents: 150000,
  out_of_pocket_remaining_cents: 450000,
  notes: 'Demo data — connect the eligibility service for real cost estimates.',
}

const DEMO_FORMULARY: FormularyLookupResult = {
  covered: true,
  drug_name: 'demo drug',
  tier: 2,
  copay_cents: 1500,
  prior_auth_required: false,
  notes: 'Demo data — connect the eligibility service for real formulary data.',
}

// ── Client functions ──────────────────────────────────────────────────────────

export async function eligibilityCheckCoverage(
  req: CoverageCheckRequest,
  signal?: AbortSignal,
): Promise<ApiResult<CoverageCheckResult>> {
  const result = await apiFetch<CoverageCheckResult>('eligibility', '/coverage', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  })
  if (!result.ok && result.isUnavailable) {
    return demoResult('eligibility', DEMO_COVERAGE)
  }
  return result
}

export async function eligibilityEstimateCost(
  req: CostEstimateRequest,
  signal?: AbortSignal,
): Promise<ApiResult<CostEstimateResult>> {
  const result = await apiFetch<CostEstimateResult>('eligibility', '/cost/estimate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  })
  if (!result.ok && result.isUnavailable) {
    return demoResult('eligibility', DEMO_COST)
  }
  return result
}

export async function eligibilityLookupFormulary(
  req: FormularyLookupRequest,
  signal?: AbortSignal,
): Promise<ApiResult<FormularyLookupResult>> {
  const result = await apiFetch<FormularyLookupResult>('eligibility', '/formulary/lookup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  })
  if (!result.ok && result.isUnavailable) {
    return demoResult('eligibility', DEMO_FORMULARY)
  }
  return result
}

// ── Demo fallback for member summary / plan benefits ─────────────────────────

const DEMO_MEMBER_SUMMARY: MemberSummaryResponse = {
  member: {
    memberId: 'CVX-0042-MT',
    name: 'Demo Member',
    eligibilityStatus: 'active',
    deductibleYtdCents: 45000,
    oopYtdCents: 45000,
  },
  plan: {
    id: '00000000-0000-0000-0000-000000000000',
    name: 'Silver PPO 4500 (demo)',
    issuer: 'Demo Health Plan',
    year: 2026,
    type: 'PPO',
    metalLevel: 'Silver',
    hsaEligible: false,
    state: null,
  },
}

const DEMO_BENEFITS: BenefitsResponse = {
  planId: '00000000-0000-0000-0000-000000000000',
  benefits: [
    {
      id: '00000000-0000-0000-0000-000000000001',
      benefitName: 'Primary Care Visit',
      serviceCategory: 'Office Visit',
      networkType: 'in_network',
      individualDeductibleCents: null,
      familyDeductibleCents: null,
      copayAmountCents: 3500,
      coinsurancePercentage: null,
      outOfPocketMaxCents: null,
      requiresPriorAuth: false,
    },
    {
      id: '00000000-0000-0000-0000-000000000002',
      benefitName: 'Specialist Visit',
      serviceCategory: 'Office Visit',
      networkType: 'in_network',
      individualDeductibleCents: null,
      familyDeductibleCents: null,
      copayAmountCents: 7000,
      coinsurancePercentage: null,
      outOfPocketMaxCents: null,
      requiresPriorAuth: false,
    },
    {
      id: '00000000-0000-0000-0000-000000000003',
      benefitName: 'MRI / Advanced Imaging',
      serviceCategory: 'Imaging',
      networkType: 'in_network',
      individualDeductibleCents: 450000,
      familyDeductibleCents: null,
      copayAmountCents: null,
      coinsurancePercentage: 20,
      outOfPocketMaxCents: null,
      requiresPriorAuth: true,
    },
    {
      id: '00000000-0000-0000-0000-000000000004',
      benefitName: 'Emergency Room',
      serviceCategory: 'Emergency',
      networkType: 'in_network',
      individualDeductibleCents: null,
      familyDeductibleCents: null,
      copayAmountCents: 25000,
      coinsurancePercentage: null,
      outOfPocketMaxCents: null,
      requiresPriorAuth: false,
    },
  ],
}

// ── Member summary / plan benefits client functions ───────────────────────────

export async function eligibilityGetMemberSummary(
  memberId: string,
  signal?: AbortSignal,
): Promise<ApiResult<MemberSummaryResponse>> {
  const result = await apiFetch<MemberSummaryResponse>(
    'eligibility',
    `/members/${encodeURIComponent(memberId)}/summary`,
    { signal },
  )
  if (!result.ok && result.isUnavailable) {
    return demoResult('eligibility', DEMO_MEMBER_SUMMARY)
  }
  return result
}

export async function eligibilityGetPlanBenefits(
  planId: string,
  signal?: AbortSignal,
): Promise<ApiResult<BenefitsResponse>> {
  const result = await apiFetch<BenefitsResponse>(
    'eligibility',
    `/plans/${encodeURIComponent(planId)}/benefits`,
    { signal },
  )
  if (!result.ok && result.isUnavailable) {
    return demoResult('eligibility', DEMO_BENEFITS)
  }
  return result
}
