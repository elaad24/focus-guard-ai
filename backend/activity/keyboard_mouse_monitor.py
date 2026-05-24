from __future__ import annotations

"""
PRIVACY INVARIANT:
This module tracks ONLY keyboard/mouse activity timestamps.
It must NEVER read, store, or log actual key values or typed content.
Handlers intentionally ignore all event payload details.
"""

import threading
import time
from typing import Any

from pynput import keyboard, mouse


class KeyboardMouseMonitor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_input_ts = time.monotonic()
        self._events_this_second = 0
        self._running = False
        self._keyboard_listener: keyboard.Listener | None = None
        self._mouse_listener: mouse.Listener | None = None
        self._ok = False

    def _touch(self) -> None:
        with self._lock:
            self._last_input_ts = time.monotonic()
            self._events_this_second += 1

    def _on_keyboard_event(self, *_args, **_kwargs) -> None:
        self._touch()

    def _on_mouse_event(self, *_args, **_kwargs) -> None:
        self._touch()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        try:
            self._keyboard_listener = keyboard.Listener(
                on_press=self._on_keyboard_event,
                on_release=self._on_keyboard_event,
            )
            self._mouse_listener = mouse.Listener(
                on_move=self._on_mouse_event,
                on_click=self._on_mouse_event,
                on_scroll=self._on_mouse_event,
            )
            self._keyboard_listener.start()
            self._mouse_listener.start()
            self._ok = True
        except Exception:
            self._ok = False

    def stop(self) -> None:
        self._running = False
        if self._keyboard_listener is not None:
            self._keyboard_listener.stop()
        if self._mouse_listener is not None:
            self._mouse_listener.stop()

    def seconds_since_last_input(self) -> float:
        with self._lock:
            return max(0.0, time.monotonic() - self._last_input_ts)

    def had_recent_activity(self, within_seconds: float = 5.0) -> bool:
        return self.seconds_since_last_input() <= within_seconds

    @property
    def ok(self) -> bool:
        return self._ok

    def health(self) -> dict[str, Any]:
        return {
            "kb_mouse_ok": self._ok,
            "idle_seconds": round(self.seconds_since_last_input(), 1),
        }
