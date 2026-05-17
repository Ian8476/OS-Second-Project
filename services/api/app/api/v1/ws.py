"""WebSocket que reenvia eventos del bus Redis al frontend.

Filtra por `case_id` para que cada cliente reciba solo los eventos
del caso que esta observando. El canal global se expone para la
vista de monitoreo.
"""

import asyncio
import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jwt import InvalidTokenError

from services.shared.events.bus import case_channel, get_event_bus, global_channel
from services.shared.logging_setup import get_logger
from services.shared.security import decode_token

router = APIRouter()
logger = get_logger("ws")


async def _authenticate(token: str | None) -> str | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
    except InvalidTokenError:
        return None
    return payload.get("sub")


async def _stream_pubsub(websocket: WebSocket, channel: str) -> None:
    bus = get_event_bus()
    pubsub = bus.subscribe([channel])
    try:
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
            if message and message.get("type") == "message":
                payload = message.get("data")
                if isinstance(payload, bytes):
                    payload = payload.decode("utf-8")
                await websocket.send_text(payload)
            await asyncio.sleep(0.05)
    finally:
        pubsub.unsubscribe(channel)
        pubsub.close()


@router.websocket("/cases/{case_id}")
async def case_events(
    websocket: WebSocket,
    case_id: str,
    token: str | None = Query(default=None),
):
    user_id = await _authenticate(token)
    if user_id is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    await websocket.send_text(json.dumps({"type": "connected", "case_id": case_id}))
    try:
        await _stream_pubsub(websocket, case_channel(case_id))
    except WebSocketDisconnect:
        logger.info("ws_disconnect", case_id=case_id, user_id=user_id)


@router.websocket("/monitoring")
async def monitoring(
    websocket: WebSocket,
    token: str | None = Query(default=None),
):
    user_id = await _authenticate(token)
    if user_id is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    await websocket.send_text(json.dumps({"type": "connected", "scope": "global"}))
    try:
        await _stream_pubsub(websocket, global_channel())
    except WebSocketDisconnect:
        logger.info("ws_monitoring_disconnect", user_id=user_id)
