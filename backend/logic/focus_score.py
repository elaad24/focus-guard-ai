from __future__ import annotations

from logic.world_state import DetectionSignals, FocusState


def clamp(value: float, low: float, high: float) -> int:
    return int(max(low, min(high, round(value))))


def calculate_focus_score(
    distraction_score: int,
    state: FocusState,
    signals: DetectionSignals,
    recent_kb_or_mouse_activity: bool,
    hands_moving: bool,
) -> int:
    if state == FocusState.BREAK_MODE:
        return 70

    if not signals.person_detected:
        return 60

    if distraction_score >= 80:
        return clamp(30 - (distraction_score - 80), 0, 30)

    if distraction_score >= 60:
        return clamp(60 - (distraction_score - 60) * 1.5, 30, 60)

    if distraction_score >= 30:
        return clamp(75 - (distraction_score - 30), 40, 75)

    base = 85
    if recent_kb_or_mouse_activity:
        base += 10
    if hands_moving:
        base += 5
    if state == FocusState.FOCUSED:
        base += 3
    return min(100, base)
