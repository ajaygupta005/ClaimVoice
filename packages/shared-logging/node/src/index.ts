import pino from 'pino'

export const PII_FIELDS = ['member_id', 'dob', 'name', 'phone', 'address', 'ssn', 'email']

export function createLogger(service: string) {
  return pino({
    base: { service },
    redact: {
      paths: PII_FIELDS,
      censor: '[REDACTED]',
    },
    timestamp: pino.stdTimeFunctions.isoTime,
    formatters: {
      level(label) {
        return { level: label.toUpperCase() }
      },
    },
  })
}

export type Logger = ReturnType<typeof createLogger>
