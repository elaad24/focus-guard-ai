from __future__ import annotations

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


class FaceTracker:
    NOSE_TIP = 1
    CHIN = 152
    LEFT_EYE = 33
    RIGHT_EYE = 263

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

    def analyze(self, frame: np.ndarray, calibration: GazeCalibration | None = None) -> FaceAnalysis:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._face_mesh.process(rgb)
        if not results.multi_face_landmarks:
            self._pitch_ema *= 0.8
            self._yaw_ema *= 0.8
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

        return FaceAnalysis(
            head_looking_down=head_down,
            looking_away_from_screen=looking_away,
            face_bbox=face_bbox,
            gaze_pitch=round(self._pitch_ema, 2),
            gaze_yaw=round(self._yaw_ema, 2),
        )

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
