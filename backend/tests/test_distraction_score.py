from __future__ import annotations

from logic.distraction_score import (
    GAZE_IDLE_CONTRIBUTORS,
    calculate_distraction_score,
    _mode_weights,
)
from logic.world_state import DetectionSignals


def _signals(**overrides: bool) -> DetectionSignals:
    base = DetectionSignals(person_detected=True)
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


DEFAULT_CONFIG = {
    "phoneUsageLimitSeconds": 90,
    "fatigueScoreWeight": 25,
}


def test_no_person_returns_zero_with_marker() -> None:
    result = calculate_distraction_score(
        DetectionSignals(person_detected=False),
        "normal",
        DEFAULT_CONFIG,
    )
    assert result.distraction_score == 0
    assert result.contributors == ["no_person_detected"]


def test_phone_near_person_adds_weight() -> None:
    result = calculate_distraction_score(
        _signals(phone_near_person=True),
        "normal",
        DEFAULT_CONFIG,
    )
    assert result.distraction_score == 40
    assert "phone_near_person" in result.contributors


def test_recent_input_activity_suppresses_gaze_idle_signals() -> None:
    result = calculate_distraction_score(
        _signals(
            head_looking_down=True,
            looking_away_from_screen=True,
            keyboard_mouse_idle=True,
            body_hand_idle=True,
        ),
        "normal",
        DEFAULT_CONFIG,
        recent_input_activity=True,
    )
    assert result.distraction_score == 0
    assert not any(c in GAZE_IDLE_CONTRIBUTORS for c in result.contributors)


def test_reading_meeting_mode_ignores_head_and_looking_away() -> None:
    result = calculate_distraction_score(
        _signals(
            head_looking_down=True,
            looking_away_from_screen=True,
        ),
        "reading_meeting",
        DEFAULT_CONFIG,
    )
    assert result.distraction_score == 0


def test_ipad_mode_tablet_reduction() -> None:
    result = calculate_distraction_score(
        _signals(
            tablet_detected=True,
            tablet_mode_active=True,
            head_looking_down=True,
        ),
        "ipad",
        DEFAULT_CONFIG,
    )
    assert "tablet_mode_reduction" in result.contributors
    assert result.distraction_score < 20


def test_mode_weights_video_lesson_reduces_looking_away() -> None:
    weights = _mode_weights("video_lesson")
    assert weights["looking_away"] < weights["phone_near_person"]
