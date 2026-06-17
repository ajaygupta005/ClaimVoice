import { describe, it, expect } from 'vitest'
import { getStateFromPhone, requiresTwoPartyConsent } from '../../src/recording/state_lookup'

describe('state_lookup', () => {
  it('NYC numbers map to NY', () => {
    expect(getStateFromPhone('+12125551234')).toBe('NY')
    expect(getStateFromPhone('2125551234')).toBe('NY')
  })

  it('SF numbers map to CA', () => {
    expect(getStateFromPhone('+14155550100')).toBe('CA')
  })

  it('CA requires two-party consent', () => {
    expect(requiresTwoPartyConsent('+14155550100')).toBe(true)
  })

  it('NY does not require two-party consent', () => {
    expect(requiresTwoPartyConsent('+12125551234')).toBe(false)
  })

  it('unknown number defaults to safer (true)', () => {
    expect(requiresTwoPartyConsent('+19995551234')).toBe(true)
  })
})
