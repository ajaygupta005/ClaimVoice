import { NextRequest, NextResponse } from 'next/server'

const VOICE_AGENT_URL =
  process.env.VOICE_AGENT_HTTP_URL ?? 'http://localhost:8004'

export async function POST(req: NextRequest): Promise<NextResponse> {
  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'invalid_request', detail: 'Body must be JSON' }, { status: 400 })
  }

  const upstream = `${VOICE_AGENT_URL}/api/v1/agent/respond`

  try {
    const res = await fetch(upstream, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      // 10s timeout via AbortSignal (Node 18+)
      signal: AbortSignal.timeout(10_000),
    })

    const data: unknown = await res.json()

    if (!res.ok) {
      return NextResponse.json(
        { error: 'upstream_error', detail: data },
        { status: res.status },
      )
    }

    return NextResponse.json(data, { status: 200 })
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return NextResponse.json(
      { error: 'backend_unavailable', detail: msg },
      { status: 503 },
    )
  }
}
