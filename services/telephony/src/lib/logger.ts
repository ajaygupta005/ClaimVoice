import pino from 'pino'

export const logger = pino({
  base: { service: 'telephony' },
  redact: {
    paths: ['member_id', 'dob', 'name', 'phone', 'address'],
    censor: '[REDACTED]',
  },
  timestamp: pino.stdTimeFunctions.isoTime,
})
