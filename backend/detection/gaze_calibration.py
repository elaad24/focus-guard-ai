from __future__ import annotations

import json
import statistics
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

WorkstationProfile = Literal["laptop_below", "screens_in_front", "side_monitors"]

VALID_PROFILES = frozenset({"laptop_below", "screens_in_front", "side_monitors"})

DEFAULT_FOCUS_ZONES: dict[str, dict[str, float]] = {
    "laptop_below": {"x1": 0.15, "y1": 0.35, "x2": 0.85, "y2": 0.95},
    "screens_in_front": {"x1": 0.2, "y1": 0.15, "x2": 0.8, "y2": 0.65},
    "side_monitors": {"x1": 0.1, "y1": 0.2, "x2": 0.9, "y2": 0.75},
}


@dataclass(frozen=True)
class ProfileTolerances:
    pitch_down_threshold: float
    pitch_up_threshold: float
    yaw_away_threshold: float


PROFILE_TOLERANCES: dict[str, ProfileTolerances] = {
    "laptop_below": ProfileTolerances(
        pitch_down_threshold=25.0,
        pitch_up_threshold=15.0,
        yaw_away_threshold=35.0,
    ),
    "screens_in_front": ProfileTolerances(
        pitch_down_threshold=20.0,
        pitch_up_threshold=20.0,
        yaw_away_threshold=25.0,
    ),
    "side_monitors": ProfileTolerances(
        pitch_down_threshold=20.0,
        pitch_up_threshold=20.0,
        yaw_away_threshold=40.0,
    ),
}


@dataclass
class GazeCalibration:
    workstation_profile: WorkstationProfile | None = None
    baseline_pitch: float | None = None
    baseline_yaw: float | None = None
    calibrated_at: float | None = None
    focus_zone: tuple[float, float, float, float] | None = None

    @property
    def is_calibrated(self) -> bool:
        return (
            self.workstation_profile is not None
            and self.baseline_pitch is not None
            and self.baseline_yaw is not None
        )

    def to_dict(self) -> dict[str, Any]:
        zone = None
        if self.focus_zone is not None:
            zone = {
                "x1": self.focus_zone[0],
                "y1": self.focus_zone[1],
                "x2": self.focus_zone[2],
                "y2": self.focus_zone[3],
            }
        return {
            "calibrated": self.is_calibrated,
            "workstationProfile": self.workstation_profile,
            "baselinePitch": self.baseline_pitch,
            "baselineYaw": self.baseline_yaw,
            "calibratedAt": self.calibrated_at,
            "focusZone": zone,
        }

    def tolerances(self) -> ProfileTolerances:
        if self.workstation_profile is None:
            return PROFILE_TOLERANCES["screens_in_front"]
        return PROFILE_TOLERANCES.get(
            self.workstation_profile,
            PROFILE_TOLERANCES["screens_in_front"],
        )


class GazeCalibrationStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path(__file__).resolve().parent.parent / "gaze_calibration.json"
        self._lock = threading.Lock()
        self._calibration = GazeCalibration()
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            profile = data.get("workstationProfile")
            if profile not in VALID_PROFILES:
                profile = None
            focus_zone = None
            zone_data = data.get("focusZone")
            if isinstance(zone_data, dict):
                focus_zone = (
                    float(zone_data["x1"]),
                    float(zone_data["y1"]),
                    float(zone_data["x2"]),
                    float(zone_data["y2"]),
                )
            self._calibration = GazeCalibration(
                workstation_profile=profile,
                baseline_pitch=data.get("baselinePitch"),
                baseline_yaw=data.get("baselineYaw"),
                calibrated_at=data.get("calibratedAt"),
                focus_zone=focus_zone,
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            self._calibration = GazeCalibration()

    def _save(self) -> None:
        data = {
            "workstationProfile": self._calibration.workstation_profile,
            "baselinePitch": self._calibration.baseline_pitch,
            "baselineYaw": self._calibration.baseline_yaw,
            "calibratedAt": self._calibration.calibrated_at,
        }
        if self._calibration.focus_zone is not None:
            data["focusZone"] = {
                "x1": self._calibration.focus_zone[0],
                "y1": self._calibration.focus_zone[1],
                "x2": self._calibration.focus_zone[2],
                "y2": self._calibration.focus_zone[3],
            }
        self._path.write_text(json.dumps(data, indent=2))

    def get(self) -> GazeCalibration:
        with self._lock:
            return GazeCalibration(
                workstation_profile=self._calibration.workstation_profile,
                baseline_pitch=self._calibration.baseline_pitch,
                baseline_yaw=self._calibration.baseline_yaw,
                calibrated_at=self._calibration.calibrated_at,
                focus_zone=self._calibration.focus_zone,
            )

    def set_profile(self, profile: str) -> dict[str, Any]:
        if profile not in VALID_PROFILES:
            raise ValueError(f"Invalid workstation profile: {profile}")
        zone_defaults = DEFAULT_FOCUS_ZONES[profile]
        zone = (
            zone_defaults["x1"],
            zone_defaults["y1"],
            zone_defaults["x2"],
            zone_defaults["y2"],
        )
        with self._lock:
            self._calibration.workstation_profile = profile  # type: ignore[assignment]
            self._calibration.focus_zone = zone
            self._save()
            return self._calibration.to_dict()

    def set_pose_baseline(self, samples: list[dict[str, float]]) -> dict[str, Any]:
        if not samples:
            raise ValueError("At least one pose sample is required")
        pitches = [float(s["pitch"]) for s in samples if "pitch" in s]
        yaws = [float(s["yaw"]) for s in samples if "yaw" in s]
        if not pitches or not yaws:
            raise ValueError("Samples must include pitch and yaw values")
        with self._lock:
            self._calibration.baseline_pitch = statistics.median(pitches)
            self._calibration.baseline_yaw = statistics.median(yaws)
            self._calibration.calibrated_at = time.time()
            self._save()
            return self._calibration.to_dict()

    def reset(self) -> dict[str, Any]:
        with self._lock:
            self._calibration = GazeCalibration()
            if self._path.exists():
                self._path.unlink()
            return self._calibration.to_dict()


gaze_calibration_store = GazeCalibrationStore()
