import { NextResponse } from 'next/server'

const VOICE_AGENT_URL = process.env.VOICE_AGENT_HTTP_URL ?? 'http://localhost:8004'

export async function GET(): Promise<NextResponse> {
  try {
    const res = await fetch(`${VOICE_AGENT_URL}/api/v1/runtime/status`, {
      // Cold backend: first call runs Python imports + the RAG chunk-count DB
      // query, which can exceed a few seconds. Give it room so we don't fall
      // back to "browser STT / RAG unavailable" while the service warms up.
      signal: AbortSignal.timeout(9_000),
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
