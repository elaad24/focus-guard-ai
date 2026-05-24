from __future__ import annotations

from dataclasses import dataclass

from logic.world_state import DetectionSignals, FocusState


def clamp(value: float, low: float, high: float) -> int:
    return int(max(low, min(high, round(value))))


@dataclass
class FocusScoreResult:
    focus_score: int
    contributors: list[str]


def _has_phone_signals(signals: DetectionSignals) -> bool:
    return (
        signals.phone_near_person
        or signals.phone_near_hand_or_face
        or signals.phone_detected
    )


def calculate_focus_score(
    distraction_score: int,
    state: FocusState,
    signals: DetectionSignals,
    recent_kb_or_mouse_activity: bool,
    hands_moving: bool,
) -> FocusScoreResult:
    contributors: list[str] = []

    if state == FocusState.BREAK_MODE:
        return FocusScoreResult(focus_score=70, contributors=["break_mode"])

    if not signals.person_detected:
        return FocusScoreResult(focus_score=60, contributors=["person_not_visible"])

    if recent_kb_or_mouse_activity and not _has_phone_signals(signals):
        contributors.append("active_working_input")
        base = max(85, 100 - distraction_score // 4)
        if hands_moving:
            contributors.append("hands_moving")
            base = min(100, base + 3)
        if state == FocusState.FOCUSED:
            contributors.append("focused_state")
            base = min(100, base + 2)
        return FocusScoreResult(focus_score=base, contributors=contributors)

    if distraction_score >= 80:
        return FocusScoreResult(
            focus_score=clamp(30 - (distraction_score - 80), 0, 30),
            contributors=["high_distraction"],
        )

    if distraction_score >= 60:
        return FocusScoreResult(
            focus_score=clamp(60 - (distraction_score - 60) * 1.5, 30, 60),
            contributors=["elevated_distraction"],
        )

    if distraction_score >= 30:
        return FocusScoreResult(
            focus_score=clamp(75 - (distraction_score - 30), 40, 75),
            contributors=["mild_distraction"],
        )

    base = 85
    if recent_kb_or_mouse_activity:
        base += 10
        contributors.append("active_typing_or_mouse")
    if hands_moving:
        base += 5
        contributors.append("hands_moving")
    if state == FocusState.FOCUSED:
        base += 3
        contributors.append("focused_state")

    if not contributors:
        contributors.append("baseline_focus")

    return FocusScoreResult(focus_score=min(100, base), contributors=contributors)
