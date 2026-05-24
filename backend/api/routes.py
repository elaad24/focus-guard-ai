from __future__ import annotations

from typing import Any

import cv2
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from detection.gaze_calibration import gaze_calibration_store
from logic.config_store import config_store
from logic.mode_rules import validate_mode
from logic.world_state import world_state
from system.metrics import get_backend_resources

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


class GazeProfileRequest(BaseModel):
    workstationProfile: str


class GazePoseSample(BaseModel):
    pitch: float
    yaw: float


class GazePoseRequest(BaseModel):
    samples: list[GazePoseSample] = Field(min_length=1)


class SettingsUpdate(BaseModel):
    mode: str | None = None
    softWarningAfterSeconds: int | None = Field(default=None, ge=5, le=600)
    mediumWarningAfterSeconds: int | None = Field(default=None, ge=5, le=600)
    finalAlertAfterSeconds: int | None = Field(default=None, ge=5, le=600)
    phoneUsageLimitSeconds: int | None = Field(default=None, ge=5, le=600)
    keyboardMouseIdleLimitSeconds: int | None = Field(default=None, ge=5, le=600)
    procrastinationScoreThreshold: int | None = Field(default=None, ge=0, le=100)
    cooldownAfterDismissSeconds: int | None = Field(default=None, ge=0, le=3600)
    inputActivityFocusWindowSeconds: int | None = Field(default=None, ge=1, le=120)
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

    config = config_store.get()
    if config.get("mode") == "break":
        return {"accepted": False, "skipped": True}

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
    resources = get_backend_resources()
    return {
        "backend": "ok",
        "camera": "ok" if snapshot.get("camera_ok") else "error",
        "model": "ok" if snapshot.get("model_ok") else "error",
        "keyboard_mouse": "ok" if snapshot.get("kb_mouse_ok") else "error",
        "websocket": "ok",
        "alert_system": "ok" if snapshot.get("alert_system_ok") else "error",
        "fps": snapshot.get("fps", 0),
        "mode": snapshot.get("mode", "normal"),
        **resources,
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


@router.get("/calibration/gaze")
def get_gaze_calibration() -> dict[str, Any]:
    return gaze_calibration_store.get().to_dict()


@router.post("/calibration/gaze/profile")
def set_gaze_profile(payload: GazeProfileRequest) -> dict[str, Any]:
    try:
        result = gaze_calibration_store.set_profile(payload.workstationProfile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    def mutate(ws) -> None:
        ws.gaze_calibrated = gaze_calibration_store.get().is_calibrated
        ws.workstation_profile = payload.workstationProfile
        ws.add_event("gaze_profile_set", f"Workstation profile set to {payload.workstationProfile}")

    world_state.mutate(mutate)
    return result


@router.post("/calibration/gaze/pose")
def set_gaze_pose(payload: GazePoseRequest) -> dict[str, Any]:
    try:
        samples = [s.model_dump() for s in payload.samples]
        result = gaze_calibration_store.set_pose_baseline(samples)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    def mutate(ws) -> None:
        cal = gaze_calibration_store.get()
        ws.gaze_calibrated = cal.is_calibrated
        ws.workstation_profile = cal.workstation_profile
        ws.add_event("gaze_calibrated", "Workstation gaze calibration completed")

    world_state.mutate(mutate)
    return result


@router.post("/calibration/gaze/reset")
def reset_gaze_calibration() -> dict[str, Any]:
    result = gaze_calibration_store.reset()

    def mutate(ws) -> None:
        ws.gaze_calibrated = False
        ws.workstation_profile = None
        ws.add_event("gaze_calibration_reset", "Gaze calibration reset")

    world_state.mutate(mutate)
    return result


@router.post("/calibration/screen-zone")
def calibrate_screen_zone(payload: ScreenZoneRequest) -> dict[str, Any]:
    from detection.screen_zone import screen_zone_store

    zone = screen_zone_store.set(payload.x1, payload.y1, payload.x2, payload.y2)

    def mutate(ws) -> None:
        ws.add_event("screen_zone_calibrated", "Screen zone calibrated")

    world_state.mutate(mutate)
    return zone
