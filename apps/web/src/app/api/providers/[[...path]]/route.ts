/**
 * Catch-all proxy: /api/providers/** → providers service :8003
 */
import { NextRequest, NextResponse } from 'next/server'

const PROVIDERS_URL = process.env.PROVIDERS_HTTP_URL ?? 'http://localhost:8003'

async function proxy(req: NextRequest, params: { path?: string[] }): Promise<NextResponse> {
  const sub = params.path ? `/${params.path.join('/')}` : ''
  const upstream = `${PROVIDERS_URL}/api/v1${sub}`

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
      { error: 'service_unavailable', service: 'providers' },
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
