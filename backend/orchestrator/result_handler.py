import threading
from typing import Any, Optional


class ResultHandler:
    """Singleton that stores the latest status/result record for each task type, used by the polling endpoint."""

    _instance: Optional["ResultHandler"] = None

    def __init__(self):
        """Initialize the internal record store; use get_instance() instead of calling directly."""
        if ResultHandler._instance is not None:
            raise RuntimeError("Use ResultHandler.get_instance()")
        self._lock = threading.Lock()
        self._records: dict[str, dict[str, Any]] = {}

    @staticmethod
    def get_instance() -> "ResultHandler":
        """Return the singleton ResultHandler, creating it on first call."""
        if ResultHandler._instance is None:
            ResultHandler._instance = ResultHandler()
        return ResultHandler._instance

    def set_processing(self, task_type: str):
        """Record that the given task type has started and is currently processing."""
        with self._lock:
            self._records[task_type] = {
                "task_type": task_type,
                "status": "processing",
                "success": None,
                "result": None,
                "error": None,
            }

    def set_complete(self, task_type: str, result: Optional[dict[str, Any]] = None):
        """Record a successful completion for the given task type; only the final chain task passes a result payload."""
        with self._lock:
            self._records[task_type] = {
                "task_type": task_type,
                "status": "complete",
                "success": True,
                "result": result,
                "error": None,
            }

    def set_error(self, task_type: str, error: str):
        """Record an error for the given task type with a human-readable error message."""
        with self._lock:
            self._records[task_type] = {
                "task_type": task_type,
                "status": "error",
                "success": False,
                "result": None,
                "error": error,
            }

    def clear(self, task_type: str):
        """Remove a stored result so the next poll returns idle."""
        with self._lock:
            self._records.pop(task_type, None)

    def get(self, task_type: str) -> Optional[dict[str, Any]]:
        """Return the record for the given task type, or None if no result has been stored."""
        with self._lock:
            record = self._records.get(task_type)
            return dict(record) if record is not None else None
