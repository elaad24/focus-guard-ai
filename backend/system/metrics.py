from __future__ import annotations

from typing import Any

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]


def get_backend_resources() -> dict[str, Any]:
    if psutil is None:
        return {"backend_cpu_percent": None, "backend_memory_mb": None}

    try:
        process = psutil.Process()
        cpu_percent = process.cpu_percent(interval=None)
        memory_mb = round(process.memory_info().rss / (1024 * 1024), 1)
        return {
            "backend_cpu_percent": round(cpu_percent, 1),
            "backend_memory_mb": memory_mb,
        }
    except Exception:
        return {"backend_cpu_percent": None, "backend_memory_mb": None}
