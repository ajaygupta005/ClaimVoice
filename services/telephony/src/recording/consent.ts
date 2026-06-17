import { requiresTwoPartyConsent } from './state_lookup.js'

// Returns TwiML <Say> snippet for caller's consent, or empty string if
// one-party-consent state.
export function consentTwiml(callerPhone: string): string {
  if (!requiresTwoPartyConsent(callerPhone)) return ''
  return '<Say voice="alice">This call may be recorded for quality and training purposes.</Say>'
}
