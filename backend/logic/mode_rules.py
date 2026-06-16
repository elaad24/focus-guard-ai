from __future__ import annotations

from typing import Any


def apply_mode_to_signals(mode: str, signals_dict: dict[str, bool]) -> dict[str, bool]:
    signals_dict = dict(signals_dict)
    signals_dict["tablet_mode_active"] = mode == "ipad"
    signals_dict["break_mode_active"] = mode == "break"
    signals_dict["video_lesson_mode_active"] = mode == "video_lesson"
    return signals_dict


def alerts_enabled(mode: str) -> bool:
    return mode != "break"


def mode_label(mode: str) -> str:
    labels = {
        "normal": "Normal",
        "video_lesson": "Video Lesson",
        "ipad": "iPad",
        "break": "Break",
        "reading_meeting": "Reading / Meeting",
    }
    return labels.get(mode, mode)


def validate_mode(mode: str) -> str:
    valid = {"normal", "video_lesson", "ipad", "break", "reading_meeting"}
    if mode not in valid:
        raise ValueError(f"Invalid mode: {mode}")
    return mode


def get_mode_config_overrides(mode: str) -> dict[str, Any]:
    if mode == "video_lesson":
        return {"allow_passive_viewing": True}
    if mode == "ipad":
        return {"allow_tablet_usage": True}
    if mode == "break":
        return {"disable_alerts": True}
    if mode == "reading_meeting":
        return {"allow_off_screen_focus": True}
    return {}
