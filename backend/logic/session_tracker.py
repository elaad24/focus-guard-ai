from __future__ import annotations

import time
from typing import Any

from logic.world_state import FocusState, WorldState


class SessionTracker:
    TICK_SECONDS = 0.25

    def tick(self, ws: WorldState, config: dict[str, Any]) -> None:
        ws.session.total_monitored_seconds += self.TICK_SECONDS

        threshold = float(config.get("procrastinationScoreThreshold", 70))
        is_focused = ws.distraction_score < threshold and ws.state in {
            FocusState.FOCUSED,
            FocusState.DISMISSED_COOLDOWN,
            FocusState.BREAK_MODE,
        }

        if is_focused:
            ws.session.focused_time_seconds += self.TICK_SECONDS
            ws.current_focus_streak += self.TICK_SECONDS
            ws.current_distraction_streak = 0.0
        else:
            ws.session.distracted_time_seconds += self.TICK_SECONDS
            ws.current_distraction_streak += self.TICK_SECONDS
            ws.current_focus_streak = 0.0

        ws.session.longest_focused_streak_seconds = max(
            ws.session.longest_focused_streak_seconds,
            ws.current_focus_streak,
        )
        ws.session.longest_distraction_streak_seconds = max(
            ws.session.longest_distraction_streak_seconds,
            ws.current_distraction_streak,
        )

        if ws.signals.phone_detected:
            ws.session.total_phone_detected_seconds += self.TICK_SECONDS

        for contributor in ws.distraction_contributors:
            if contributor in {"no_person_detected", "tablet_mode_reduction"}:
                continue
            ws.trigger_counts[contributor] = ws.trigger_counts.get(contributor, 0) + 1

        if ws.trigger_counts:
            ws.session.most_common_trigger = max(ws.trigger_counts, key=ws.trigger_counts.get)

    def on_soft_warning(self, ws: WorldState) -> None:
        ws.session.soft_warnings += 1

    def on_medium_warning(self, ws: WorldState) -> None:
        ws.session.medium_warnings += 1

    def on_final_alert(self, ws: WorldState) -> None:
        ws.session.final_alerts += 1

    def on_dismiss(self, ws: WorldState) -> None:
        ws.session.dismissals += 1
        ws.add_event("alert_dismissed", "Alert dismissed by user")

    def reset(self, ws: WorldState) -> None:
        ws.session = ws.session.__class__()
        ws.trigger_counts = {}
        ws.current_focus_streak = 0.0
        ws.current_distraction_streak = 0.0
        ws.add_event("session_reset", "Session summary reset")
