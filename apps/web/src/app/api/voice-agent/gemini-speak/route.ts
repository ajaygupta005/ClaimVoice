import { NextRequest, NextResponse } from 'next/server'

const VOICE_AGENT_URL = process.env.VOICE_AGENT_HTTP_URL ?? 'http://localhost:8004'

export async function POST(req: NextRequest): Promise<NextResponse> {
  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'invalid_request' }, { status: 400 })
  }

  try {
    const res = await fetch(`${VOICE_AGENT_URL}/api/v1/gemini-live/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(30_000),
    })
    const data: unknown = await res.json()
    if (!res.ok) {
      return NextResponse.json({ error: 'upstream_error', detail: data }, { status: res.status })
    }
    return NextResponse.json(data)
  } catch {
    // Backend offline — return ok=false so the browser falls back to browser TTS
    return NextResponse.json({
      ok: false,
      provider: 'browser',
      voiceName: '',
      mimeType: '',
      audioBase64: '',
      reason: 'voice agent unavailable',
      fallback: 'browser',
    })
  }
}
