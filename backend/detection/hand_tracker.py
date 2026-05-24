from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

import cv2
import mediapipe as mp
import numpy as np


@dataclass
class HandAnalysis:
    hand_bboxes: list[tuple[float, float, float, float]]
    body_hand_idle: bool


class HandTracker:
    def __init__(self, idle_window: int = 15, motion_threshold: float = 8.0) -> None:
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._motion_history: deque[float] = deque(maxlen=idle_window)
        self._motion_threshold = motion_threshold
        self._last_centers: list[tuple[float, float]] = []

    def analyze(self, frame: np.ndarray) -> HandAnalysis:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb)
        h, w = frame.shape[:2]
        hand_bboxes: list[tuple[float, float, float, float]] = []
        centers: list[tuple[float, float]] = []

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                xs = [lm.x * w for lm in hand_landmarks.landmark]
                ys = [lm.y * h for lm in hand_landmarks.landmark]
                bbox = (min(xs), min(ys), max(xs), max(ys))
                hand_bboxes.append(bbox)
                centers.append(((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2))

        motion = self._compute_motion(centers)
        self._motion_history.append(motion)
        self._last_centers = centers

        avg_motion = float(np.mean(self._motion_history)) if self._motion_history else 0.0
        body_hand_idle = avg_motion < self._motion_threshold

        return HandAnalysis(hand_bboxes=hand_bboxes, body_hand_idle=body_hand_idle)

    def _compute_motion(self, centers: list[tuple[float, float]]) -> float:
        if not centers or not self._last_centers:
            return 0.0
        total = 0.0
        count = min(len(centers), len(self._last_centers))
        for idx in range(count):
            cx, cy = centers[idx]
            lx, ly = self._last_centers[idx]
            total += float(np.hypot(cx - lx, cy - ly))
        return total / max(count, 1)

    def health(self) -> dict[str, Any]:
        return {"hand_tracker_ok": True}
