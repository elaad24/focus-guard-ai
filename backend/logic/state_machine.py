from __future__ import annotations

import threading
import time
from typing import Callable

from alerts.notification_alert import NotificationAlert
from alerts.sound_alert import SoundAlert
from logic.config_store import config_store
from logic.distraction_score import GAZE_IDLE_CONTRIBUTORS, calculate_distraction_score
from logic.event_labels import build_warning_message
from logic.focus_score import calculate_focus_score
from logic.mode_rules import alerts_enabled, apply_mode_to_signals
from logic.session_tracker import SessionTracker
from logic.world_state import DetectionSignals, FocusState, WorldState, world_state

DISTRACTION_RESET_SECONDS = 12.0
THRESHOLD_HYSTERESIS = 10
PERSON_STALE_SECONDS = 8.0

MEANINGFUL_CONTRIBUTORS = frozenset({
    "phone_near_person",
    "phone_near_hand_or_face",
    "phone_usage_over_limit",
    "head_looking_down",
    "looking_away_from_screen",
    "keyboard_mouse_idle",
    "body_hand_idle",
    "frequent_yawns",
    "eyes_closed_too_long",
})

FATIGUE_CONTRIBUTORS = frozenset({"frequent_yawns", "eyes_closed_too_long"})


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

    def start_snooze(self, duration_seconds: float) -> None:
        def mutate(ws: WorldState) -> None:
            now = time.monotonic()
            self._sound_alert.stop_loop()
            ws.snooze_until = now + duration_seconds
            ws.state = FocusState.SNOOZED
            ws.warning_stage = "snooze"
            ws.alert_active = False
            ws.above_threshold_since = None
            ws.time_above_threshold_seconds = 0.0
            ws.below_threshold_since = None
            self._soft_alert_sent = False
            self._medium_beep_sent = False
            minutes = int(duration_seconds // 60)
            ws.add_event("snooze_started", f"Snooze active for {minutes} minutes")

        world_state.mutate(mutate)

    def cancel_snooze(self) -> None:
        def mutate(ws: WorldState) -> None:
            ws.snooze_until = None
            ws.state = FocusState.FOCUSED
            ws.warning_stage = "none"
            ws.add_event("snooze_cancelled", "Snooze cancelled by user")

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

                if ws.signals.person_detected:
                    ws.last_person_detected_at = now

                if ws.signals.phone_near_person:
                    if ws.phone_near_since is None:
                        ws.phone_near_since = now
                else:
                    ws.phone_near_since = None

                ws.recent_input_activity = recent_activity
                ws.input_activity_override_active = (
                    recent_activity and not self._is_instant_unfocused(ws)
                )
                ws.fatigue_active = ws.signals.frequent_yawns or ws.signals.eyes_closed_too_long

                score_result = calculate_distraction_score(
                    ws.signals,
                    ws.mode,
                    config,
                    phone_near_seconds=max(0.0, now - ws.phone_near_since) if ws.phone_near_since else 0.0,
                    recent_input_activity=recent_activity,
                )

                distraction_score = score_result.distraction_score
                contributors = score_result.contributors

                if (
                    not ws.signals.person_detected
                    and "no_person_detected" in contributors
                    and ws.last_person_detected_at is not None
                    and (now - ws.last_person_detected_at) <= PERSON_STALE_SECONDS
                    and ws.last_distraction_score > 0
                ):
                    distraction_score = ws.last_distraction_score
                    contributors = [
                        c for c in ws.last_distraction_contributors if c != "no_person_detected"
                    ] or contributors

                ws.distraction_score = distraction_score
                ws.distraction_contributors = contributors
                if distraction_score > 0 or ws.signals.person_detected:
                    ws.last_distraction_score = distraction_score
                    ws.last_distraction_contributors = list(contributors)

                hands_moving = not ws.signals.body_hand_idle
                focus_result = calculate_focus_score(
                    ws.distraction_score,
                    ws.state,
                    ws.signals,
                    recent_activity,
                    hands_moving,
                )
                ws.focus_score = focus_result.focus_score
                ws.focus_contributors = focus_result.contributors

                self._session_tracker.tick(ws, config)
                self._update_state(ws, config, now, recent_activity)

            world_state.mutate(mutate)
            time.sleep(self.TICK_SECONDS)

    def _has_meaningful_contributors(
        self,
        contributors: list[str],
        recent_input_activity: bool = False,
    ) -> bool:
        if recent_input_activity:
            return any(
                c in MEANINGFUL_CONTRIBUTORS and c not in GAZE_IDLE_CONTRIBUTORS
                for c in contributors
            )
        return any(c in MEANINGFUL_CONTRIBUTORS for c in contributors)

    @staticmethod
    def _event_contributors(ws: WorldState) -> list[str]:
        if ws.distraction_contributors:
            return list(ws.distraction_contributors)
        if ws.last_distraction_contributors:
            return list(ws.last_distraction_contributors)
        return []

    @staticmethod
    def _is_fatigue_active(ws: WorldState) -> bool:
        return any(c in FATIGUE_CONTRIBUTORS for c in ws.distraction_contributors)

    @staticmethod
    def _fatigue_notification_message(ws: WorldState) -> str:
        if "frequent_yawns" in ws.distraction_contributors:
            return (
                "You seem tired — try opening your eyes wide for 20 seconds, "
                "stand and stretch, or sip some water."
            )
        if "eyes_closed_too_long" in ws.distraction_contributors:
            return (
                "Your eyes have been closed a while — blink, look at something far away, "
                "or take a short movement break to wake up."
            )
        return (
            "You seem tired — try 20 seconds with eyes open, a stretch, or water to refocus."
        )

    def _is_instant_unfocused(self, ws: WorldState) -> bool:
        signals = ws.signals
        if signals.phone_near_person or signals.phone_near_hand_or_face:
            return True
        if signals.tablet_near_person and ws.mode != "ipad":
            return True
        return False

    def _update_state(
        self,
        ws: WorldState,
        config: dict,
        now: float,
        recent_input_activity: bool = False,
    ) -> None:
        threshold = float(config.get("procrastinationScoreThreshold", 70))
        exit_threshold = max(0.0, threshold - THRESHOLD_HYSTERESIS)
        soft_after = float(config.get("softWarningAfterSeconds", 45))
        medium_after = float(config.get("mediumWarningAfterSeconds", 60))
        final_after = float(config.get("finalAlertAfterSeconds", 90))
        if self._is_fatigue_active(ws):
            soft_after = min(
                soft_after,
                float(config.get("fatigueSoftWarningAfterSeconds", 15)),
            )

        if ws.mode == "break":
            ws.state = FocusState.BREAK_MODE
            ws.warning_stage = "break"
            ws.alert_active = False
            ws.cooldown_remaining_seconds = 0.0
            return

        if ws.snooze_until is not None:
            remaining = ws.snooze_until - now
            if remaining > 0:
                ws.state = FocusState.SNOOZED
                ws.warning_stage = "snooze"
                ws.alert_active = False
                self._sound_alert.stop_loop()
                ws.above_threshold_since = None
                ws.time_above_threshold_seconds = 0.0
                return
            ws.snooze_until = None
            ws.add_event("snooze_finished", "Snooze period ended")

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

        instant_unfocused = self._is_instant_unfocused(ws)

        if recent_input_activity and not instant_unfocused:
            if ws.state not in {FocusState.ALERT_ACTIVE, FocusState.DISMISSED_COOLDOWN}:
                ws.state = FocusState.FOCUSED
                ws.warning_stage = "none"
                ws.above_threshold_since = None
                ws.time_above_threshold_seconds = 0.0
                ws.below_threshold_since = None
                self._soft_alert_sent = False
                self._medium_beep_sent = False
            return

        above_threshold = ws.distraction_score >= threshold or instant_unfocused
        has_active_contributors = self._has_meaningful_contributors(
            ws.distraction_contributors,
            recent_input_activity,
        )

        if above_threshold or (has_active_contributors and ws.above_threshold_since is not None):
            ws.below_threshold_since = None
            if ws.above_threshold_since is None:
                ws.above_threshold_since = now
            ws.time_above_threshold_seconds = now - ws.above_threshold_since
        else:
            below_exit = ws.distraction_score < exit_threshold and not has_active_contributors
            if below_exit:
                ws.below_threshold_since = ws.below_threshold_since or now
                if now - ws.below_threshold_since >= DISTRACTION_RESET_SECONDS:
                    if ws.state not in {FocusState.ALERT_ACTIVE, FocusState.DISMISSED_COOLDOWN}:
                        ws.state = FocusState.FOCUSED
                        ws.warning_stage = "none"
                        ws.above_threshold_since = None
                        ws.time_above_threshold_seconds = 0.0
                        self._soft_alert_sent = False
                        self._medium_beep_sent = False
            else:
                ws.below_threshold_since = None
                if ws.above_threshold_since is not None:
                    ws.time_above_threshold_seconds = now - ws.above_threshold_since
            if ws.distraction_score < exit_threshold and not has_active_contributors:
                return

        if instant_unfocused and ws.state not in {
            FocusState.ALERT_ACTIVE,
            FocusState.DISMISSED_COOLDOWN,
            FocusState.DISTRACTION_WARNING_SOFT,
            FocusState.DISTRACTION_WARNING_MEDIUM,
        }:
            ws.state = FocusState.DISTRACTED
            ws.warning_stage = "building"

        if ws.time_above_threshold_seconds >= final_after:
            if ws.state != FocusState.ALERT_ACTIVE:
                ws.state = FocusState.ALERT_ACTIVE
                ws.alert_active = True
                ws.warning_stage = "final"
                self._session_tracker.on_final_alert(ws)
                contributors = self._event_contributors(ws)
                ws.add_event(
                    "final_alert",
                    build_warning_message(
                        "final",
                        "Final alert: time for a cheerful refocus check-in",
                        contributors,
                    ),
                    contributors=contributors,
                    warning_stage="final",
                )
                if alerts_enabled(ws.mode) and config.get("soundEnabled", True):
                    self._sound_alert.start_final_loop()
                if alerts_enabled(ws.mode) and config.get("notificationsEnabled", True):
                    body = (
                        self._fatigue_notification_message(ws)
                        if self._is_fatigue_active(ws)
                        else "You've got this! Take a breath and jump back into focus."
                    )
                    self._notification_alert.send("Focus Guard AI", body)
            return

        if ws.time_above_threshold_seconds >= medium_after:
            ws.state = FocusState.DISTRACTION_WARNING_MEDIUM
            ws.warning_stage = "medium"
            if not self._medium_beep_sent and alerts_enabled(ws.mode) and config.get("soundEnabled", True):
                self._sound_alert.play_medium()
                self._medium_beep_sent = True
                self._session_tracker.on_medium_warning(ws)
                contributors = self._event_contributors(ws)
                ws.add_event(
                    "medium_warning",
                    build_warning_message(
                        "medium",
                        "Medium reminder: gentle nudge to return to focus",
                        contributors,
                    ),
                    contributors=contributors,
                    warning_stage="medium",
                )
                if (
                    alerts_enabled(ws.mode)
                    and config.get("notificationsEnabled", True)
                    and self._is_fatigue_active(ws)
                ):
                    self._notification_alert.send(
                        "Focus Guard AI",
                        self._fatigue_notification_message(ws),
                    )
            return

        if ws.time_above_threshold_seconds >= soft_after:
            if ws.state != FocusState.DISTRACTION_WARNING_SOFT:
                self._session_tracker.on_soft_warning(ws)
                contributors = self._event_contributors(ws)
                base_soft = (
                    "Soft warning: you seem tired — take a short wake-up break"
                    if self._is_fatigue_active(ws)
                    else "Soft warning: distraction is building — a good moment to refocus"
                )
                ws.add_event(
                    "soft_warning",
                    build_warning_message("soft", base_soft, contributors),
                    contributors=contributors,
                    warning_stage="soft",
                )
                if not self._soft_alert_sent and alerts_enabled(ws.mode):
                    self._soft_alert_sent = True
                    if config.get("soundEnabled", True):
                        self._sound_alert.play_soft()
                    if config.get("notificationsEnabled", True):
                        body = (
                            self._fatigue_notification_message(ws)
                            if self._is_fatigue_active(ws)
                            else "Distraction is building — a good moment to refocus."
                        )
                        self._notification_alert.send("Focus Guard AI", body)
            ws.state = FocusState.DISTRACTION_WARNING_SOFT
            ws.warning_stage = "soft"
            return

        if ws.state not in {
            FocusState.DISTRACTION_WARNING_SOFT,
            FocusState.DISTRACTION_WARNING_MEDIUM,
            FocusState.ALERT_ACTIVE,
        }:
            ws.state = FocusState.DISTRACTED
            ws.warning_stage = "building"
