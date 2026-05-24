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
from detection.face_tracker import FaceTracker
from detection.hand_tracker import HandTracker
from detection.screen_zone import screen_zone_store
from detection.yolo_detector import YoloDetector
from logic.config_store import config_store
from logic.mode_rules import apply_mode_to_signals
from logic.state_machine import StateMachine
from logic.world_state import DetectionSignals, world_state

camera = CameraCapture()
yolo = YoloDetector()
face_tracker = FaceTracker()
hand_tracker = HandTracker()
kb_mouse = KeyboardMouseMonitor()
active_window = ActiveWindowMonitor()
sound_alert = SoundAlert()
notification_alert = NotificationAlert()
state_machine = StateMachine(
    sound_alert=sound_alert,
    notification_alert=notification_alert,
    get_idle_seconds=kb_mouse.seconds_since_last_input,
    get_recent_activity=lambda: kb_mouse.had_recent_activity(within_seconds=5.0),
)

_detection_running = False
_detection_thread: threading.Thread | None = None


def _detection_loop() -> None:
    global _detection_running
    while _detection_running:
        frame = camera.get_frame()
        config = config_store.get()
        mode = config.get("mode", "normal")
        screen_zone = screen_zone_store.get()

        if frame is None:
            time.sleep(0.1)
            continue

        yolo_result = yolo.detect(frame)
        face_result = face_tracker.analyze(frame, screen_zone)
        hand_result = hand_tracker.analyze(frame)

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
            tablet_mode_active=mode == "ipad",
            break_mode_active=mode == "break",
            video_lesson_mode_active=mode == "video_lesson",
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

        world_state.mutate(mutate)
        time.sleep(1.0 / 15.0)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    bind_runtime(state_machine, camera, yolo, kb_mouse, sound_alert)

    def mutate(ws) -> None:
        ws.mode = config_store.get().get("mode", "normal")
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
    stop_broadcaster()
    state_machine.stop()
    kb_mouse.stop()
    active_window.stop()
    camera.stop()
    sound_alert.stop_loop()


app = FastAPI(title="Focus Guard AI", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.websocket("/ws/status")(websocket_status_handler)
