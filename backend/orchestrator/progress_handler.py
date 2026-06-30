import threading
from typing import Any, Optional


class ProgressHandler:
    """Singleton that stores current/total/status/eta progress for each task type, read by the polling endpoint."""

    _instance: Optional["ProgressHandler"] = None

    def __init__(self):
        """Initialize the internal progress store; use get_instance() instead of calling directly."""
        if ProgressHandler._instance is not None:
            raise RuntimeError("Use ProgressHandler.get_instance()")
        self._lock = threading.Lock()
        self._records: dict[str, dict[str, Any]] = {}

    @staticmethod
    def get_instance() -> "ProgressHandler":
        """Return the singleton ProgressHandler, creating it on first call."""
        if ProgressHandler._instance is None:
            ProgressHandler._instance = ProgressHandler()
        return ProgressHandler._instance

    def set(self, task_type: str, progress: dict[str, Any]):
        """Store a progress snapshot for the given task type (keys: current, total, status, eta_seconds)."""
        with self._lock:
            self._records[task_type] = {
                "task_type": task_type,
                "current": int(progress.get("current", 0)),
                "total": int(progress.get("total", 0)),
                "status": str(progress.get("status", "")),
                "eta_seconds": float(progress.get("eta_seconds", 0.0)),
            }

    def get(self, task_type: str) -> Optional[dict[str, Any]]:
        """Return the stored progress dict for the given task type, or None if not set."""
        with self._lock:
            record = self._records.get(task_type)
            return dict(record) if record is not None else None

    def clear(self, task_type: str):
        """Remove the stored progress record for the given task type."""
        with self._lock:
            self._records.pop(task_type, None)
