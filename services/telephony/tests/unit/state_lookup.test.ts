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

  it('recognizes several two-party-consent states', () => {
    // FL=305, IL=312, MA=617, PA=215, WA=425, CT=860
    for (const ac of ['305', '312', '617', '215', '425', '860']) {
      expect(requiresTwoPartyConsent(`+1${ac}5550100`)).toBe(true)
    }
  })

  it('treats clear one-party states as one-party', () => {
    // NY=212, TX=214, GA=404
    for (const ac of ['212', '214', '404']) {
      expect(requiresTwoPartyConsent(`+1${ac}5550100`)).toBe(false)
    }
  })
})
