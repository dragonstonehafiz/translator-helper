import threading
import time
from typing import Any, Optional


class ProgressHandler:
    _instance: Optional["ProgressHandler"] = None

    def __init__(self):
        if ProgressHandler._instance is not None:
            raise RuntimeError("Use ProgressHandler.get_instance()")
        self._lock = threading.Lock()
        self._records: dict[str, dict[str, Any]] = {}

    @staticmethod
    def get_instance() -> "ProgressHandler":
        if ProgressHandler._instance is None:
            ProgressHandler._instance = ProgressHandler()
        return ProgressHandler._instance

    def set(self, task_type: str, progress: dict[str, Any]):
        with self._lock:
            self._records[task_type] = {
                "task_type": task_type,
                "current": int(progress.get("current", 0)),
                "total": int(progress.get("total", 0)),
                "avg_seconds_per_line": float(progress.get("avg_seconds_per_line", 0.0)),
                "eta_seconds": float(progress.get("eta_seconds", 0.0)),
                "_updated_at": time.time(),
            }

    def get(self, task_type: str) -> Optional[dict[str, Any]]:
        with self._lock:
            record = self._records.get(task_type)
            if record is None:
                return None
            return self._public(record)

    def get_latest(self, task_types: list[str]) -> Optional[dict[str, Any]]:
        with self._lock:
            latest: Optional[dict[str, Any]] = None
            for task_type in task_types:
                record = self._records.get(task_type)
                if record is None:
                    continue
                if latest is None or record["_updated_at"] > latest["_updated_at"]:
                    latest = record
            if latest is None:
                return None
            return self._public(latest)

    def clear(self, task_type: str):
        with self._lock:
            self._records.pop(task_type, None)

    @staticmethod
    def _public(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "task_type": record["task_type"],
            "current": record["current"],
            "total": record["total"],
            "avg_seconds_per_line": record["avg_seconds_per_line"],
            "eta_seconds": record["eta_seconds"],
        }
