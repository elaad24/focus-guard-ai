from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Any

import cv2
import mediapipe as mp
import numpy as np

from detection.gaze_calibration import GazeCalibration


@dataclass
class FaceAnalysis:
    head_looking_down: bool = False
    looking_away_from_screen: bool = False
    face_bbox: tuple[float, float, float, float] | None = None
    gaze_pitch: float = 0.0
    gaze_yaw: float = 0.0
    eye_aspect_ratio: float = 0.0
    eyes_closed: bool = False
    eyes_closed_duration_seconds: float = 0.0
    eyes_closed_too_long: bool = False
    yawn_detected: bool = False
    frequent_yawns: bool = False
    yawns_in_window: int = 0


class FaceTracker:
    NOSE_TIP = 1
    CHIN = 152
    LEFT_EYE = 33
    RIGHT_EYE = 263

    LEFT_EYE_EAR = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE_EAR = [362, 385, 387, 263, 373, 380]
    MOUTH_TOP = 13
    MOUTH_BOTTOM = 14
    MOUTH_LEFT = 61
    MOUTH_RIGHT = 291

    def __init__(self) -> None:
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._pitch_ema = 0.0
        self._yaw_ema = 0.0
        self._alpha = 0.35
        self._eyes_closed_since: float | None = None
        self._yawn_timestamps: deque[float] = deque()
        self._last_analyzed_at = 0.0

    def analyze(
        self,
        frame: np.ndarray,
        calibration: GazeCalibration | None = None,
        fatigue_config: dict[str, Any] | None = None,
    ) -> FaceAnalysis:
        cfg = fatigue_config or {}
        ear_threshold = float(cfg.get("ear_closed_threshold", 0.2))
        mar_yawn_threshold = float(cfg.get("mar_yawn_threshold", 0.55))
        yawn_window = float(cfg.get("yawn_window_seconds", 90))
        yawns_threshold = int(cfg.get("yawns_in_window_threshold", 3))
        eye_closed_alert = float(cfg.get("eye_closed_alert_seconds", 2.5))

        now = time.monotonic()
        self._last_analyzed_at = now

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._face_mesh.process(rgb)
        if not results.multi_face_landmarks:
            self._pitch_ema *= 0.8
            self._yaw_ema *= 0.8
            self._eyes_closed_since = None
            return FaceAnalysis(gaze_pitch=self._pitch_ema, gaze_yaw=self._yaw_ema)

        landmarks = results.multi_face_landmarks[0].landmark
        h, w = frame.shape[:2]

        def point(idx: int) -> tuple[float, float]:
            lm = landmarks[idx]
            return lm.x * w, lm.y * h

        nose = point(self.NOSE_TIP)
        chin = point(self.CHIN)
        left_eye = point(self.LEFT_EYE)
        right_eye = point(self.RIGHT_EYE)

        pitch = chin[1] - nose[1]
        eye_center_x = (left_eye[0] + right_eye[0]) / 2
        yaw = eye_center_x - (w / 2)

        self._pitch_ema = self._alpha * pitch + (1 - self._alpha) * self._pitch_ema
        self._yaw_ema = self._alpha * yaw + (1 - self._alpha) * self._yaw_ema

        xs = [lm.x * w for lm in landmarks]
        ys = [lm.y * h for lm in landmarks]
        face_bbox = (min(xs), min(ys), max(xs), max(ys))

        head_down = self._pitch_ema > 18
        looking_away = abs(self._yaw_ema) > 45

        if calibration is not None and calibration.is_calibrated:
            head_down, looking_away = self._evaluate_with_calibration(
                calibration,
                face_bbox,
                w,
                h,
            )

        ear = (self._eye_aspect_ratio(landmarks, self.LEFT_EYE_EAR, w, h) +
               self._eye_aspect_ratio(landmarks, self.RIGHT_EYE_EAR, w, h)) / 2.0
        mar = self._mouth_aspect_ratio(landmarks, w, h)

        eyes_closed = ear < ear_threshold
        if eyes_closed:
            if self._eyes_closed_since is None:
                self._eyes_closed_since = now
        else:
            self._eyes_closed_since = None

        eyes_closed_duration = 0.0
        if self._eyes_closed_since is not None:
            eyes_closed_duration = now - self._eyes_closed_since

        eyes_closed_too_long = eyes_closed_duration >= eye_closed_alert

        yawn_detected = mar >= mar_yawn_threshold
        if yawn_detected:
            if not self._yawn_timestamps or (now - self._yawn_timestamps[-1]) > 3.0:
                self._yawn_timestamps.append(now)

        cutoff = now - yawn_window
        while self._yawn_timestamps and self._yawn_timestamps[0] < cutoff:
            self._yawn_timestamps.popleft()

        yawns_in_window = len(self._yawn_timestamps)
        frequent_yawns = yawns_in_window >= yawns_threshold

        return FaceAnalysis(
            head_looking_down=head_down,
            looking_away_from_screen=looking_away,
            face_bbox=face_bbox,
            gaze_pitch=round(self._pitch_ema, 2),
            gaze_yaw=round(self._yaw_ema, 2),
            eye_aspect_ratio=round(ear, 3),
            eyes_closed=eyes_closed,
            eyes_closed_duration_seconds=round(eyes_closed_duration, 2),
            eyes_closed_too_long=eyes_closed_too_long,
            yawn_detected=yawn_detected,
            frequent_yawns=frequent_yawns,
            yawns_in_window=yawns_in_window,
        )

    @staticmethod
    def _eye_aspect_ratio(landmarks, indices: list[int], w: int, h: int) -> float:
        def pt(idx: int) -> np.ndarray:
            lm = landmarks[idx]
            return np.array([lm.x * w, lm.y * h])

        p1, p2, p3, p4, p5, p6 = (pt(i) for i in indices)
        vertical = np.linalg.norm(p2 - p6) + np.linalg.norm(p3 - p5)
        horizontal = np.linalg.norm(p1 - p4)
        if horizontal <= 1e-6:
            return 0.3
        return float(vertical / (2.0 * horizontal))

    @staticmethod
    def _mouth_aspect_ratio(landmarks, w: int, h: int) -> float:
        def pt(idx: int) -> np.ndarray:
            lm = landmarks[idx]
            return np.array([lm.x * w, lm.y * h])

        top = pt(FaceTracker.MOUTH_TOP)
        bottom = pt(FaceTracker.MOUTH_BOTTOM)
        left = pt(FaceTracker.MOUTH_LEFT)
        right = pt(FaceTracker.MOUTH_RIGHT)
        vertical = np.linalg.norm(top - bottom)
        horizontal = np.linalg.norm(left - right)
        if horizontal <= 1e-6:
            return 0.0
        return float(vertical / horizontal)

    def _evaluate_with_calibration(
        self,
        calibration: GazeCalibration,
        face_bbox: tuple[float, float, float, float],
        frame_w: int,
        frame_h: int,
    ) -> tuple[bool, bool]:
        tolerances = calibration.tolerances()
        baseline_pitch = calibration.baseline_pitch or 0.0
        baseline_yaw = calibration.baseline_yaw or 0.0

        pitch_delta = self._pitch_ema - baseline_pitch
        yaw_delta = self._yaw_ema - baseline_yaw

        profile = calibration.workstation_profile or "screens_in_front"

        if profile == "laptop_below":
            head_down = pitch_delta > tolerances.pitch_down_threshold
        else:
            head_down = (
                pitch_delta > tolerances.pitch_down_threshold
                or pitch_delta < -tolerances.pitch_up_threshold
            )

        looking_away = abs(yaw_delta) > tolerances.yaw_away_threshold

        if calibration.focus_zone is not None:
            sx1, sy1, sx2, sy2 = calibration.focus_zone
            face_cx = ((face_bbox[0] + face_bbox[2]) / 2) / frame_w
            face_cy = ((face_bbox[1] + face_bbox[3]) / 2) / frame_h
            in_zone = sx1 <= face_cx <= sx2 and sy1 <= face_cy <= sy2
            if profile == "screens_in_front" and in_zone:
                looking_away = False
            elif not in_zone:
                looking_away = True

        return head_down, looking_away

    def health(self) -> dict[str, Any]:
        return {"face_tracker_ok": True}
