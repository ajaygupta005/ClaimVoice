import { NextRequest, NextResponse } from 'next/server'

// Proxy browser calls to the providers service (WS-5). Mirrors the voice-agent proxy.
const BASE = process.env.PROVIDERS_BASE_URL ?? 'http://localhost:8003'

async function proxy(req: NextRequest, slug: string[]): Promise<NextResponse> {
  // providers endpoints live under /api/v1/providers/* (e.g. providers/near, providers/bulk)
  const url = `${BASE}/api/v1/providers/${slug.join('/')}${req.nextUrl.search}`
  const init: RequestInit = {
    method: req.method,
    headers: { 'Content-Type': 'application/json' },
    signal: AbortSignal.timeout(10_000),
  }
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    init.body = await req.text()
  }
  try {
    const res = await fetch(url, init)
    const data: unknown = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return NextResponse.json({ error: 'backend_unavailable', detail: msg }, { status: 503 })
  }
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ slug: string[] }> }) {
  return proxy(req, (await ctx.params).slug)
}
export async function POST(req: NextRequest, ctx: { params: Promise<{ slug: string[] }> }) {
  return proxy(req, (await ctx.params).slug)
}
