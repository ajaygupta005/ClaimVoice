"""WebSocket endpoint: /api/v1/ws/gemini-live (Component 52).

Accepts raw PCM16 audio frames from the browser over a WebSocket connection,
passes them through the Gemini Live bridge, and emits normalized JSON events
back to the browser.

Protocol
--------
Browser → Server:
  - Binary frame: raw PCM16 LE audio at 16 kHz (one chunk per frame)
  - Text frame:   JSON {"type": "stop"} to signal end of speech

Server → Browser:
  - JSON {"kind": "session.opened", "session_id": "..."}
  - JSON {"kind": "transcript.partial", "text": "...", "confidence": 0.0}
  - JSON {"kind": "transcript.final",   "text": "...", "confidence": 0.0, "duration_ms": 0}
  - JSON {"kind": "session.closed",     "reason": "..."}
  - JSON {"kind": "error",              "code": "...", "message": "..."}

Security
--------
GEMINI_API_KEY never leaves the server. The browser sends raw audio; the server
holds the key and runs Gemini Live server-side.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from voice_agent.lib.logger import logger
from voice_agent.streaming.gemini_live_bridge import (
    BridgeErrorEvent,
    GeminiLiveSession,
    SessionClosedEvent,
    SessionOpenedEvent,
    TranscriptFinalEvent,
    TranscriptPartialEvent,
    build_gemini_bridge,
)

router = APIRouter()

# Maximum audio bytes we'll accept per WebSocket connection (safety cap)
_MAX_AUDIO_BYTES = 2 * 1024 * 1024  # 2 MB ≈ 60 s @ 16 kHz PCM16


def _event_to_json(ev: object) -> str:
    """Serialize a normalized bridge event dataclass to JSON string."""
    return json.dumps(dataclasses.asdict(ev))


async def _stream_events(
    ws: WebSocket,
    session: GeminiLiveSession,
) -> None:
    """Read events from the bridge session and forward them to the browser."""
    async for ev in session.events():
        if ws.client_state == WebSocketState.DISCONNECTED:
            break
        try:
            await ws.send_text(_event_to_json(ev))
        except Exception:
            break
        # Stop forwarding after the session closes or a hard error
        if isinstance(ev, (SessionClosedEvent, BridgeErrorEvent)):
            break


@router.websocket("/ws/gemini-live")
async def gemini_live_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("gemini_live_ws.connected")

    bridge = build_gemini_bridge()

    if not bridge.is_available():
        await websocket.send_text(
            json.dumps({"kind": "error", "code": "unavailable",
                        "message": "Gemini Live not configured on this server."})
        )
        await websocket.close()
        return

    total_audio_bytes = 0

    async with bridge.open_session() as session:
        # Fan-out: receive audio from browser while forwarding events to browser
        event_task = asyncio.create_task(_stream_events(websocket, session))

        try:
            while True:
                msg = await websocket.receive()

                # Binary frame → audio chunk
                if "bytes" in msg and msg["bytes"] is not None:
                    pcm = msg["bytes"]
                    total_audio_bytes += len(pcm)
                    if total_audio_bytes > _MAX_AUDIO_BYTES:
                        logger.warning("gemini_live_ws.audio_cap_exceeded")
                        await websocket.send_text(json.dumps({
                            "kind": "error", "code": "audio_cap_exceeded",
                            "message": "Audio session limit reached.",
                        }))
                        break
                    await session.send_audio(pcm)

                # Text frame → control message (only "stop" supported)
                elif "text" in msg and msg["text"] is not None:
                    try:
                        ctrl = json.loads(msg["text"])
                    except json.JSONDecodeError:
                        continue
                    if ctrl.get("type") == "stop":
                        logger.info("gemini_live_ws.stop_received",
                                    audio_bytes=total_audio_bytes)
                        break

        except WebSocketDisconnect:
            logger.info("gemini_live_ws.disconnected",
                        audio_bytes=total_audio_bytes)
        except Exception as exc:
            logger.error("gemini_live_ws.error", error=str(exc))
        finally:
            event_task.cancel()
            try:
                await event_task
            except asyncio.CancelledError:
                pass

    logger.info("gemini_live_ws.session_closed", audio_bytes=total_audio_bytes)
