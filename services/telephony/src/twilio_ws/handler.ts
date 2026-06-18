// WebSocket handler for Twilio Media Streams. Bridges audio to the voice agent.

import type { FastifyInstance, FastifyRequest } from 'fastify'
import type { WebSocket } from 'ws'
import type { TwilioFrame, StreamState } from './types.js'
import { ulawToPcm16, pcm16ToUlaw, resamplePcm16 } from '../audio_codec/index.js'
import { openBridge, type VoiceAgentBridge } from './voice_agent_bridge.js'
import { loadConfig } from '../lib/config.js'
import {
  callsTotal,
  callDurationSeconds,
  activeCalls,
  audioBytesTotal,
} from '../lib/metrics.js'

const activeStreams = new Map<string, StreamState>()
const { VOICE_AGENT_WS_URL } = loadConfig()

export function registerMediaStreamHandler(app: FastifyInstance) {
  // @fastify/websocket v11: the handler receives the raw ws WebSocket directly.
  app.get('/media-stream', { websocket: true }, (socket: WebSocket, req: FastifyRequest) => {
    let state: StreamState | null = null
    let bridge: VoiceAgentBridge | null = null
    let finalized = false

    // Finalize exactly once, whether the call ends via a Twilio `stop` frame
    // or an abrupt socket close (caller hangs up). Counts the call, records
    // duration, decrements the active gauge, and tears down the bridge.
    function finalize(reason: 'stop' | 'close'): void {
      if (finalized || !state) return
      finalized = true

      const duration = Date.now() - state.startedAt
      bridge?.sendStop()
      bridge?.close()
      bridge = null

      callsTotal.inc({ direction: 'inbound', status: 'completed' })
      callDurationSeconds.observe({ direction: 'inbound' }, duration / 1000)
      activeCalls.dec()

      req.log.info({
        event: 'twilio_ws.finalize',
        reason,
        streamSid: state.streamSid,
        callSid: state.callSid,
        duration_ms: duration,
        bytes_in: state.bytesIn,
        bytes_out: state.bytesOut,
      })
      activeStreams.delete(state.streamSid)
      state = null
    }

    // Called by the bridge whenever the voice-agent sends back a tts.audio event.
    // Converts PCM16 24 kHz → µ-law 8 kHz and writes a Twilio media frame to the
    // caller's WebSocket.
    function onReturnAudio(pcm24k: Buffer, isFinal: boolean): void {
      if (!state) return
      try {
        const frame = pcm16ToTwilioFrame(state.streamSid, pcm24k)
        const frameBytes = Buffer.byteLength(frame)
        state.bytesOut += frameBytes
        audioBytesTotal.inc({ direction: 'outbound' }, frameBytes)
        socket.send(frame)
        req.log.debug({
          event: 'twilio_ws.return_audio',
          streamSid: state.streamSid,
          callSid: state.callSid,
          bytes: frameBytes,
          isFinal,
        })
      } catch (err) {
        req.log.warn({ event: 'twilio_ws.return_audio_error', streamSid: state?.streamSid, err })
      }
    }

    socket.on('message', (raw: Buffer) => {
      try {
        const msg = JSON.parse(raw.toString()) as TwilioFrame

        if (msg.event === 'start') {
          state = {
            streamSid: msg.start.streamSid,
            callSid: msg.start.callSid,
            startedAt: Date.now(),
            bytesIn: 0,
            bytesOut: 0,
          }
          activeStreams.set(state.streamSid, state)
          activeCalls.inc()

          bridge = openBridge(VOICE_AGENT_WS_URL, state.callSid, state.streamSid, req.log, onReturnAudio)
          bridge.sendStart({
            callSid: state.callSid,
            streamSid: state.streamSid,
            mediaFormat: msg.start.mediaFormat,
          })

          req.log.info({
            event: 'twilio_ws.start',
            streamSid: state.streamSid,
            callSid: state.callSid,
          })
        } else if (msg.event === 'media' && state) {
          // Twilio sends mu-law 8 kHz → decode and resample to PCM16 24 kHz for the agent.
          const ulaw = Buffer.from(msg.media.payload, 'base64')
          const pcm8k = ulawToPcm16(ulaw)
          const pcm24k = resamplePcm16(pcm8k, 8000, 24000)
          state.bytesIn += ulaw.length
          audioBytesTotal.inc({ direction: 'inbound' }, ulaw.length)
          bridge?.sendAudio(pcm24k)
        } else if (msg.event === 'stop' && state) {
          finalize('stop')
        }
      } catch (err) {
        req.log.error({ err })
      }
    })

    socket.on('close', () => {
      // Abrupt hangup with no `stop` frame still finalizes (idempotent).
      finalize('close')
    })
  })
}

// Outbound: send PCM16 24 kHz audio to Twilio, encoded as mu-law 8 kHz.
export function pcm16ToTwilioFrame(streamSid: string, pcm24k: Buffer): string {
  const pcm8k = resamplePcm16(pcm24k, 24000, 8000)
  const ulaw = pcm16ToUlaw(pcm8k)
  return JSON.stringify({
    event: 'media',
    streamSid,
    media: { payload: ulaw.toString('base64') },
  })
}
