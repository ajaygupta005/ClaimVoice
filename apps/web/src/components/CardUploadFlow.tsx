'use client'

import { useCallback, useRef, useState } from 'react'
import { Upload, FileImage, RotateCcw, CheckCircle, AlertTriangle, XCircle, Cpu, FlaskConical } from 'lucide-react'
import { mockExtractedFields, type ExtractedField } from '@/lib/mock-data'
import {
  documentAiOcrCard,
  documentAiClassifyCard,
  normalizeOcrResult,
  normalizeClassifyResult,
  type NormalizedCardFields,
  type NormalizedPayorClassification,
} from '@/lib/api/document-ai'

// ── Stage machine ─────────────────────────────────────────────────────────────

type Stage =
  | 'ready'
  | 'uploading'
  | 'extracting'
  | 'review_ready'
  | 'unavailable'
  | 'error'

const STAGE_LABELS: Record<Stage, string> = {
  ready:        'Ready',
  uploading:    'Uploading…',
  extracting:   'Extracting fields…',
  review_ready: 'Extraction complete',
  unavailable:  'Document AI unavailable',
  error:        'Extraction failed',
}

const STAGE_PROGRESS: Record<Stage, number> = {
  ready:        0,
  uploading:    30,
  extracting:   70,
  review_ready: 100,
  unavailable:  0,
  error:        0,
}

// ── Data source badge ─────────────────────────────────────────────────────────

type DataSource = 'real' | 'demo'

function SourceBadge({ source }: { source: DataSource }) {
  if (source === 'real') return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
      <Cpu size={10} /> Document AI
    </span>
  )
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
      <FlaskConical size={10} /> Demo fallback
    </span>
  )
}

// ── Confidence helpers ────────────────────────────────────────────────────────

const CONFIDENCE_THRESHOLD = 90

function confidenceColour(c: number) {
  if (c === 0)  return 'text-slate-400 dark:text-slate-500'
  if (c < 85)   return 'text-amber-600 dark:text-amber-400'
  if (c < 90)   return 'text-amber-500 dark:text-amber-300'
  return 'text-green-600 dark:text-green-400'
}

// ── Status badge ──────────────────────────────────────────────────────────────

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

// ── Field row ─────────────────────────────────────────────────────────────────

function FieldRow({ field }: { field: ExtractedField }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-100 dark:border-slate-800 last:border-0">
      <div className="min-w-0">
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">{field.label}</p>
        <p className={`text-sm font-semibold mt-0.5 ${
          field.status === 'missing'
            ? 'text-slate-400 dark:text-slate-600 italic'
            : 'text-slate-900 dark:text-slate-100'
        }`}>
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

// ── Normalised ExtractedField from real API result ────────────────────────────

function normalizedToExtractedFields(result: NormalizedCardFields): ExtractedField[] {
  return result.fields.map(f => ({
    label:      f.label,
    value:      f.value,
    confidence: f.confidence,
    source:     f.source,
    status:     f.status,
  }))
}

// ── Mock fields as ExtractedField[] ──────────────────────────────────────────

function demoFields(): ExtractedField[] {
  return mockExtractedFields
}

// ── Main component ────────────────────────────────────────────────────────────

export default function CardUploadFlow() {
  const [stage,         setStage]        = useState<Stage>('ready')
  const [fileName,      setFileName]     = useState<string | null>(null)
  const [fields,        setFields]       = useState<ExtractedField[]>([])
  const [dataSource,    setDataSource]   = useState<DataSource>('demo')
  const [modelVersion,  setModelVersion] = useState<string>('')
  const [payor,         setPayor]        = useState<NormalizedPayorClassification | null>(null)
  const [errorMessage,  setErrorMessage] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  const reset = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setStage('ready')
    setFileName(null)
    setFields([])
    setDataSource('demo')
    setModelVersion('')
    setPayor(null)
    setErrorMessage(null)
    if (inputRef.current) inputRef.current.value = ''
  }, [])

  const runExtraction = useCallback(async (file: File) => {
    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac

    setFileName(file.name)
    setStage('uploading')
    setErrorMessage(null)

    // Small delay so the uploading state is visible for a beat
    await new Promise(r => setTimeout(r, 400))
    if (ac.signal.aborted) return

    setStage('extracting')

    // Run OCR and classification in parallel
    let ocrResult: Awaited<ReturnType<typeof documentAiOcrCard>>
    let classifyResult: Awaited<ReturnType<typeof documentAiClassifyCard>>
    try {
      ;[ocrResult, classifyResult] = await Promise.all([
        documentAiOcrCard(file, ac.signal),
        documentAiClassifyCard(file, ac.signal),
      ])
    } catch (err) {
      // apiFetch re-throws AbortError on cancellation (reset / new upload mid-
      // extraction). Expected — exit quietly so it doesn't surface as a runtime
      // error overlay; otherwise show the failure.
      if (ac.signal.aborted || (err instanceof Error && err.name === 'AbortError')) return
      setErrorMessage(err instanceof Error ? err.message : 'Extraction failed')
      setStage('error')
      return
    }

    if (ac.signal.aborted) return

    // Handle unavailable (service down, no model loaded)
    if (!ocrResult.ok && !ocrResult.isUnavailable) {
      setErrorMessage(ocrResult.error ?? 'Extraction failed')
      setStage('error')
      return
    }

    if (!ocrResult.ok && ocrResult.isUnavailable) {
      setStage('unavailable')
      return
    }

    // ocrResult.ok === true (TypeScript narrowing needs the explicit guard)
    if (!ocrResult.ok) return
    const normalized = normalizeOcrResult(ocrResult.data)
    const extractedFields = normalizedToExtractedFields(normalized)

    setFields(extractedFields)
    setModelVersion(normalized.modelVersion)
    setDataSource(ocrResult.isDemo ? 'demo' : 'real')

    if (classifyResult.ok) {
      setPayor(normalizeClassifyResult(classifyResult.data))
    }

    setStage('review_ready')
  }, [])

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
    const file = files[0]
    if (!file.type.startsWith('image/')) return
    void runExtraction(file)
  }

  const reviewFields = fields.filter(f => f.confidence > 0 && f.confidence < CONFIDENCE_THRESHOLD)
  const isProcessing = stage === 'uploading' || stage === 'extracting'
  const [dragOver, setDragOver] = useState(false)

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
              : stage === 'unavailable' || stage === 'error'
              ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
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
                {isProcessing && (
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Processing…</p>
                )}
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
          {isProcessing && (
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

          {/* Document AI unavailable */}
          {stage === 'unavailable' && (
            <div className="rounded-lg bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 p-4 flex items-start gap-3">
              <XCircle size={16} className="text-red-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-red-800 dark:text-red-300">Document AI unavailable</p>
                <p className="text-xs text-red-600 dark:text-red-400 mt-0.5">
                  The OCR model is not loaded. Run <code className="font-mono">just train.card_ocr</code> or
                  place model artifacts and restart the service. The demo fallback below uses synthetic data.
                </p>
                <button
                  onClick={() => {
                    setStage('review_ready')
                    setFields(demoFields())
                    setDataSource('demo')
                  }}
                  className="mt-2 text-xs text-red-700 dark:text-red-400 underline hover:no-underline"
                >
                  Show demo extraction anyway
                </button>
              </div>
            </div>
          )}

          {/* Extraction error */}
          {stage === 'error' && errorMessage && (
            <div className="rounded-lg bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 p-4 flex items-start gap-3">
              <XCircle size={16} className="text-red-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-red-800 dark:text-red-300">Extraction failed</p>
                <p className="text-xs text-red-600 dark:text-red-400 mt-0.5">{errorMessage}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Extracted fields */}
      {stage === 'review_ready' && fields.length > 0 && (
        <>
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700">
            <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Extracted fields</h2>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                  Fields below {CONFIDENCE_THRESHOLD}% confidence require review
                  {modelVersion && modelVersion !== 'demo' && (
                    <span className="ml-1">· model {modelVersion}</span>
                  )}
                </p>
              </div>
              <SourceBadge source={dataSource} />
            </div>
            <div className="px-5 divide-y divide-slate-100 dark:divide-slate-800">
              {fields.map(f => <FieldRow key={f.label} field={f} />)}
            </div>
          </div>

          {/* Payor classification */}
          {payor && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 px-5 py-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Payor Classification</p>
                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 mt-0.5">{payor.payorLabel}</p>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                  {payor.sourceModel !== 'demo' ? payor.sourceModel : 'Demo model'}{' · '}
                  confidence {payor.confidence}%
                </p>
              </div>
              <span className={`text-sm font-mono font-bold ${confidenceColour(payor.confidence)}`}>
                {payor.confidence}%
              </span>
            </div>
          )}

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
