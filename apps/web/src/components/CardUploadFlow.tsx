'use client'

import { useCallback, useRef, useState } from 'react'
import { Upload, FileImage, RotateCcw, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'
import { mockExtractedFields, type ExtractedField } from '@/lib/mock-data'

type Stage = 'ready' | 'uploading' | 'extracting' | 'review_ready'

const CONFIDENCE_THRESHOLD = 90

const STAGE_LABELS: Record<Stage, string> = {
  ready:        'Ready',
  uploading:    'Uploading…',
  extracting:   'Extracting fields…',
  review_ready: 'Extraction complete',
}

const STAGE_PROGRESS: Record<Stage, number> = {
  ready:        0,
  uploading:    35,
  extracting:   75,
  review_ready: 100,
}

function confidenceColour(c: number) {
  if (c === 0)   return 'text-slate-400 dark:text-slate-500'
  if (c < 85)    return 'text-amber-600 dark:text-amber-400'
  if (c < 90)    return 'text-amber-500 dark:text-amber-300'
  return 'text-green-600 dark:text-green-400'
}

function StatusBadge({ status }: { status: ExtractedField['status'] }) {
  if (status === 'confirmed') return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300">
      <CheckCircle size={10} /> Confirmed
    </span>
  )
  if (status === 'review') return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
      <AlertTriangle size={10} /> Review
    </span>
  )
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
      <XCircle size={10} /> Missing
    </span>
  )
}

function FieldRow({ field }: { field: ExtractedField }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-100 dark:border-slate-800 last:border-0">
      <div className="min-w-0">
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">{field.label}</p>
        <p className={`text-sm font-semibold mt-0.5 ${field.status === 'missing' ? 'text-slate-400 dark:text-slate-600 italic' : 'text-slate-900 dark:text-slate-100'}`}>
          {field.status === 'missing' ? 'Not detected' : field.value}
        </p>
      </div>
      <div className="flex items-center gap-3 ml-4 shrink-0">
        {field.confidence > 0 && (
          <span className={`text-xs font-mono font-semibold ${confidenceColour(field.confidence)}`}>
            {field.confidence}%
          </span>
        )}
        <StatusBadge status={field.status} />
      </div>
    </div>
  )
}

export default function CardUploadFlow() {
  const [stage, setStage] = useState<Stage>('ready')
  const [fileName, setFileName] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const runMockExtraction = useCallback((name: string) => {
    setFileName(name)
    setStage('uploading')
    setTimeout(() => setStage('extracting'), 1200)
    setTimeout(() => setStage('review_ready'), 2800)
  }, [])

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
    const file = files[0]
    if (!file.type.startsWith('image/')) return
    runMockExtraction(file.name)
  }

  function reset() {
    setStage('ready')
    setFileName(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  const reviewFields = mockExtractedFields.filter(f => f.confidence < CONFIDENCE_THRESHOLD)
  const isProcessing = stage === 'uploading' || stage === 'extracting'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Insurance Card Extraction</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Upload your insurance card to extract plan details automatically.
          </p>
        </div>
        {stage !== 'ready' && (
          <button
            onClick={reset}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
          >
            <RotateCcw size={14} /> Reset
          </button>
        )}
      </div>

      {/* Upload panel */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="p-5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Upload card</h2>
          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
            stage === 'review_ready'
              ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
              : isProcessing
              ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
              : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
          }`}>
            {STAGE_LABELS[stage]}
          </span>
        </div>

        <div className="p-5 space-y-4">
          {/* Drop zone */}
          <div
            onClick={() => stage === 'ready' && inputRef.current?.click()}
            onDragOver={e => { e.preventDefault(); if (stage === 'ready') setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={e => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
            className={`
              flex flex-col items-center justify-center rounded-xl border-2 border-dashed py-10 transition-colors
              ${stage === 'ready'
                ? dragOver
                  ? 'border-blue-400 bg-blue-50 dark:border-blue-500 dark:bg-blue-950/30 cursor-pointer'
                  : 'border-slate-300 dark:border-slate-600 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer'
                : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/30 cursor-default'
              }
            `}
          >
            {fileName ? (
              <>
                <FileImage size={32} className="text-blue-500 dark:text-blue-400 mb-2" strokeWidth={1.5} />
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">{fileName}</p>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Simulated extraction — real OCR not connected</p>
              </>
            ) : (
              <>
                <Upload size={32} className="text-slate-300 dark:text-slate-600 mb-3" strokeWidth={1.5} />
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">Drop your insurance card here</p>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">or click to browse — JPEG, PNG, WEBP</p>
              </>
            )}
          </div>

          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={e => handleFiles(e.target.files)}
          />

          {/* Progress bar */}
          {stage !== 'ready' && (
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
                <span>{STAGE_LABELS[stage]}</span>
                <span>{STAGE_PROGRESS[stage]}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-blue-500 transition-all duration-700"
                  style={{ width: `${STAGE_PROGRESS[stage]}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Extracted fields */}
      {stage === 'review_ready' && (
        <>
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700">
            <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800">
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Extracted fields</h2>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                Simulated extraction · fields below {CONFIDENCE_THRESHOLD}% confidence require review
              </p>
            </div>
            <div className="px-5 divide-y divide-slate-100 dark:divide-slate-800">
              {mockExtractedFields.map(f => <FieldRow key={f.label} field={f} />)}
            </div>
          </div>

          {/* Review queue */}
          {reviewFields.length > 0 && (
            <div className="bg-amber-50 dark:bg-amber-950/20 rounded-xl border border-amber-200 dark:border-amber-800">
              <div className="px-5 py-4 border-b border-amber-100 dark:border-amber-800/60 flex items-center gap-2">
                <AlertTriangle size={15} className="text-amber-500 shrink-0" />
                <div>
                  <h2 className="text-sm font-semibold text-amber-800 dark:text-amber-300">
                    Review queue · {reviewFields.length} field{reviewFields.length > 1 ? 's' : ''}
                  </h2>
                  <p className="text-xs text-amber-600 dark:text-amber-400/80 mt-0.5">
                    Confidence below {CONFIDENCE_THRESHOLD}% — verify before saving
                  </p>
                </div>
              </div>
              <div className="px-5 divide-y divide-amber-100 dark:divide-amber-800/40">
                {reviewFields.map(f => <FieldRow key={f.label} field={f} />)}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
