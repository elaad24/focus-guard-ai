from __future__ import annotations

from unittest.mock import MagicMock

from logic.state_machine import StateMachine
from logic.world_state import FocusState, WorldState


def _make_state_machine() -> StateMachine:
    sound = MagicMock()
    sound.ok = True
    notification = MagicMock()
    return StateMachine(
        sound_alert=sound,
        notification_alert=notification,
        get_idle_seconds=lambda: 0.0,
        get_recent_activity=lambda: False,
    )


DEFAULT_CONFIG = {
    "procrastinationScoreThreshold": 70,
    "softWarningAfterSeconds": 45,
    "mediumWarningAfterSeconds": 60,
    "finalAlertAfterSeconds": 90,
    "fatigueSoftWarningAfterSeconds": 15,
    "soundEnabled": True,
    "notificationsEnabled": True,
    "cooldownAfterDismissSeconds": 120,
}


def _distracted_world(now: float, seconds_above: float) -> WorldState:
    ws = WorldState()
    ws.mode = "normal"
    ws.distraction_score = 80
    ws.distraction_contributors = ["phone_near_person"]
    ws.signals.phone_near_person = True
    ws.signals.person_detected = True
    ws.above_threshold_since = now - seconds_above
    ws.time_above_threshold_seconds = seconds_above
    return ws


def test_soft_warning_after_threshold_time() -> None:
    sm = _make_state_machine()
    now = 1000.0
    ws = _distracted_world(now, 46.0)

    sm._update_state(ws, DEFAULT_CONFIG, now)

    assert ws.state == FocusState.DISTRACTION_WARNING_SOFT
    assert ws.warning_stage == "soft"


def test_medium_warning_after_threshold_time() -> None:
    sm = _make_state_machine()
    now = 1000.0
    ws = _distracted_world(now, 61.0)

    sm._update_state(ws, DEFAULT_CONFIG, now)

    assert ws.state == FocusState.DISTRACTION_WARNING_MEDIUM
    assert ws.warning_stage == "medium"


def test_final_alert_after_threshold_time() -> None:
    sm = _make_state_machine()
    now = 1000.0
    ws = _distracted_world(now, 91.0)

    sm._update_state(ws, DEFAULT_CONFIG, now)

    assert ws.state == FocusState.ALERT_ACTIVE
    assert ws.alert_active is True
    assert ws.warning_stage == "final"


def test_break_mode_disables_alerts() -> None:
    sm = _make_state_machine()
    now = 1000.0
    ws = _distracted_world(now, 120.0)
    ws.mode = "break"

    sm._update_state(ws, DEFAULT_CONFIG, now)

    assert ws.state == FocusState.BREAK_MODE
    assert ws.alert_active is False
    assert ws.warning_stage == "break"


def test_snooze_suppresses_warnings() -> None:
    sm = _make_state_machine()
    now = 1000.0
    ws = _distracted_world(now, 120.0)
    ws.snooze_until = now + 300

    sm._update_state(ws, DEFAULT_CONFIG, now)

    assert ws.state == FocusState.SNOOZED
    assert ws.warning_stage == "snooze"
    assert ws.alert_active is False


def test_start_snooze_sets_state() -> None:
    sm = _make_state_machine()
    sm.start_snooze(900.0)

    from logic.world_state import world_state

    ws = world_state.read()
    assert ws.state == FocusState.SNOOZED
    assert ws.snooze_until is not None
    sm.cancel_snooze()
