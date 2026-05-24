from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


class ScreenZoneStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path(__file__).resolve().parent.parent / "screen_zone.json"
        self._lock = threading.Lock()
        self._zone: tuple[float, float, float, float] | None = None
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            self._zone = (
                float(data["x1"]),
                float(data["y1"]),
                float(data["x2"]),
                float(data["y2"]),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            self._zone = None

    def get(self) -> tuple[float, float, float, float] | None:
        with self._lock:
            return self._zone

    def set(self, x1: float, y1: float, x2: float, y2: float) -> dict[str, Any]:
        zone = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        with self._lock:
            self._zone = zone
            self._path.write_text(
                json.dumps({"x1": zone[0], "y1": zone[1], "x2": zone[2], "y2": zone[3]}, indent=2)
            )
        return {"x1": zone[0], "y1": zone[1], "x2": zone[2], "y2": zone[3]}


screen_zone_store = ScreenZoneStore()
