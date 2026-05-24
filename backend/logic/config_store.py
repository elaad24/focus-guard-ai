from __future__ import annotations

import json
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "mode": "normal",
    "softWarningAfterSeconds": 45,
    "mediumWarningAfterSeconds": 60,
    "finalAlertAfterSeconds": 90,
    "phoneUsageLimitSeconds": 90,
    "keyboardMouseIdleLimitSeconds": 60,
    "procrastinationScoreThreshold": 70,
    "cooldownAfterDismissSeconds": 120,
    "inputActivityFocusWindowSeconds": 10,
    "soundEnabled": True,
    "notificationsEnabled": True,
    "debugMode": False,
    "saveRawVideo": False,
}

VALID_MODES = {"normal", "video_lesson", "ipad", "break"}


class ConfigStore:
    def __init__(self, path: Path = CONFIG_PATH) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._config = self._load()
        self._subscribers: list[Callable[[dict[str, Any]], None]] = []

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            self._path.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
            return deepcopy(DEFAULT_CONFIG)
        data = json.loads(self._path.read_text())
        merged = deepcopy(DEFAULT_CONFIG)
        merged.update(data)
        return merged

    def get(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._config)

    def update(self, partial: dict[str, Any]) -> dict[str, Any]:
        if "mode" in partial and partial["mode"] not in VALID_MODES:
            raise ValueError(f"Invalid mode: {partial['mode']}")
        if partial.get("saveRawVideo") is True:
            partial["saveRawVideo"] = False
        with self._lock:
            self._config.update(partial)
            self._path.write_text(json.dumps(self._config, indent=2))
            snapshot = deepcopy(self._config)
        for subscriber in self._subscribers:
            subscriber(snapshot)
        return snapshot

    def subscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        self._subscribers.append(callback)


config_store = ConfigStore()
