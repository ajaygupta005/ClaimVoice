/**
 * TTS client — tries Google TTS backend, falls back to null so the caller
 * can use browser speechSynthesis. The frontend never holds API keys.
 */

export interface TtsSynthesizeRequest {
  text: string
  voice?: string
  format?: 'mp3' | 'wav'
}

/** Unified backend response — always 200, branch on ok. */
export interface TtsSynthesizeResponse {
  ok: boolean
  provider: 'google' | 'browser'
  voiceName: string
  mimeType: string
  audioBase64: string
  reason: string
  fallback: string
}

/**
 * Returns the response when Google audio is available (ok=true + audioBase64),
 * or null when the backend says ok=false or is unreachable.
 */
export async function synthesizeSpeech(
  req: TtsSynthesizeRequest,
): Promise<TtsSynthesizeResponse | null> {
  try {
    const res = await fetch('/api/voice-agent/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
      signal: AbortSignal.timeout(8_000),
    })
    if (!res.ok) return null
    const data = await res.json() as TtsSynthesizeResponse
    if (!data.ok || !data.audioBase64) return null
    return data
  } catch {
    return null
  }
}
