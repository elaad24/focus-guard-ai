from __future__ import annotations

from typing import Any

import cv2
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from detection.screen_zone import screen_zone_store
from logic.config_store import config_store
from logic.mode_rules import validate_mode
from logic.world_state import world_state

router = APIRouter()

_state_machine = None
_camera = None
_yolo = None
_kb_mouse = None
_sound_alert = None


def bind_runtime(state_machine, camera, yolo, kb_mouse, sound_alert) -> None:
    global _state_machine, _camera, _yolo, _kb_mouse, _sound_alert
    _state_machine = state_machine
    _camera = camera
    _yolo = yolo
    _kb_mouse = kb_mouse
    _sound_alert = sound_alert


class ModeRequest(BaseModel):
    mode: str


class ScreenZoneRequest(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class SettingsUpdate(BaseModel):
    mode: str | None = None
    softWarningAfterSeconds: int | None = Field(default=None, ge=5, le=600)
    mediumWarningAfterSeconds: int | None = Field(default=None, ge=5, le=600)
    finalAlertAfterSeconds: int | None = Field(default=None, ge=5, le=600)
    phoneUsageLimitSeconds: int | None = Field(default=None, ge=5, le=600)
    keyboardMouseIdleLimitSeconds: int | None = Field(default=None, ge=5, le=600)
    procrastinationScoreThreshold: int | None = Field(default=None, ge=0, le=100)
    cooldownAfterDismissSeconds: int | None = Field(default=None, ge=0, le=3600)
    soundEnabled: bool | None = None
    notificationsEnabled: bool | None = None
    debugMode: bool | None = None
    saveRawVideo: bool | None = None


@router.post("/camera/frame")
async def ingest_camera_frame(request: Request) -> dict[str, bool]:
    if _camera is None:
        raise HTTPException(status_code=503, detail="Camera runtime not initialized")
    if _camera.source != "browser":
        raise HTTPException(status_code=409, detail="Backend is not configured for browser camera frames")

    jpeg_bytes = await request.body()
    if not _camera.submit_browser_frame(jpeg_bytes):
        raise HTTPException(status_code=400, detail="Invalid or oversized camera frame")

    return {"accepted": True}


@router.get("/camera/frame")
def camera_frame() -> Response:
    if _camera is None:
        raise HTTPException(status_code=503, detail="Camera runtime not initialized")

    frame = _camera.get_frame()
    if frame is None:
        raise HTTPException(status_code=503, detail="No camera frame available yet")

    encoded_ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
    if not encoded_ok:
        raise HTTPException(status_code=500, detail="Failed to encode camera frame")

    return Response(content=encoded.tobytes(), media_type="image/jpeg")


@router.get("/health")
def health() -> dict[str, Any]:
    snapshot = world_state.snapshot()
    return {
        "backend": "ok",
        "camera": "ok" if snapshot.get("camera_ok") else "error",
        "model": "ok" if snapshot.get("model_ok") else "error",
        "keyboard_mouse": "ok" if snapshot.get("kb_mouse_ok") else "error",
        "websocket": "ok",
        "alert_system": "ok" if snapshot.get("alert_system_ok") else "error",
        "fps": snapshot.get("fps", 0),
        "mode": snapshot.get("mode", "normal"),
    }


@router.get("/settings")
def get_settings() -> dict[str, Any]:
    return config_store.get()


@router.post("/settings")
def update_settings(payload: SettingsUpdate) -> dict[str, Any]:
    partial = payload.model_dump(exclude_none=True)
    if "mode" in partial:
        validate_mode(partial["mode"])
    updated = config_store.update(partial)

    def mutate(ws) -> None:
        if "mode" in partial and _state_machine is not None:
            _state_machine.set_mode(partial["mode"])
        ws.add_event("settings_changed", "Settings updated")

    world_state.mutate(mutate)
    return updated


@router.get("/state")
def get_state() -> dict[str, Any]:
    return world_state.snapshot()


@router.post("/mode")
def set_mode(payload: ModeRequest) -> dict[str, Any]:
    mode = validate_mode(payload.mode)
    config_store.update({"mode": mode})
    if _state_machine is not None:
        _state_machine.set_mode(mode)
    return {"mode": mode}


@router.post("/alert/dismiss")
def dismiss_alert() -> dict[str, Any]:
    if _state_machine is not None:
        _state_machine.dismiss_alert()
    return {"dismissed": True}


@router.get("/session-summary")
def session_summary() -> dict[str, Any]:
    return world_state.snapshot()["session_summary"]


@router.post("/session/reset")
def reset_session() -> dict[str, Any]:
    from logic.session_tracker import SessionTracker

    tracker = SessionTracker()

    def mutate(ws) -> None:
        tracker.reset(ws)

    world_state.mutate(mutate)
    return world_state.snapshot()["session_summary"]


@router.post("/calibration/screen-zone")
def calibrate_screen_zone(payload: ScreenZoneRequest) -> dict[str, Any]:
    zone = screen_zone_store.set(payload.x1, payload.y1, payload.x2, payload.y2)

    def mutate(ws) -> None:
        ws.add_event("screen_zone_calibrated", "Screen zone calibrated")

    world_state.mutate(mutate)
    return zone
