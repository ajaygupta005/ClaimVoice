// WebSocket handler for Twilio Media Streams. Bridges audio to the voice agent.

import type { FastifyInstance, FastifyRequest } from 'fastify'
import type { TwilioFrame, StreamState } from './types.js'
import { ulawToPcm16, pcm16ToUlaw, resamplePcm16 } from '../audio_codec/index.js'
import { openBridge, type VoiceAgentBridge } from './voice_agent_bridge.js'
import { loadConfig } from '../lib/config.js'

const activeStreams = new Map<string, StreamState>()
const { VOICE_AGENT_WS_URL } = loadConfig()

export function registerMediaStreamHandler(app: FastifyInstance) {
  app.get('/media-stream', { websocket: true }, (connection, req: FastifyRequest) => {
    let state: StreamState | null = null
    let bridge: VoiceAgentBridge | null = null

    connection.socket.on('message', (raw: Buffer) => {
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

          bridge = openBridge(VOICE_AGENT_WS_URL, state.callSid, state.streamSid, req.log)
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
          bridge?.sendAudio(pcm24k)
        } else if (msg.event === 'stop' && state) {
          const duration = Date.now() - state.startedAt

          bridge?.sendStop()
          bridge?.close()
          bridge = null

          req.log.info({
            event: 'twilio_ws.stop',
            streamSid: state.streamSid,
            callSid: state.callSid,
            duration_ms: duration,
            bytes_in: state.bytesIn,
            bytes_out: state.bytesOut,
          })
          activeStreams.delete(state.streamSid)
          state = null
        }
      } catch (err) {
        req.log.error({ err })
      }
    })

    connection.socket.on('close', () => {
      if (state) {
        bridge?.sendStop()
        bridge?.close()
        bridge = null
        activeStreams.delete(state.streamSid)
      }
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
