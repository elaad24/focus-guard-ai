from __future__ import annotations

import platform
import threading
import time
from typing import Any


class ActiveWindowMonitor:
    def __init__(self, poll_interval: float = 2.0) -> None:
        self._poll_interval = poll_interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._active_window: dict[str, str] = {"app_name": "unknown", "bundle_id": "unknown"}
        self._ok = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="active-window")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def get(self) -> dict[str, str]:
        with self._lock:
            return dict(self._active_window)

    def _loop(self) -> None:
        while self._running:
            window = self._fetch_active_window()
            with self._lock:
                self._active_window = window
                self._ok = window.get("app_name") != "unknown"
            time.sleep(self._poll_interval)

    def _fetch_active_window(self) -> dict[str, str]:
        if platform.system() != "Darwin":
            return {"app_name": "unsupported", "bundle_id": "unsupported"}

        try:
            from AppKit import NSWorkspace

            app = NSWorkspace.sharedWorkspace().frontmostApplication()
            if app is None:
                return {"app_name": "unknown", "bundle_id": "unknown"}
            return {
                "app_name": str(app.localizedName() or "unknown"),
                "bundle_id": str(app.bundleIdentifier() or "unknown"),
            }
        except Exception:
            return {"app_name": "unknown", "bundle_id": "unknown"}

    def health(self) -> dict[str, Any]:
        with self._lock:
            return {"active_window_ok": self._ok, "active_window": dict(self._active_window)}
