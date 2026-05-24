from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FocusState(str, Enum):
    FOCUSED = "FOCUSED"
    DISTRACTED = "DISTRACTED"
    DISTRACTION_WARNING_SOFT = "DISTRACTION_WARNING_SOFT"
    DISTRACTION_WARNING_MEDIUM = "DISTRACTION_WARNING_MEDIUM"
    ALERT_ACTIVE = "ALERT_ACTIVE"
    DISMISSED_COOLDOWN = "DISMISSED_COOLDOWN"
    BREAK_MODE = "BREAK_MODE"


@dataclass
class DetectionSignals:
    person_detected: bool = False
    phone_detected: bool = False
    phone_near_person: bool = False
    phone_near_hand_or_face: bool = False
    head_looking_down: bool = False
    looking_away_from_screen: bool = False
    keyboard_mouse_idle: bool = False
    body_hand_idle: bool = False
    tablet_detected: bool = False
    tablet_near_person: bool = False
    tablet_mode_active: bool = False
    break_mode_active: bool = False
    video_lesson_mode_active: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "person_detected": self.person_detected,
            "phone_detected": self.phone_detected,
            "phone_near_person": self.phone_near_person,
            "phone_near_hand_or_face": self.phone_near_hand_or_face,
            "head_looking_down": self.head_looking_down,
            "looking_away_from_screen": self.looking_away_from_screen,
            "keyboard_mouse_idle": self.keyboard_mouse_idle,
            "body_hand_idle": self.body_hand_idle,
            "tablet_detected": self.tablet_detected,
            "tablet_near_person": self.tablet_near_person,
            "tablet_mode_active": self.tablet_mode_active,
            "break_mode_active": self.break_mode_active,
            "video_lesson_mode_active": self.video_lesson_mode_active,
        }


@dataclass
class SessionSummary:
    session_start_time: float = field(default_factory=time.time)
    total_monitored_seconds: float = 0.0
    focused_time_seconds: float = 0.0
    distracted_time_seconds: float = 0.0
    soft_warnings: int = 0
    medium_warnings: int = 0
    final_alerts: int = 0
    dismissals: int = 0
    total_phone_detected_seconds: float = 0.0
    longest_focused_streak_seconds: float = 0.0
    longest_distraction_streak_seconds: float = 0.0
    most_common_trigger: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_start_time": self.session_start_time,
            "total_monitored_seconds": round(self.total_monitored_seconds, 1),
            "focused_time_seconds": round(self.focused_time_seconds, 1),
            "distracted_time_seconds": round(self.distracted_time_seconds, 1),
            "soft_warnings": self.soft_warnings,
            "medium_warnings": self.medium_warnings,
            "final_alerts": self.final_alerts,
            "dismissals": self.dismissals,
            "total_phone_detected_seconds": round(self.total_phone_detected_seconds, 1),
            "longest_focused_streak_seconds": round(self.longest_focused_streak_seconds, 1),
            "longest_distraction_streak_seconds": round(self.longest_distraction_streak_seconds, 1),
            "most_common_trigger": self.most_common_trigger,
        }


@dataclass
class WorldState:
    state: FocusState = FocusState.FOCUSED
    mode: str = "normal"
    focus_score: int = 85
    distraction_score: int = 0
    distraction_contributors: list[str] = field(default_factory=list)
    focus_contributors: list[str] = field(default_factory=list)
    signals: DetectionSignals = field(default_factory=DetectionSignals)
    keyboard_mouse_idle_seconds: float = 0.0
    time_above_threshold_seconds: float = 0.0
    warning_stage: str = "none"
    alert_active: bool = False
    cooldown_remaining_seconds: float = 0.0
    fps: float = 0.0
    camera_ok: bool = False
    model_ok: bool = False
    kb_mouse_ok: bool = False
    alert_system_ok: bool = False
    active_window: dict[str, str] = field(default_factory=dict)
    session: SessionSummary = field(default_factory=SessionSummary)
    events: list[dict[str, Any]] = field(default_factory=list)
    above_threshold_since: float | None = None
    below_threshold_since: float | None = None
    cooldown_until: float | None = None
    trigger_counts: dict[str, int] = field(default_factory=dict)
    current_focus_streak: float = 0.0
    current_distraction_streak: float = 0.0
    phone_near_since: float | None = None
    last_distraction_score: int = 0
    last_distraction_contributors: list[str] = field(default_factory=list)
    last_person_detected_at: float | None = None
    gaze_pitch: float = 0.0
    gaze_yaw: float = 0.0
    gaze_calibrated: bool = False
    workstation_profile: str | None = None
    recent_input_activity: bool = False
    input_activity_override_active: bool = False

    def add_event(self, event_type: str, message: str) -> None:
        entry = {
            "type": event_type,
            "message": message,
            "timestamp": time.time(),
        }
        self.events.insert(0, entry)
        self.events = self.events[:100]

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "mode": self.mode,
            "focus_score": self.focus_score,
            "distraction_score": self.distraction_score,
            "distraction_contributors": self.distraction_contributors,
            "focus_contributors": self.focus_contributors,
            "signals": self.signals.to_dict(),
            "keyboard_mouse_idle_seconds": round(self.keyboard_mouse_idle_seconds, 1),
            "time_above_threshold_seconds": round(self.time_above_threshold_seconds, 1),
            "warning_stage": self.warning_stage,
            "alert_active": self.alert_active,
            "cooldown_remaining_seconds": round(self.cooldown_remaining_seconds, 1),
            "fps": round(self.fps, 1),
            "camera_ok": self.camera_ok,
            "model_ok": self.model_ok,
            "kb_mouse_ok": self.kb_mouse_ok,
            "alert_system_ok": self.alert_system_ok,
            "active_window": self.active_window,
            "session_summary": self.session.to_dict(),
            "events": self.events[:50],
            "gaze_pitch": round(self.gaze_pitch, 2),
            "gaze_yaw": round(self.gaze_yaw, 2),
            "gaze_calibrated": self.gaze_calibrated,
            "workstation_profile": self.workstation_profile,
            "recent_input_activity": self.recent_input_activity,
            "input_activity_override_active": self.input_activity_override_active,
        }


class WorldStateManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = WorldState()

    def read(self) -> WorldState:
        with self._lock:
            return self._state

    def mutate(self, fn) -> WorldState:
        with self._lock:
            fn(self._state)
            return self._state

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._state.to_snapshot()


world_state = WorldStateManager()
