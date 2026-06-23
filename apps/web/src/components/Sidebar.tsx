'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { CreditCard, FileText, MapPin, Mic, Phone, BookOpen, Lock } from 'lucide-react'
import DarkModeToggle from './DarkModeToggle'
import { mockMember } from '@/lib/mock-data'
import { useTutorialStore } from '@/lib/tutorial-store'
import {
  CARD_REVIEW_SESSION_EVENT,
  readCardReviewSession,
  type CardReviewSession,
} from '@/lib/demo-session'

const NAV_ITEMS: { href: string; label: string; Icon: React.ComponentType<{ size?: number; strokeWidth?: number }> }[] = [
  { href: '/dashboard/card',      label: 'Card',      Icon: CreditCard },
  { href: '/dashboard/plan',      label: 'Plan',      Icon: FileText },
  { href: '/dashboard/providers', label: 'Providers', Icon: MapPin },
  { href: '/dashboard/voice',     label: 'Voice',     Icon: Mic },
  { href: '/dashboard/calls',     label: 'Calls',     Icon: Phone },
]

export default function Sidebar() {
  const pathname = usePathname()
  const openTutorial = useTutorialStore(s => s.openTutorial)
  const [cardSession, setCardSession] = useState<CardReviewSession | null>(null)

  useEffect(() => {
    const sync = () => setCardSession(readCardReviewSession())
    sync()
    window.addEventListener(CARD_REVIEW_SESSION_EVENT, sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener(CARD_REVIEW_SESSION_EVENT, sync)
      window.removeEventListener('storage', sync)
    }
  }, [])

  const cardReady = cardSession !== null

  return (
    <aside className="flex flex-col w-60 min-h-screen bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-700">
      {/* Brand */}
      <div className="px-5 pt-6 pb-4 border-b border-slate-200 dark:border-slate-700">
        <p className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">ClaimVoice</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Realtime member support</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV_ITEMS.map(({ href, label, Icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          const locked = !cardReady && href !== '/dashboard/card'
          const target = locked ? '/dashboard/card' : href
          return (
            <Link
              key={href}
              href={target as never}
              title={locked ? 'Upload or review a card first' : undefined}
              className={[
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                active
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300'
                  : locked
                  ? 'text-slate-400 dark:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800'
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800',
              ].join(' ')}
            >
              <Icon size={16} strokeWidth={active ? 2.5 : 2} />
              {label}
              {locked && <Lock size={12} className="ml-auto opacity-60" />}
            </Link>
          )
        })}
      </nav>

      {/* Member context card */}
      <div className="mx-3 mb-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
        {cardReady ? (
          <>
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
                {cardSession?.memberName || mockMember.name}
              </p>
              <span className="shrink-0 ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">
                {mockMember.status}
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
              {cardSession?.planName || mockMember.plan}
            </p>
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
              {cardSession?.memberId || mockMember.memberId}
            </p>
          </>
        ) : (
          <>
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
              No card loaded
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Start with card extraction
            </p>
          </>
        )}
      </div>

      {/* Bottom actions */}
      <div className="px-3 pb-4 flex items-center justify-between">
        <button
          onClick={openTutorial}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <BookOpen size={13} />
          Tutorial
        </button>
        <DarkModeToggle />
      </div>
    </aside>
  )
}
