'use client'

export const CARD_REVIEW_SESSION_EVENT = 'claimvoice-card-session-changed'
const CARD_REVIEW_SESSION_KEY = 'claimvoice.cardReviewSession.v1'

export type CardReviewSession = {
  reviewedAt: string
  source: 'demo' | 'real'
  memberId?: string
  memberName?: string
  planName?: string
}

export function readCardReviewSession(): CardReviewSession | null {
  if (typeof window === 'undefined') return null
  // Old builds used localStorage, which made demo members appear active after
  // returning to a blank card screen. Clear that legacy state on every read.
  window.localStorage.removeItem(CARD_REVIEW_SESSION_KEY)

  const raw = window.sessionStorage.getItem(CARD_REVIEW_SESSION_KEY)
  if (!raw) return null

  try {
    const parsed = JSON.parse(raw) as CardReviewSession
    if (!parsed.reviewedAt || parsed.memberId === 'DEMO-001') {
      window.sessionStorage.removeItem(CARD_REVIEW_SESSION_KEY)
      return null
    }
    return parsed
  } catch {
    window.sessionStorage.removeItem(CARD_REVIEW_SESSION_KEY)
    return null
  }
}

export function hasCardReviewSession(): boolean {
  return readCardReviewSession() !== null
}

export function markCardReviewed(session: Omit<CardReviewSession, 'reviewedAt'>) {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(CARD_REVIEW_SESSION_KEY)
  window.sessionStorage.setItem(
    CARD_REVIEW_SESSION_KEY,
    JSON.stringify({ ...session, reviewedAt: new Date().toISOString() }),
  )
  window.dispatchEvent(new Event(CARD_REVIEW_SESSION_EVENT))
}

export function clearCardReviewSession() {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(CARD_REVIEW_SESSION_KEY)
  window.sessionStorage.removeItem(CARD_REVIEW_SESSION_KEY)
  window.dispatchEvent(new Event(CARD_REVIEW_SESSION_EVENT))
}
