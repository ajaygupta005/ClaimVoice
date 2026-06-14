'use client'

import { useState } from 'react'
import { X, CreditCard, CheckSquare, FileText, MapPin, Mic, Phone, ArrowLeft, ArrowRight } from 'lucide-react'
import { useTutorialStore } from '@/lib/tutorial-store'

interface Step {
  icon: React.ReactNode
  title: string
  description: string
  tip: string
}

const STEPS: Step[] = [
  {
    icon: <CreditCard size={28} className="text-blue-500" />,
    title: 'Upload your insurance card',
    description: 'Go to the Card tab and take a photo or upload a scan of your insurance card. ClaimVoice will read it for you.',
    tip: 'Both sides of the card are helpful, but the front side is usually enough.',
  },
  {
    icon: <CheckSquare size={28} className="text-blue-500" />,
    title: 'Check the extracted details',
    description: 'After uploading, ClaimVoice shows you the information it read from the card. Review each field and correct any mistakes.',
    tip: 'Fields shown in yellow may need a quick review — the AI flagged them as low confidence.',
  },
  {
    icon: <FileText size={28} className="text-blue-500" />,
    title: 'Review your plan',
    description: 'The Plan tab shows your deductible, out-of-pocket maximum, copays, and what your insurance covers. It is a plain-English summary of your benefits.',
    tip: 'Tap any coverage row to see more details about that benefit.',
  },
  {
    icon: <MapPin size={28} className="text-blue-500" />,
    title: 'Find in-network providers',
    description: 'The Providers tab helps you search for doctors, specialists, and clinics that are covered by your plan. Seeing an in-network provider usually costs much less.',
    tip: 'Filter by specialty to narrow down the list quickly.',
  },
  {
    icon: <Mic size={28} className="text-blue-500" />,
    title: 'Ask a question using voice',
    description: 'The Voice tab lets you speak or type any insurance question. The AI assistant answers in plain language and checks every answer for accuracy before it is read back to you.',
    tip: 'Try asking "Is my annual physical covered?" or "What is my urgent care copay?"',
  },
  {
    icon: <Phone size={28} className="text-blue-500" />,
    title: 'Review previous calls',
    description: 'The Calls tab keeps a history of past voice sessions. You can read the transcript, see how long the call lasted, and check whether the recording was saved with your consent.',
    tip: 'Calls that were escalated to a human agent are marked "Transferred".',
  },
]

export default function TutorialModal() {
  const { open, closeTutorial } = useTutorialStore()
  const [step, setStep] = useState(0)

  if (!open) return null

  const current = STEPS[step]
  const isFirst = step === 0
  const isLast  = step === STEPS.length - 1

  function handleClose() {
    closeTutorial()
    setStep(0)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      onClick={e => { if (e.target === e.currentTarget) handleClose() }}
    >
      <div className="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
          <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">
            How ClaimVoice works
          </p>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X size={16} className="text-slate-500 dark:text-slate-400" />
          </button>
        </div>

        {/* Progress dots */}
        <div className="flex items-center justify-center gap-1.5 pt-5">
          {STEPS.map((_, i) => (
            <button
              key={i}
              onClick={() => setStep(i)}
              className={`rounded-full transition-all ${
                i === step
                  ? 'w-5 h-2 bg-blue-500'
                  : 'w-2 h-2 bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600'
              }`}
            />
          ))}
        </div>

        {/* Content */}
        <div className="px-8 py-6 min-h-[260px] flex flex-col items-center text-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 dark:bg-blue-950/30 flex items-center justify-center">
            {current.icon}
          </div>
          <div className="space-y-2">
            <p className="text-xs font-semibold text-blue-500 uppercase tracking-widest">
              Step {step + 1} of {STEPS.length}
            </p>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              {current.title}
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              {current.description}
            </p>
          </div>
          <div className="w-full mt-auto px-4 py-3 rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-800/40 text-left">
            <p className="text-xs font-semibold text-amber-700 dark:text-amber-400 mb-0.5">Tip</p>
            <p className="text-xs text-amber-600 dark:text-amber-500 leading-relaxed">{current.tip}</p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 dark:border-slate-800">
          <button
            onClick={() => setStep(s => s - 1)}
            disabled={isFirst}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ArrowLeft size={14} /> Back
          </button>

          {isLast ? (
            <button
              onClick={handleClose}
              className="px-5 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-sm font-medium text-white transition-colors"
            >
              Get started
            </button>
          ) : (
            <button
              onClick={() => setStep(s => s + 1)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-sm font-medium text-white transition-colors"
            >
              Next <ArrowRight size={14} />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
