// Component 12 - missing required env vars cause fast failure at boot.

import { describe, it, expect } from 'vitest'
// import { loadConfig } from '../../src/lib/config'

describe('config validation', () => {
  it.skip('throws when required env var is missing', () => {
    delete process.env.TWILIO_ACCOUNT_SID
    // expect(() => loadConfig()).toThrow(/TWILIO_ACCOUNT_SID/)
  })
})
