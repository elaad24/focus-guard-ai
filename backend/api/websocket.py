from __future__ import annotations

import asyncio
import json
import threading
import time
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from logic.world_state import world_state

_connections: set[WebSocket] = set()
_lock = threading.Lock()
_running = False
_thread: threading.Thread | None = None
BROADCAST_INTERVAL_SECONDS = 1.0


async def connect(websocket: WebSocket) -> None:
    await websocket.accept()
    with _lock:
        _connections.add(websocket)
    await websocket.send_text(json.dumps(world_state.snapshot()))


def disconnect(websocket: WebSocket) -> None:
    with _lock:
        _connections.discard(websocket)


def start_broadcaster() -> None:
    global _running, _thread
    if _running:
        return
    _running = True
    _thread = threading.Thread(target=_broadcast_loop, daemon=True, name="ws-broadcast")
    _thread.start()


def stop_broadcaster() -> None:
    global _running
    _running = False


def _broadcast_loop() -> None:
    while _running:
        payload = json.dumps(world_state.snapshot())
        dead: list[WebSocket] = []
        with _lock:
            connections = list(_connections)
        for ws in connections:
            try:
                asyncio.run(_send(ws, payload))
            except Exception:
                dead.append(ws)
        if dead:
            with _lock:
                for ws in dead:
                    _connections.discard(ws)
        time.sleep(BROADCAST_INTERVAL_SECONDS)


async def _send(websocket: WebSocket, payload: str) -> None:
    await websocket.send_text(payload)


async def websocket_status_handler(websocket: WebSocket) -> None:
    await connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        disconnect(websocket)
