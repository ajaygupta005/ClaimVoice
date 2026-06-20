import { NextResponse } from 'next/server'

const VOICE_AGENT_URL = process.env.VOICE_AGENT_HTTP_URL ?? 'http://localhost:8004'

export async function GET(): Promise<NextResponse> {
  try {
    const res = await fetch(`${VOICE_AGENT_URL}/api/v1/runtime/status`, {
      signal: AbortSignal.timeout(4_000),
    })
    const data: unknown = await res.json()
    if (!res.ok) {
      return NextResponse.json({ error: 'upstream_error', detail: data }, { status: res.status })
    }
    return NextResponse.json(data)
  } catch {
    // Backend offline — return a safe fallback so the UI still renders
    return NextResponse.json({
      runtime: 'fallback',
      model: '',
      voice: '',
      note: 'Voice agent backend unavailable.',
    })
  }
}
