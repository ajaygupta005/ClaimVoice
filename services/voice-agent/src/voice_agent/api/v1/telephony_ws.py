"""
WebSocket endpoint: /api/v1/ws/telephony

Receives bridge events from the telephony service (Component 23) and
maintains per-connection session state. Placeholder for WS-6 STT/TTS
pipeline — today it validates, logs, and acknowledges each event.

Query parameters (set by the bridge):
  callSid   — Twilio call SID
  streamSid — Twilio stream SID
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError

from voice_agent.lib.logger import logger
from voice_agent.schemas.telephony_bridge import (
    AckResponse,
    AudioEvent,
    BridgeEvent,
    ErrorResponse,
    StartEvent,
    StopEvent,
)

router = APIRouter()

_bridge_event_adapter: TypeAdapter[BridgeEvent] = TypeAdapter(BridgeEvent)


# ── Per-connection session state ──────────────────────────────────────────────

@dataclass
class SessionState:
    call_sid: str
    stream_sid: str
    started: bool = False
    audio_bytes_received: int = 0
    audio_frames: int = 0
    stopped: bool = False


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _send_ack(ws: WebSocket, ack: AckResponse) -> None:
    await ws.send_text(ack.model_dump_json(exclude_none=True))


async def _send_error(ws: WebSocket, error: str, detail: str) -> None:
    resp = ErrorResponse(error=error, detail=detail)
    await ws.send_text(resp.model_dump_json())


# ── Event handlers ────────────────────────────────────────────────────────────

async def _handle_start(ws: WebSocket, ev: StartEvent, session: SessionState) -> None:
    session.started = True
    logger.info(
        "bridge.session_started",
        call_sid=ev.callSid,
        stream_sid=ev.streamSid,
        media_format=ev.mediaFormat.model_dump() if ev.mediaFormat else None,
    )
    await _send_ack(ws, AckResponse(ack="start", callSid=ev.callSid, streamSid=ev.streamSid))


async def _handle_audio(ws: WebSocket, ev: AudioEvent, session: SessionState) -> None:
    if not session.started:
        await _send_error(ws, "unexpected_audio", "audio received before start event")
        return
    pcm = ev.decode_pcm()
    session.audio_bytes_received += len(pcm)
    session.audio_frames += 1
    # TODO (WS-6): forward pcm bytes into the STT pipeline
    await _send_ack(
        ws,
        AckResponse(ack="audio", callSid=ev.callSid, streamSid=ev.streamSid, bytes=len(pcm)),
    )


async def _handle_stop(ws: WebSocket, ev: StopEvent, session: SessionState) -> None:
    session.stopped = True
    logger.info(
        "bridge.session_stopped",
        call_sid=ev.callSid,
        stream_sid=ev.streamSid,
        audio_bytes=session.audio_bytes_received,
        audio_frames=session.audio_frames,
    )
    await _send_ack(ws, AckResponse(ack="stop", callSid=ev.callSid, streamSid=ev.streamSid))


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.websocket("/ws/telephony")
async def telephony_ws(
    websocket: WebSocket,
    callSid: Optional[str] = Query(default=None),
    streamSid: Optional[str] = Query(default=None),
) -> None:
    await websocket.accept()
    logger.info("bridge.connected", call_sid=callSid, stream_sid=streamSid)

    session: Optional[SessionState] = None
    if callSid and streamSid:
        session = SessionState(call_sid=callSid, stream_sid=streamSid)

    try:
        while True:
            raw = await websocket.receive_text()

            # Parse the raw JSON payload
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                await _send_error(websocket, "invalid_json", str(exc))
                continue

            # Validate against the discriminated union
            try:
                event: BridgeEvent = _bridge_event_adapter.validate_python(data)
            except ValidationError as exc:
                await _send_error(websocket, "invalid_event", exc.errors()[0]["msg"])
                continue

            # Bootstrap session from the event if query params were absent
            if session is None:
                session = SessionState(call_sid=event.callSid, stream_sid=event.streamSid)

            if isinstance(event, StartEvent):
                await _handle_start(websocket, event, session)
            elif isinstance(event, AudioEvent):
                await _handle_audio(websocket, event, session)
            elif isinstance(event, StopEvent):
                await _handle_stop(websocket, event, session)

    except WebSocketDisconnect:
        logger.info(
            "bridge.disconnected",
            call_sid=callSid,
            stream_sid=streamSid,
            audio_bytes=session.audio_bytes_received if session else 0,
        )
