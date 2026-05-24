from __future__ import annotations

import threading
import time
from typing import Callable

from alerts.notification_alert import NotificationAlert
from alerts.sound_alert import SoundAlert
from logic.config_store import config_store
from logic.distraction_score import calculate_distraction_score
from logic.focus_score import calculate_focus_score
from logic.mode_rules import alerts_enabled, apply_mode_to_signals
from logic.session_tracker import SessionTracker
from logic.world_state import DetectionSignals, FocusState, WorldState, world_state

DISTRACTION_RESET_SECONDS = 12.0


class StateMachine:
    TICK_SECONDS = 0.5

    def __init__(
        self,
        sound_alert: SoundAlert,
        notification_alert: NotificationAlert,
        get_idle_seconds: Callable[[], float],
        get_recent_activity: Callable[[], bool],
    ) -> None:
        self._sound_alert = sound_alert
        self._notification_alert = notification_alert
        self._get_idle_seconds = get_idle_seconds
        self._get_recent_activity = get_recent_activity
        self._session_tracker = SessionTracker()
        self._running = False
        self._thread: threading.Thread | None = None
        self._soft_alert_sent = False
        self._medium_beep_sent = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="state-machine")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def dismiss_alert(self) -> None:
        config = config_store.get()

        def mutate(ws: WorldState) -> None:
            self._sound_alert.stop_loop()
            ws.alert_active = False
            ws.cooldown_until = time.monotonic() + float(config.get("cooldownAfterDismissSeconds", 120))
            ws.state = FocusState.DISMISSED_COOLDOWN
            ws.warning_stage = "cooldown"
            ws.above_threshold_since = None
            self._soft_alert_sent = False
            self._medium_beep_sent = False
            self._session_tracker.on_dismiss(ws)
            ws.add_event("cooldown_started", "Cooldown started after alert dismissal")

        world_state.mutate(mutate)

    def set_mode(self, mode: str) -> None:
        def mutate(ws: WorldState) -> None:
            ws.mode = mode
            ws.signals = DetectionSignals(**apply_mode_to_signals(mode, ws.signals.to_dict()))
            if mode == "break":
                self._sound_alert.stop_loop()
                ws.state = FocusState.BREAK_MODE
                ws.alert_active = False
                ws.warning_stage = "break"
            elif ws.state == FocusState.BREAK_MODE:
                ws.state = FocusState.FOCUSED
                ws.warning_stage = "none"
            ws.add_event("mode_changed", f"Mode changed to {mode}")

        world_state.mutate(mutate)

    def _loop(self) -> None:
        while self._running:
            config = config_store.get()
            idle_seconds = self._get_idle_seconds()
            recent_activity = self._get_recent_activity()
            now = time.monotonic()

            def mutate(ws: WorldState) -> None:
                ws.keyboard_mouse_idle_seconds = idle_seconds
                ws.kb_mouse_ok = True
                ws.alert_system_ok = self._sound_alert.ok

                idle_limit = float(config.get("keyboardMouseIdleLimitSeconds", 60))
                ws.signals.keyboard_mouse_idle = idle_seconds >= idle_limit

                if ws.signals.phone_near_person:
                    if ws.phone_near_since is None:
                        ws.phone_near_since = now
                else:
                    ws.phone_near_since = None

                score_result = calculate_distraction_score(
                    ws.signals,
                    ws.mode,
                    config,
                    phone_near_seconds=max(0.0, now - ws.phone_near_since) if ws.phone_near_since else 0.0,
                )
                ws.distraction_score = score_result.distraction_score
                ws.distraction_contributors = score_result.contributors

                hands_moving = not ws.signals.body_hand_idle
                ws.focus_score = calculate_focus_score(
                    ws.distraction_score,
                    ws.state,
                    ws.signals,
                    recent_activity,
                    hands_moving,
                )

                self._session_tracker.tick(ws, config)
                self._update_state(ws, config)

            world_state.mutate(mutate)
            time.sleep(self.TICK_SECONDS)

    def _update_state(self, ws: WorldState, config: dict) -> None:
        now = time.monotonic()
        threshold = float(config.get("procrastinationScoreThreshold", 70))
        soft_after = float(config.get("softWarningAfterSeconds", 45))
        medium_after = float(config.get("mediumWarningAfterSeconds", 60))
        final_after = float(config.get("finalAlertAfterSeconds", 90))

        if ws.mode == "break":
            ws.state = FocusState.BREAK_MODE
            ws.warning_stage = "break"
            ws.alert_active = False
            ws.cooldown_remaining_seconds = 0.0
            return

        if ws.cooldown_until is not None:
            remaining = ws.cooldown_until - now
            if remaining > 0:
                ws.cooldown_remaining_seconds = remaining
                ws.state = FocusState.DISMISSED_COOLDOWN
                ws.warning_stage = "cooldown"
                ws.alert_active = False
                return
            ws.cooldown_until = None
            ws.cooldown_remaining_seconds = 0.0
            ws.add_event("cooldown_finished", "Cooldown finished")

        if ws.state == FocusState.ALERT_ACTIVE:
            ws.alert_active = True
            ws.warning_stage = "final"
            if alerts_enabled(ws.mode) and config.get("soundEnabled", True):
                self._sound_alert.start_final_loop()
            return

        above_threshold = ws.distraction_score >= threshold

        if above_threshold:
            ws.below_threshold_since = None
            if ws.above_threshold_since is None:
                ws.above_threshold_since = now
            ws.time_above_threshold_seconds = now - ws.above_threshold_since
        else:
            ws.above_threshold_since = None
            ws.time_above_threshold_seconds = 0.0
            ws.below_threshold_since = ws.below_threshold_since or now
            reset_after = DISTRACTION_RESET_SECONDS if ws.warning_stage in {"soft", "medium", "building"} else 2.0
            if now - ws.below_threshold_since >= reset_after:
                if ws.state not in {FocusState.ALERT_ACTIVE, FocusState.DISMISSED_COOLDOWN}:
                    ws.state = FocusState.FOCUSED
                    ws.warning_stage = "none"
                    self._soft_alert_sent = False
                    self._medium_beep_sent = False
            return

        if ws.time_above_threshold_seconds >= final_after:
            if ws.state != FocusState.ALERT_ACTIVE:
                ws.state = FocusState.ALERT_ACTIVE
                ws.alert_active = True
                ws.warning_stage = "final"
                self._session_tracker.on_final_alert(ws)
                ws.add_event("final_alert", "Final alert: time for a cheerful refocus check-in")
                if alerts_enabled(ws.mode) and config.get("soundEnabled", True):
                    self._sound_alert.start_final_loop()
                if alerts_enabled(ws.mode) and config.get("notificationsEnabled", True):
                    self._notification_alert.send(
                        "Focus Guard AI",
                        "You've got this! Take a breath and jump back into focus.",
                    )
            return

        if ws.time_above_threshold_seconds >= medium_after:
            ws.state = FocusState.DISTRACTION_WARNING_MEDIUM
            ws.warning_stage = "medium"
            if not self._medium_beep_sent and alerts_enabled(ws.mode) and config.get("soundEnabled", True):
                self._sound_alert.play_medium()
                self._medium_beep_sent = True
                self._session_tracker.on_medium_warning(ws)
                ws.add_event("medium_warning", "Medium reminder: gentle nudge to return to focus")
            return

        if ws.time_above_threshold_seconds >= soft_after:
            if ws.state != FocusState.DISTRACTION_WARNING_SOFT:
                self._session_tracker.on_soft_warning(ws)
                ws.add_event(
                    "soft_warning",
                    "Soft warning: distraction is building — a good moment to refocus",
                )
                if not self._soft_alert_sent and alerts_enabled(ws.mode):
                    self._soft_alert_sent = True
                    if config.get("soundEnabled", True):
                        self._sound_alert.play_soft()
                    if config.get("notificationsEnabled", True):
                        self._notification_alert.send(
                            "Focus Guard AI",
                            "Distraction is building — a good moment to refocus.",
                        )
            ws.state = FocusState.DISTRACTION_WARNING_SOFT
            ws.warning_stage = "soft"
            return

        ws.state = FocusState.DISTRACTED
        ws.warning_stage = "building"
