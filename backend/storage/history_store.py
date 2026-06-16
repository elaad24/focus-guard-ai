from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from logic.world_state import SessionSummary

DB_PATH = Path(__file__).resolve().parent.parent / "focus_history.db"
MIN_MONITORED_SECONDS = 5.0


class HistoryStore:
    def __init__(self, path: Path = DB_PATH) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            with sqlite3.connect(self._path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS session_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_start_time REAL NOT NULL,
                        total_monitored_seconds REAL NOT NULL,
                        focused_time_seconds REAL NOT NULL,
                        distracted_time_seconds REAL NOT NULL,
                        soft_warnings INTEGER NOT NULL,
                        medium_warnings INTEGER NOT NULL,
                        final_alerts INTEGER NOT NULL,
                        dismissals INTEGER NOT NULL,
                        total_phone_detected_seconds REAL NOT NULL,
                        longest_focused_streak_seconds REAL NOT NULL,
                        longest_distraction_streak_seconds REAL NOT NULL,
                        most_common_trigger TEXT NOT NULL,
                        ended_at REAL NOT NULL,
                        ended_reason TEXT NOT NULL
                    )
                    """
                )
                conn.commit()

    def save(self, summary: SessionSummary, reason: str) -> bool:
        if summary.total_monitored_seconds < MIN_MONITORED_SECONDS:
            return False

        row = summary.to_dict()
        ended_at = time.time()

        with self._lock:
            with sqlite3.connect(self._path) as conn:
                conn.execute(
                    """
                    INSERT INTO session_history (
                        session_start_time,
                        total_monitored_seconds,
                        focused_time_seconds,
                        distracted_time_seconds,
                        soft_warnings,
                        medium_warnings,
                        final_alerts,
                        dismissals,
                        total_phone_detected_seconds,
                        longest_focused_streak_seconds,
                        longest_distraction_streak_seconds,
                        most_common_trigger,
                        ended_at,
                        ended_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["session_start_time"],
                        row["total_monitored_seconds"],
                        row["focused_time_seconds"],
                        row["distracted_time_seconds"],
                        row["soft_warnings"],
                        row["medium_warnings"],
                        row["final_alerts"],
                        row["dismissals"],
                        row["total_phone_detected_seconds"],
                        row["longest_focused_streak_seconds"],
                        row["longest_distraction_streak_seconds"],
                        row["most_common_trigger"],
                        ended_at,
                        reason,
                    ),
                )
                conn.commit()
        return True

    def recent(self, limit: int = 20) -> list[dict]:
        safe_limit = max(1, min(limit, 100))
        with self._lock:
            with sqlite3.connect(self._path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT
                        id,
                        session_start_time,
                        total_monitored_seconds,
                        focused_time_seconds,
                        distracted_time_seconds,
                        soft_warnings,
                        medium_warnings,
                        final_alerts,
                        dismissals,
                        total_phone_detected_seconds,
                        longest_focused_streak_seconds,
                        longest_distraction_streak_seconds,
                        most_common_trigger,
                        ended_at,
                        ended_reason
                    FROM session_history
                    ORDER BY ended_at DESC
                    LIMIT ?
                    """,
                    (safe_limit,),
                ).fetchall()

        return [dict(row) for row in rows]


history_store = HistoryStore()
