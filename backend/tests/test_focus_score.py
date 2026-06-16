from __future__ import annotations

from logic.focus_score import calculate_focus_score
from logic.world_state import DetectionSignals, FocusState


def test_break_mode_returns_neutral_focus_score() -> None:
    result = calculate_focus_score(
        distraction_score=90,
        state=FocusState.BREAK_MODE,
        signals=DetectionSignals(person_detected=True),
        recent_kb_or_mouse_activity=False,
        hands_moving=False,
    )
    assert result.focus_score == 70
    assert result.contributors == ["break_mode"]


def test_active_input_without_phone_boosts_focus() -> None:
    result = calculate_focus_score(
        distraction_score=20,
        state=FocusState.FOCUSED,
        signals=DetectionSignals(person_detected=True),
        recent_kb_or_mouse_activity=True,
        hands_moving=True,
    )
    assert result.focus_score >= 85
    assert "active_working_input" in result.contributors


def test_high_distraction_caps_focus_score() -> None:
    result = calculate_focus_score(
        distraction_score=95,
        state=FocusState.DISTRACTED,
        signals=DetectionSignals(person_detected=True),
        recent_kb_or_mouse_activity=False,
        hands_moving=False,
    )
    assert result.focus_score <= 30
    assert "high_distraction" in result.contributors
