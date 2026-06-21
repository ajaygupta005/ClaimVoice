/**
 * Unit tests for eligibilityGetMemberSummary / eligibilityGetPlanBenefits (Component 60).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { MemberSummaryResponse, BenefitsResponse } from '../api/eligibility'

function mockFetch(status: number, body: unknown, ok = status >= 200 && status < 300): void {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  }))
}

beforeEach(() => vi.unstubAllGlobals())
afterEach(() => vi.restoreAllMocks())

// ── Member summary ────────────────────────────────────────────────────────────

const REAL_SUMMARY: MemberSummaryResponse = {
  member: {
    memberId: 'CVX-0042-MT',
    name: 'Test Member',
    eligibilityStatus: 'active',
    deductibleYtdCents: 45000,
    oopYtdCents: 45000,
  },
  plan: {
    id: 'abc123-plan-id',
    name: 'Silver PPO 4500',
    issuer: 'BCBS',
    year: 2026,
    type: 'PPO',
    metalLevel: 'Silver',
    hsaEligible: false,
    state: 'MT',
  },
}

describe('eligibilityGetMemberSummary — success', () => {
  it('returns real data on 200', async () => {
    mockFetch(200, REAL_SUMMARY)

    const { eligibilityGetMemberSummary } = await import('../api/eligibility')
    const result = await eligibilityGetMemberSummary('CVX-0042-MT')

    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(false)
    if (result.ok) {
      expect(result.data.member.memberId).toBe('CVX-0042-MT')
      expect(result.data.plan.name).toBe('Silver PPO 4500')
    }
  })
})

describe('eligibilityGetMemberSummary — not found', () => {
  it('returns ok=false with statusCode 404', async () => {
    mockFetch(404, { detail: "Member 'X' not found" }, false)

    const { eligibilityGetMemberSummary } = await import('../api/eligibility')
    const result = await eligibilityGetMemberSummary('X')

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.statusCode).toBe(404)
      expect(result.isUnavailable).toBe(false)
    }
  })
})

describe('eligibilityGetMemberSummary — service unavailable', () => {
  it('returns demo fallback on 503', async () => {
    mockFetch(503, { error: 'down' }, false)

    const { eligibilityGetMemberSummary } = await import('../api/eligibility')
    const result = await eligibilityGetMemberSummary('CVX-0042-MT')

    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(true)
    if (result.ok) {
      expect(result.data.member.memberId).toBe('CVX-0042-MT')
      expect(result.data.plan.name).toContain('demo')
    }
  })

  it('returns demo fallback on network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('ECONNREFUSED')))

    const { eligibilityGetMemberSummary } = await import('../api/eligibility')
    const result = await eligibilityGetMemberSummary('CVX-0042-MT')

    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(true)
  })
})

// ── Plan benefits ─────────────────────────────────────────────────────────────

const REAL_BENEFITS: BenefitsResponse = {
  planId: 'abc123-plan-id',
  benefits: [
    {
      id: 'b1',
      benefitName: 'Primary Care Visit',
      serviceCategory: 'Office Visit',
      networkType: 'in_network',
      individualDeductibleCents: null,
      familyDeductibleCents: null,
      copayAmountCents: 3500,
      coinsurancePercentage: null,
      outOfPocketMaxCents: 790000,
      requiresPriorAuth: false,
    },
    {
      id: 'b2',
      benefitName: 'MRI',
      serviceCategory: 'Imaging',
      networkType: 'in_network',
      individualDeductibleCents: 450000,
      familyDeductibleCents: null,
      copayAmountCents: null,
      coinsurancePercentage: 20,
      outOfPocketMaxCents: null,
      requiresPriorAuth: true,
    },
  ],
}

describe('eligibilityGetPlanBenefits — success', () => {
  it('returns real data on 200', async () => {
    mockFetch(200, REAL_BENEFITS)

    const { eligibilityGetPlanBenefits } = await import('../api/eligibility')
    const result = await eligibilityGetPlanBenefits('abc123-plan-id')

    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(false)
    if (result.ok) {
      expect(result.data.benefits).toHaveLength(2)
      const pcp = result.data.benefits.find(b => b.benefitName === 'Primary Care Visit')
      expect(pcp?.copayAmountCents).toBe(3500)
      const mri = result.data.benefits.find(b => b.benefitName === 'MRI')
      expect(mri?.requiresPriorAuth).toBe(true)
    }
  })
})

describe('eligibilityGetPlanBenefits — service unavailable', () => {
  it('returns demo fallback on 503', async () => {
    mockFetch(503, { error: 'down' }, false)

    const { eligibilityGetPlanBenefits } = await import('../api/eligibility')
    const result = await eligibilityGetPlanBenefits('some-plan-id')

    expect(result.ok).toBe(true)
    expect(result.isDemo).toBe(true)
    if (result.ok) {
      expect(result.data.benefits.length).toBeGreaterThan(0)
    }
  })
})
