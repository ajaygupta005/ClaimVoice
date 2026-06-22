/**
 * Catch-all proxy: /api/eligibility/** → eligibility service :8002
 *
 * All sub-paths (/coverage, /cost/estimate, /formulary/lookup, /health, …)
 * are forwarded verbatim. Service URL is server-side only.
 */
import { NextRequest, NextResponse } from 'next/server'

const ELIGIBILITY_URL = process.env.ELIGIBILITY_HTTP_URL ?? 'http://localhost:8002'

async function proxy(req: NextRequest, params: { path?: string[] }): Promise<NextResponse> {
  const sub = params.path ? `/${params.path.join('/')}` : ''
  const upstream = `${ELIGIBILITY_URL}/api/v1${sub}`

  try {
    const headers = new Headers()
    if (req.headers.get('content-type')) {
      headers.set('content-type', req.headers.get('content-type')!)
    }

    const res = await fetch(upstream, {
      method: req.method,
      headers,
      body: req.method !== 'GET' && req.method !== 'HEAD' ? req.body : undefined,
      signal: AbortSignal.timeout(12_000),
      // @ts-expect-error Node fetch supports duplex for streaming bodies
      duplex: 'half',
    })

    const data: unknown = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json(
      { error: 'service_unavailable', service: 'eligibility' },
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
