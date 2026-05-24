from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from logic.world_state import DetectionSignals

PHONE_NEAR_PERSON = 40
PHONE_NEAR_HAND_OR_FACE = 30
HEAD_DOWN = 20
LOOKING_AWAY = 15
KB_MOUSE_IDLE_OVER_LIMIT = 20
BODY_HAND_IDLE_OVER_LIMIT = 10
TABLET_REDUCTION_IF_IPAD_MODE = -25


@dataclass
class ScoreResult:
    distraction_score: int
    contributors: list[str]


def calculate_distraction_score(
    signals: DetectionSignals,
    mode: str,
    config: dict[str, Any],
    phone_near_seconds: float = 0.0,
) -> ScoreResult:
    if not signals.person_detected:
        return ScoreResult(distraction_score=0, contributors=["no_person_detected"])

    contributors: list[str] = []
    score = 0.0

    weights = _mode_weights(mode)

    if signals.phone_near_person:
        score += PHONE_NEAR_PERSON * weights["phone_near_person"]
        contributors.append("phone_near_person")

    phone_limit = float(config.get("phoneUsageLimitSeconds", 90))
    if phone_near_seconds >= phone_limit and signals.phone_near_person:
        score += 15
        contributors.append("phone_usage_over_limit")

    if signals.phone_near_hand_or_face:
        score += PHONE_NEAR_HAND_OR_FACE * weights["phone_near_hand_or_face"]
        contributors.append("phone_near_hand_or_face")

    if signals.head_looking_down:
        if not (mode == "ipad" and signals.tablet_detected):
            score += HEAD_DOWN * weights["head_down"]
            contributors.append("head_looking_down")

    if signals.looking_away_from_screen:
        if mode != "video_lesson":
            score += LOOKING_AWAY * weights["looking_away"]
            contributors.append("looking_away_from_screen")

    idle_limit = float(config.get("keyboardMouseIdleLimitSeconds", 60))
    if signals.keyboard_mouse_idle:
        score += KB_MOUSE_IDLE_OVER_LIMIT * weights["kb_idle"]
        contributors.append("keyboard_mouse_idle")

    if signals.body_hand_idle and signals.keyboard_mouse_idle:
        score += BODY_HAND_IDLE_OVER_LIMIT * weights["body_idle"]
        contributors.append("body_hand_idle")

    if mode == "ipad" and signals.tablet_detected and signals.tablet_mode_active:
        score += TABLET_REDUCTION_IF_IPAD_MODE
        contributors.append("tablet_mode_reduction")

    if mode == "break":
        score = max(0, score * 0.2)

    distraction = int(max(0, min(100, round(score))))
    return ScoreResult(distraction_score=distraction, contributors=contributors)


def _mode_weights(mode: str) -> dict[str, float]:
    if mode == "video_lesson":
        return {
            "phone_near_person": 1.0,
            "phone_near_hand_or_face": 1.0,
            "head_down": 0.5,
            "looking_away": 0.2,
            "kb_idle": 0.25,
            "body_idle": 0.5,
        }
    if mode == "ipad":
        return {
            "phone_near_person": 1.0,
            "phone_near_hand_or_face": 1.0,
            "head_down": 0.3,
            "looking_away": 0.5,
            "kb_idle": 0.3,
            "body_idle": 0.4,
        }
    if mode == "break":
        return {
            "phone_near_person": 0.2,
            "phone_near_hand_or_face": 0.2,
            "head_down": 0.2,
            "looking_away": 0.2,
            "kb_idle": 0.2,
            "body_idle": 0.2,
        }
    return {
        "phone_near_person": 1.0,
        "phone_near_hand_or_face": 1.0,
        "head_down": 1.0,
        "looking_away": 1.0,
        "kb_idle": 1.0,
        "body_idle": 1.0,
    }
