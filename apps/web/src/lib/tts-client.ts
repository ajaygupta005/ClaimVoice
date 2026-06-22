/**
 * TTS client — asks the voice-agent backend for playable audio. The backend
 * may use Cartesia, Google Cloud TTS, or local system TTS; the frontend never holds API keys.
 */

export interface TtsSynthesizeRequest {
  text: string
  voice?: string
  format?: 'mp3' | 'wav'
}

/** Unified backend response — always 200, branch on ok. */
export interface TtsSynthesizeResponse {
  ok: boolean
  provider: 'cartesia' | 'google' | 'browser' | 'system'
  voiceName: string
  mimeType: string
  audioBase64: string
  reason: string
  /** Machine-readable failure code, e.g. cartesia_timeout, cartesia_key_missing. */
  errorCode: string
  fallback: string
}

/**
 * Returns the response when backend audio is available (ok=true + audioBase64),
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
      signal: AbortSignal.timeout(60_000),
    })
    if (!res.ok) return null
    const data = await res.json() as TtsSynthesizeResponse
    if (!data.ok || !data.audioBase64) return null
    return data
  } catch {
    return null
  }
}

/**
 * Ask the backend to synthesise the final ClaimVoice answer text via Gemini Live.
 * Returns null on failure so the caller can fall back to browser TTS.
 * The Gemini API key never leaves the server.
 */
export async function synthesizeGeminiSpeech(
  text: string,
): Promise<TtsSynthesizeResponse | null> {
  try {
    const res = await fetch('/api/voice-agent/gemini-speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
      signal: AbortSignal.timeout(60_000),
    })
    if (!res.ok) return null
    const data = await res.json() as TtsSynthesizeResponse
    if (!data.ok || !data.audioBase64) return null
    return data
  } catch {
    return null
  }
}
