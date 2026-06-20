"""
WebSocket endpoint: /api/v1/ws/telephony

Receives bridge events from the telephony service (Component 23),
maintains per-connection session state, and pipes audio through the
STT adapter (Component 25). Transcript events are sent back over the
same WebSocket connection.

Query parameters (set by the bridge):
  callSid   — Twilio call SID
  streamSid — Twilio stream SID
"""

from __future__ import annotations

import json
from dataclasses import dataclass
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
from voice_agent.services.answer_orchestrator import orchestrate
from voice_agent.streaming.factory import build_stt, build_tts
from voice_agent.streaming.stt_adapter import StreamingSTT
from voice_agent.streaming.tts_adapter import TtsAudioEvent

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
    stt: Optional[StreamingSTT] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _send_json(ws: WebSocket, payload: str) -> None:
    await ws.send_text(payload)


async def _send_ack(ws: WebSocket, ack: AckResponse) -> None:
    await _send_json(ws, ack.model_dump_json(exclude_none=True))


async def _send_error(ws: WebSocket, error: str, detail: str) -> None:
    await _send_json(ws, ErrorResponse(error=error, detail=detail).model_dump_json())


# ── Event handlers ────────────────────────────────────────────────────────────

async def _handle_start(ws: WebSocket, ev: StartEvent, session: SessionState) -> None:
    session.started = True
    session.stt = build_stt(call_sid=ev.callSid, stream_sid=ev.streamSid)
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

    # Send ack first so the bridge knows the frame was received
    await _send_ack(
        ws,
        AckResponse(ack="audio", callSid=ev.callSid, streamSid=ev.streamSid, bytes=len(pcm)),
    )

    # Feed audio through the STT adapter; emit any partial transcripts
    if session.stt is not None:
        partials = session.stt.push_audio(pcm)
        for partial in partials:
            logger.debug(
                "stt.partial",
                call_sid=ev.callSid,
                stream_sid=ev.streamSid,
                text=partial.text,
                confidence=partial.confidence,
            )
            await _send_json(ws, partial.model_dump_json())


async def _handle_stop(ws: WebSocket, ev: StopEvent, session: SessionState) -> None:
    session.stopped = True

    # Flush the STT adapter to get the final transcript before closing
    if session.stt is not None:
        final = session.stt.flush()
        if final is not None:
            logger.info(
                "stt.final",
                call_sid=ev.callSid,
                stream_sid=ev.streamSid,
                text=final.text,
                confidence=final.confidence,
                duration_ms=final.duration_ms,
            )
            await _send_json(ws, final.model_dump_json())

            # Orchestrate a grounded answer from the transcript
            answer = orchestrate(final)
            logger.info(
                "answer.final",
                call_sid=ev.callSid,
                stream_sid=ev.streamSid,
                intent=answer.intent,
                grounded=answer.grounded,
                tools=[t.tool for t in answer.tool_trace],
            )
            await _send_json(ws, answer.model_dump_json())

            # Synthesize the answer into TTS audio chunks
            tts = build_tts()
            tts_events = tts.synthesize(answer.text, ev.callSid, ev.streamSid)
            audio_count = sum(1 for e in tts_events if isinstance(e, TtsAudioEvent))
            logger.info(
                "tts.synthesized",
                call_sid=ev.callSid,
                stream_sid=ev.streamSid,
                chunks=audio_count,
            )
            for tts_ev in tts_events:
                await _send_json(ws, tts_ev.model_dump_json())

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

            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                await _send_error(websocket, "invalid_json", str(exc))
                continue

            try:
                event: BridgeEvent = _bridge_event_adapter.validate_python(data)
            except ValidationError as exc:
                await _send_error(websocket, "invalid_event", exc.errors()[0]["msg"])
                continue

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
