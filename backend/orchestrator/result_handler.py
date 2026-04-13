import threading
from typing import Any, Optional


class ResultHandler:
    _instance: Optional["ResultHandler"] = None

    def __init__(self):
        if ResultHandler._instance is not None:
            raise RuntimeError("Use ResultHandler.get_instance()")
        self._lock = threading.Lock()
        self._records: dict[str, dict[str, Any]] = {}

    @staticmethod
    def get_instance() -> "ResultHandler":
        if ResultHandler._instance is None:
            ResultHandler._instance = ResultHandler()
        return ResultHandler._instance

    def set_processing(self, task_type: str):
        with self._lock:
            self._records[task_type] = {
                "task_type": task_type,
                "status": "processing",
                "success": None,
                "result": None,
                "error": None,
            }

    def set_complete(self, task_type: str, result: Optional[dict[str, Any]] = None):
        with self._lock:
            self._records[task_type] = {
                "task_type": task_type,
                "status": "complete",
                "success": True,
                "result": result,
                "error": None,
            }

    def set_error(self, task_type: str, error: str):
        with self._lock:
            self._records[task_type] = {
                "task_type": task_type,
                "status": "error",
                "success": False,
                "result": None,
                "error": error,
            }

    def get(self, task_type: str) -> Optional[dict[str, Any]]:
        with self._lock:
            record = self._records.get(task_type)
            if record is None:
                return None
            return self._public(record)

    @staticmethod
    def _public(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "task_type": record["task_type"],
            "status": record["status"],
            "success": record["success"],
            "result": record["result"],
            "error": record["error"],
        }
