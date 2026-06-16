from __future__ import annotations

import asyncio
import json
import threading
import time

from fastapi import WebSocket, WebSocketDisconnect

from logic.world_state import world_state

_connections: set[WebSocket] = set()
_lock = threading.Lock()
_broadcast_task: asyncio.Task | None = None
BROADCAST_INTERVAL_SECONDS = 2.0
_POLL_INTERVAL_SECONDS = 0.25


async def connect(websocket: WebSocket) -> None:
    await websocket.accept()
    with _lock:
        _connections.add(websocket)
    await websocket.send_text(json.dumps(world_state.snapshot()))


def disconnect(websocket: WebSocket) -> None:
    with _lock:
        _connections.discard(websocket)


def start_broadcaster() -> None:
    global _broadcast_task
    if _broadcast_task is not None and not _broadcast_task.done():
        return
    _broadcast_task = asyncio.create_task(_broadcast_loop(), name="ws-broadcast")


async def stop_broadcaster() -> None:
    global _broadcast_task
    if _broadcast_task is None:
        return
    _broadcast_task.cancel()
    try:
        await _broadcast_task
    except asyncio.CancelledError:
        pass
    _broadcast_task = None


async def _broadcast_loop() -> None:
    last_forced_broadcast = time.monotonic()
    try:
        while True:
            now = time.monotonic()
            should_send = world_state.should_broadcast() or (
                now - last_forced_broadcast >= BROADCAST_INTERVAL_SECONDS
            )
            if should_send:
                payload = json.dumps(world_state.snapshot())
                dead: list[WebSocket] = []
                with _lock:
                    connections = list(_connections)
                for ws in connections:
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        dead.append(ws)
                if dead:
                    with _lock:
                        for ws in dead:
                            _connections.discard(ws)
                world_state.mark_broadcasted()
                last_forced_broadcast = now
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        raise


async def websocket_status_handler(websocket: WebSocket) -> None:
    await connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        disconnect(websocket)
