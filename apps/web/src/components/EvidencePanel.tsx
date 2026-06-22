'use client'

import { useState } from 'react'
import { FileText, ChevronDown, ChevronUp } from 'lucide-react'
import type { EvidenceItem } from '@/lib/voice-agent-client'

// Max chars shown before "show more" expand
const TRUNCATE_AT = 160

interface EvidenceChunkProps {
  item: EvidenceItem
  index: number
}

function EvidenceChunk({ item, index }: EvidenceChunkProps) {
  const [expanded, setExpanded] = useState(false)
  const needsTruncation = item.text.length > TRUNCATE_AT
  const displayText = expanded || !needsTruncation
    ? item.text
    : item.text.slice(0, TRUNCATE_AT) + '…'

  return (
    <div className="rounded border border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 px-2.5 py-2">
      {/* Source header */}
      <div className="flex items-center gap-1.5 mb-1.5">
        <FileText size={10} className="text-slate-400 shrink-0" />
        <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 truncate flex-1">
          {item.sectionName || 'Plan Document'}
        </span>
        <span className="text-[9px] text-slate-400 dark:text-slate-500 shrink-0 truncate max-w-[80px]" title={item.sourceFile}>
          {item.sourceFile || '—'}
        </span>
        <span className="text-[9px] text-slate-300 dark:text-slate-600 shrink-0">
          #{index + 1}
        </span>
      </div>

      {/* Chunk text */}
      <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed">
        {displayText}
      </p>

      {/* Expand / collapse */}
      {needsTruncation && (
        <button
          onClick={() => setExpanded(e => !e)}
          className="mt-1 flex items-center gap-0.5 text-[10px] text-blue-500 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
          aria-expanded={expanded}
        >
          {expanded
            ? <><ChevronUp size={10} /> Show less</>
            : <><ChevronDown size={10} /> Show more</>}
        </button>
      )}
    </div>
  )
}

interface EvidencePanelProps {
  evidence: EvidenceItem[]
  ragSource?: string
}

/**
 * Compact citation panel shown below the answer when SBC RAG evidence is available.
 *
 * Component 70 — WS-2 SBC Evidence Citations.
 * Only renders when evidence[] is non-empty. Never creates fake citations.
 */
export default function EvidencePanel({ evidence, ragSource }: EvidencePanelProps) {
  if (evidence.length === 0) return null

  return (
    <div
      className="mt-2 rounded-lg border border-blue-100 dark:border-blue-900/40 bg-blue-50/50 dark:bg-blue-900/10 px-3 py-2.5"
      data-testid="evidence-panel"
    >
      {/* Panel header */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
          Plan Document Evidence
        </span>
        <span className="text-[9px] text-blue-400 dark:text-blue-600 shrink-0">
          {evidence.length} source{evidence.length !== 1 ? 's' : ''}{ragSource ? ` · ${ragSource}` : ''}
        </span>
      </div>

      {/* Evidence chunks */}
      <div className="flex flex-col gap-1.5">
        {evidence.map((item, i) => (
          <EvidenceChunk key={i} item={item} index={i} />
        ))}
      </div>
    </div>
  )
}
