from __future__ import annotations

import threading
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from activity.active_window_monitor import ActiveWindowMonitor
from activity.keyboard_mouse_monitor import KeyboardMouseMonitor
from alerts.notification_alert import NotificationAlert
from alerts.sound_alert import SoundAlert
from api.routes import bind_runtime, router
from api.websocket import start_broadcaster, stop_broadcaster, websocket_status_handler
from detection.camera import CameraCapture
from detection.face_tracker import FaceAnalysis, FaceTracker
from detection.frame_utils import downscale_for_inference
from detection.gaze_calibration import gaze_calibration_store
from detection.hand_tracker import HandAnalysis, HandTracker
from detection.yolo_detector import YoloDetector
from logic.config_store import config_store
from logic.mode_rules import apply_mode_to_signals
from logic.state_machine import StateMachine
from logic.world_state import DetectionSignals, world_state
from storage.history_store import history_store

camera = CameraCapture()
yolo = YoloDetector()
face_tracker = FaceTracker()
hand_tracker = HandTracker()
kb_mouse = KeyboardMouseMonitor()
active_window = ActiveWindowMonitor(poll_interval=4.0)
sound_alert = SoundAlert()
notification_alert = NotificationAlert()
state_machine = StateMachine(
    sound_alert=sound_alert,
    notification_alert=notification_alert,
    get_idle_seconds=kb_mouse.seconds_since_last_input,
    get_recent_activity=lambda: kb_mouse.had_recent_activity(
        within_seconds=float(config_store.get().get("inputActivityFocusWindowSeconds", 10)),
    ),
)

_detection_running = False
_detection_thread: threading.Thread | None = None
_last_processed_generation = 0
_new_frame_counter = 0
_last_hand_result = HandAnalysis(hand_bboxes=[], body_hand_idle=True)


def _idle_sleep_seconds() -> float:
    return 0.35 if camera.source == "browser" else 0.05


def _loop_sleep_seconds() -> float:
    return 1.0 / 15.0 if camera.source == "opencv" else 0.5


def _fatigue_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "ear_closed_threshold": float(config.get("earClosedThreshold", 0.2)),
        "mar_yawn_threshold": float(config.get("marYawnThreshold", 0.55)),
        "yawn_window_seconds": float(config.get("yawnWindowSeconds", 90)),
        "yawns_in_window_threshold": int(config.get("yawnsInWindowThreshold", 3)),
        "eye_closed_alert_seconds": float(config.get("eyeClosedAlertSeconds", 2.5)),
    }


def _run_detection_on_frame(
    frame,
    mode: str,
    gaze_calibration,
    fatigue_cfg: dict[str, Any],
    run_hands: bool,
) -> tuple[DetectionSignals, FaceAnalysis]:
    global _last_hand_result

    inference_frame = downscale_for_inference(frame)
    yolo_result = yolo.detect(inference_frame)
    face_result = face_tracker.analyze(inference_frame, gaze_calibration, fatigue_cfg)

    if run_hands:
        hand_result = hand_tracker.analyze(inference_frame)
        _last_hand_result = hand_result
    else:
        hand_result = _last_hand_result

    phone_near_hand = yolo.phone_near_hand_or_face(
        yolo_result["phones"],
        hand_result.hand_bboxes,
        face_result.face_bbox,
    )

    signals = DetectionSignals(
        person_detected=len(yolo_result["persons"]) > 0,
        phone_detected=len(yolo_result["phones"]) > 0,
        phone_near_person=yolo_result["phone_near_person"],
        phone_near_hand_or_face=phone_near_hand,
        head_looking_down=face_result.head_looking_down,
        looking_away_from_screen=face_result.looking_away_from_screen,
        keyboard_mouse_idle=False,
        body_hand_idle=hand_result.body_hand_idle,
        tablet_detected=yolo_result["tablet_detected"],
        tablet_near_person=yolo_result.get("tablet_near_person", False),
        tablet_mode_active=mode == "ipad",
        break_mode_active=False,
        video_lesson_mode_active=mode == "video_lesson",
        eyes_closed=face_result.eyes_closed,
        frequent_yawns=face_result.frequent_yawns,
        eyes_closed_too_long=face_result.eyes_closed_too_long,
    )
    return signals, face_result


def _detection_loop() -> None:
    global _detection_running, _last_processed_generation, _new_frame_counter

    while _detection_running:
        config = config_store.get()
        mode = config.get("mode", "normal")

        if mode == "break":
            def mutate_break(ws) -> None:
                ws.mode = mode
                ws.signals = DetectionSignals(break_mode_active=True)
                ws.fps = 0.0
                ws.camera_ok = False
                ws.model_ok = yolo.ok
                ws.kb_mouse_ok = kb_mouse.ok
                ws.alert_system_ok = sound_alert.ok
                ws.active_window = active_window.get()
                ws.fatigue_active = False

            world_state.mutate(mutate_break)
            time.sleep(0.5)
            continue

        frame_result = camera.get_frame_for_detection(_last_processed_generation)
        if frame_result is None:
            if camera.frame_generation == 0:
                time.sleep(0.1)
            else:
                time.sleep(_idle_sleep_seconds())
            continue

        frame, generation = frame_result
        _last_processed_generation = generation
        _new_frame_counter += 1
        gaze_calibration = gaze_calibration_store.get()
        fatigue_cfg = _fatigue_config(config)
        run_hands = _new_frame_counter % 2 == 1

        signals, face_result = _run_detection_on_frame(
            frame,
            mode,
            gaze_calibration,
            fatigue_cfg,
            run_hands,
        )

        def mutate(ws) -> None:
            ws.mode = mode
            ws.signals = signals
            ws.fps = camera.fps
            ws.camera_ok = camera.ok
            ws.model_ok = yolo.ok
            ws.kb_mouse_ok = kb_mouse.ok
            ws.alert_system_ok = sound_alert.ok
            ws.active_window = active_window.get()
            ws.gaze_pitch = face_result.gaze_pitch
            ws.gaze_yaw = face_result.gaze_yaw
            ws.gaze_calibrated = gaze_calibration.is_calibrated
            ws.workstation_profile = gaze_calibration.workstation_profile
            ws.fatigue_active = signals.frequent_yawns or signals.eyes_closed_too_long

        world_state.mutate(mutate)
        time.sleep(_loop_sleep_seconds())


@asynccontextmanager
async def lifespan(_app: FastAPI):
    bind_runtime(state_machine, camera, yolo, kb_mouse, sound_alert)

    def mutate(ws) -> None:
        ws.mode = config_store.get().get("mode", "normal")
        cal = gaze_calibration_store.get()
        ws.gaze_calibrated = cal.is_calibrated
        ws.workstation_profile = cal.workstation_profile
        ws.add_event("app_started", "Focus Guard AI started")
        if camera.source == "browser":
            ws.add_event("camera_browser_mode", "Waiting for browser camera feed")
        elif camera.ok:
            ws.add_event("camera_connected", "Camera connected")
        if yolo.ok:
            ws.add_event("model_loaded", "YOLO model loaded")

    world_state.mutate(mutate)

    camera.start()
    kb_mouse.start()
    active_window.start()
    state_machine.start()
    start_broadcaster()

    global _detection_running, _detection_thread
    _detection_running = True
    _detection_thread = threading.Thread(target=_detection_loop, daemon=True, name="detection-loop")
    _detection_thread.start()

    yield

    _detection_running = False
    if _detection_thread and _detection_thread.is_alive():
        _detection_thread.join(timeout=2.0)
    await stop_broadcaster()
    history_store.save(world_state.read().session, "shutdown")
    state_machine.stop()
    kb_mouse.stop()
    active_window.stop()
    camera.stop()
    sound_alert.stop_loop()


app = FastAPI(title="Focus Guard AI", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5700",
        "http://127.0.0.1:5700",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.websocket("/ws/status")(websocket_status_handler)
