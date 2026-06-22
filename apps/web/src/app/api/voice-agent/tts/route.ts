import { NextResponse } from 'next/server'

const VOICE_AGENT_HTTP_URL =
  process.env.VOICE_AGENT_HTTP_URL ?? 'http://localhost:8004'

export async function POST(req: Request) {
  try {
    const body = await req.json()
    const upstream = await fetch(`${VOICE_AGENT_HTTP_URL}/api/v1/tts/synthesize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(60_000),
    })
    if (!upstream.ok) {
      return NextResponse.json({ error: 'upstream_error' }, { status: upstream.status })
    }
    const data = await upstream.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ error: 'backend_unavailable' }, { status: 503 })
  }
}
