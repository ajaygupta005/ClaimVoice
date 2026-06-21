/**
 * Catch-all proxy: /api/document-ai/** → document-ai service :8001
 *
 * The backend expects JSON with a base64-encoded image string — no multipart.
 * Image bytes stay in the JSON body; the proxy forwards them without storing.
 */
import { NextRequest, NextResponse } from 'next/server'

const DOCUMENT_AI_URL = process.env.DOCUMENT_AI_HTTP_URL ?? 'http://localhost:8001'

async function proxy(req: NextRequest, params: { path?: string[] }): Promise<NextResponse> {
  const sub = params.path ? `/${params.path.join('/')}` : ''
  const upstream = `${DOCUMENT_AI_URL}/api/v1${sub}`

  try {
    const res = await fetch(upstream, {
      method: req.method,
      headers: { 'Content-Type': 'application/json' },
      body: req.method !== 'GET' && req.method !== 'HEAD' ? req.body : undefined,
      signal: AbortSignal.timeout(35_000),  // OCR can be slow
      // @ts-expect-error Node fetch supports duplex for streaming bodies
      duplex: 'half',
    })

    const data: unknown = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json(
      { error: 'service_unavailable', service: 'document-ai' },
      { status: 503 },
    )
  }
}

export async function GET(req: NextRequest, { params }: { params: Promise<{ path?: string[] }> }): Promise<NextResponse> {
  return proxy(req, await params)
}
export async function POST(req: NextRequest, { params }: { params: Promise<{ path?: string[] }> }): Promise<NextResponse> {
  return proxy(req, await params)
}
