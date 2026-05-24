from __future__ import annotations

import os
import sys
import threading
import time
from typing import Any, Literal

import cv2
import numpy as np

# Camera frames are kept in RAM only. This module never writes images or video to disk.

CameraSource = Literal["browser", "opencv"]

_STALE_FRAME_SECONDS = 8.0
_MAX_JPEG_BYTES = 2 * 1024 * 1024

def _resolve_source(source: CameraSource | None) -> CameraSource:
    if source is not None:
        return source
    configured = os.getenv("FOCUS_GUARD_CAMERA_SOURCE", "browser").strip().lower()
    return "opencv" if configured == "opencv" else "browser"


class CameraCapture:
    def __init__(
        self,
        device_index: int = 0,
        target_fps: float = 15.0,
        source: CameraSource | None = None,
    ) -> None:
        self._device_index = device_index
        self._target_fps = target_fps
        self._source = _resolve_source(source)
        self._lock = threading.Lock()
        self._latest_frame: np.ndarray | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._capture: cv2.VideoCapture | None = None
        self._fps = 0.0
        self._ok = False
        self._frame_count = 0
        self._fps_window_start = time.monotonic()
        self._last_frame_at = 0.0

    @property
    def source(self) -> CameraSource:
        return self._source

    @property
    def ok(self) -> bool:
        if self._source == "browser":
            if self._last_frame_at <= 0:
                return False
            return (time.monotonic() - self._last_frame_at) <= _STALE_FRAME_SECONDS
        return self._ok

    @property
    def fps(self) -> float:
        return self._fps

    def start(self) -> None:
        if self._source != "opencv" or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="camera-capture")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def get_frame(self) -> np.ndarray | None:
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def submit_browser_frame(self, jpeg_bytes: bytes) -> bool:
        if self._source != "browser":
            return False
        if len(jpeg_bytes) == 0 or len(jpeg_bytes) > _MAX_JPEG_BYTES:
            return False

        encoded = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if frame is None:
            return False

        now = time.monotonic()
        with self._lock:
            self._latest_frame = frame
            self._last_frame_at = now
            self._frame_count += 1
            elapsed = now - self._fps_window_start
            if elapsed >= 1.0:
                self._fps = self._frame_count / elapsed
                self._frame_count = 0
                self._fps_window_start = now

        return True

    def _store_frame(self, frame: np.ndarray) -> None:
        with self._lock:
            self._latest_frame = frame

        self._frame_count += 1
        elapsed = time.monotonic() - self._fps_window_start
        if elapsed >= 1.0:
            self._fps = self._frame_count / elapsed
            self._frame_count = 0
            self._fps_window_start = time.monotonic()

    def _open_capture(self) -> cv2.VideoCapture:
        if sys.platform == "darwin":
            return cv2.VideoCapture(self._device_index, cv2.CAP_AVFOUNDATION)
        return cv2.VideoCapture(self._device_index)

    def _loop(self) -> None:
        self._capture = self._open_capture()
        self._ok = self._capture.isOpened()
        frame_interval = 1.0 / self._target_fps

        while self._running:
            loop_start = time.monotonic()
            if self._capture is None or not self._capture.isOpened():
                self._ok = False
                time.sleep(0.5)
                continue

            ok, frame = self._capture.read()
            if not ok or frame is None:
                self._ok = False
                time.sleep(0.1)
                continue

            self._ok = True
            self._store_frame(frame)

            sleep_for = frame_interval - (time.monotonic() - loop_start)
            if sleep_for > 0:
                time.sleep(sleep_for)

    def health(self) -> dict[str, Any]:
        return {
            "camera_ok": self.ok,
            "fps": round(self._fps, 1),
            "source": self._source,
        }
