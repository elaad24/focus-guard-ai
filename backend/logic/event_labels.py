from __future__ import annotations

CONTRIBUTOR_LABELS: dict[str, str] = {
    "phone_near_person": "Phone detected near you",
    "phone_near_hand_or_face": "Phone near hand or face",
    "phone_usage_over_limit": "Phone use exceeded time limit",
    "head_looking_down": "Head looking down",
    "looking_away_from_screen": "Looking away from screen",
    "keyboard_mouse_idle": "No keyboard/mouse activity",
    "body_hand_idle": "Hands not moving",
    "frequent_yawns": "Repeated yawning (possible fatigue)",
    "eyes_closed_too_long": "Eyes closed for extended period",
    "no_person_detected": "Person not visible to camera",
    "tablet_mode_reduction": "Tablet mode score reduction",
    "high_distraction": "High distraction level",
    "elevated_distraction": "Elevated distraction level",
    "mild_distraction": "Mild distraction detected",
}

WARNING_STAGE_LABELS: dict[str, str] = {
    "soft": "Soft",
    "medium": "Medium",
    "final": "Final",
    "building": "Building",
    "cooldown": "Cooldown",
    "break": "Break",
}


def label_contributor(key: str) -> str:
    return CONTRIBUTOR_LABELS.get(key, key.replace("_", " "))


def format_event_reasons(contributors: list[str] | None) -> str:
    if not contributors:
        return ""
    labels = [label_contributor(c) for c in contributors]
    return "; ".join(labels)


def build_warning_message(stage: str, base_message: str, contributors: list[str] | None) -> str:
    reasons = format_event_reasons(contributors)
    if not reasons:
        return base_message
    stage_label = WARNING_STAGE_LABELS.get(stage, stage.capitalize())
    return f"{stage_label} warning — Reasons: {reasons}"
