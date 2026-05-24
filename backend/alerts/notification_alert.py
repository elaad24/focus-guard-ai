from __future__ import annotations

import subprocess


class NotificationAlert:
    def send(self, title: str, message: str) -> None:
        safe_title = title.replace('"', "'")
        safe_message = message.replace('"', "'")
        script = f'display notification "{safe_message}" with title "{safe_title}"'
        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=False,
                capture_output=True,
                text=True,
            )
        except Exception:
            pass
