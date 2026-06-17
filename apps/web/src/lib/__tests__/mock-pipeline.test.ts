import { describe, it, expect } from 'vitest'
import {
  routeIntent,
  mockHallucinationGuard,
  runMockPipeline,
  type ToolResult,
} from '../mock-pipeline'

// ── Intent routing ────────────────────────────────────────────────────────────

describe('routeIntent', () => {
  it('routes MRI question to check_coverage', () => {
    expect(routeIntent('Is an MRI of the brain covered?')).toBe('check_coverage')
  })

  it('routes prior auth question to check_coverage', () => {
    expect(routeIntent('Do I need prior authorization for an MRI?')).toBe('check_coverage')
  })

  it('routes urgent care copay to estimate_cost', () => {
    expect(routeIntent('What is my urgent care copay?')).toBe('estimate_cost')
  })

  it('routes deductible question to estimate_cost', () => {
    expect(routeIntent('How much of my deductible have I met?')).toBe('estimate_cost')
  })

  it('routes lisinopril to check_formulary', () => {
    expect(routeIntent('Is lisinopril on my formulary?')).toBe('check_formulary')
  })

  it('routes generic drug question to check_formulary', () => {
    expect(routeIntent('Is my medication covered by my prescription benefit?')).toBe('check_formulary')
  })

  it('routes cardiologist search to find_provider', () => {
    expect(routeIntent('Find a cardiologist near me who is in network')).toBe('find_provider')
  })

  it('routes doctor near me to find_provider', () => {
    expect(routeIntent('I need to find a doctor near me')).toBe('find_provider')
  })

  it('routes claim denied to escalate_to_human', () => {
    expect(routeIntent('My claim was denied — what do I do?')).toBe('escalate_to_human')
  })

  it('routes appeal to escalate_to_human', () => {
    expect(routeIntent('I want to appeal a coverage decision')).toBe('escalate_to_human')
  })

  it('routes unknown question to escalate_to_human', () => {
    expect(routeIntent('xyzzy purple elephant')).toBe('escalate_to_human')
  })
})

// ── Hallucination guard ───────────────────────────────────────────────────────

describe('mockHallucinationGuard', () => {
  it('passes when answer dollar amounts are in tool facts', () => {
    const tool: ToolResult = {
      tool: 'estimate_cost',
      facts: ['Urgent care copay: $75 in-network'],
      summary: 'Urgent care $75',
    }
    const result = mockHallucinationGuard('Your urgent care copay is $75 per visit.', tool)
    expect(result.passed).toBe(true)
  })

  it('fails when answer contains dollar amount not in facts', () => {
    const tool: ToolResult = {
      tool: 'check_coverage',
      facts: ['MRI covered', 'Prior auth required'],
      summary: 'MRI covered',
    }
    const result = mockHallucinationGuard('MRI costs $999 per scan.', tool)
    expect(result.passed).toBe(false)
  })

  it('always passes for escalation answers', () => {
    const tool: ToolResult = {
      tool: 'escalate_to_human',
      facts: ['Escalation required'],
      summary: 'Escalating',
    }
    const result = mockHallucinationGuard('I will transfer you to a human specialist.', tool)
    expect(result.passed).toBe(true)
  })
})

// ── Full pipeline scenarios ───────────────────────────────────────────────────

describe('runMockPipeline', () => {
  it('MRI question: uses check_coverage tool and guard passes', () => {
    const result = runMockPipeline('Is an MRI of the brain covered?')
    expect(result.intent).toBe('check_coverage')
    expect(result.toolResult.tool).toBe('check_coverage')
    expect(result.guard.passed).toBe(true)
    expect(result.answer).toBeTruthy()
    expect(result.tts.status).toBe('prepared')
  })

  it('urgent care copay: uses estimate_cost tool', () => {
    const result = runMockPipeline('What is my urgent care copay?')
    expect(result.intent).toBe('estimate_cost')
    expect(result.toolResult.tool).toBe('estimate_cost')
    expect(result.answer).toMatch(/\$75/)
  })

  it('lisinopril: uses check_formulary and mentions tier', () => {
    const result = runMockPipeline('Is lisinopril on my formulary?')
    expect(result.intent).toBe('check_formulary')
    expect(result.toolResult.tool).toBe('check_formulary')
    expect(result.answer.toLowerCase()).toMatch(/tier 1|formulary/)
  })

  it('cardiologist search: uses find_provider tool', () => {
    const result = runMockPipeline('Find a cardiologist near me who is in network')
    expect(result.intent).toBe('find_provider')
    expect(result.toolResult.tool).toBe('find_provider')
    expect(result.answer.toLowerCase()).toMatch(/cardiolog/)
  })

  it('claim denial: escalates to human', () => {
    const result = runMockPipeline('My claim was denied — can you help?')
    expect(result.intent).toBe('escalate_to_human')
    expect(result.toolResult.tool).toBe('escalate_to_human')
    expect(result.guard.passed).toBe(true)
  })

  it('twilio session metadata is present', () => {
    const result = runMockPipeline('Is therapy covered?')
    expect(result.twilio.provider).toBe('twilio')
    expect(result.twilio.status).toBe('mock')
    expect(result.twilio.callSid).toMatch(/^CA-demo-/)
    expect(result.twilio.streamSid).toMatch(/^MZ-demo-/)
  })

  it('each call gets unique SIDs', () => {
    const r1 = runMockPipeline('What is my copay?')
    const r2 = runMockPipeline('What is my copay?')
    expect(r1.twilio.callSid).not.toBe(r2.twilio.callSid)
  })

  it('backends array has five entries', () => {
    const result = runMockPipeline('Is telehealth covered?')
    expect(result.backends).toHaveLength(5)
  })
})
