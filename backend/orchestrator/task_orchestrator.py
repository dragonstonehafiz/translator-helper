import threading
import time
from interface.base_task import BaseTask
from typing import Any, Optional
from utils.logger import setup_logger

logger = setup_logger()


class TaskOrchestrator:
    _instance: Optional["TaskOrchestrator"] = None

    def __init__(self):
        if TaskOrchestrator._instance is not None:
            raise RuntimeError("Use TaskOrchestrator.get_instance()")
        self._is_doing_task: bool = False
        self._active_task_type: Optional[str] = None
        self._task_list: list[BaseTask] = []
        self._lock = threading.Lock()

    @staticmethod
    def get_instance() -> "TaskOrchestrator":
        if TaskOrchestrator._instance is None:
            TaskOrchestrator._instance = TaskOrchestrator()
        return TaskOrchestrator._instance

    def is_doing_task(self) -> bool:
        with self._lock:
            return self._is_doing_task

    def is_running(self) -> bool:
        return self.is_doing_task()

    def get_active_task_type(self) -> Optional[str]:
        with self._lock:
            return self._active_task_type

    def add_task(self, task: BaseTask):
        with self._lock:
            self._task_list.append(task)

    def clear_tasks(self):
        with self._lock:
            self._task_list.clear()

    def run_task(self, task: BaseTask, data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        self.clear_tasks()
        self.add_task(task)
        return self.run_tasks(initial_data=data)

    def run_tasks(self, initial_data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        with self._lock:
            if self._is_doing_task:
                raise RuntimeError("A task is already running.")
            self._is_doing_task = True
            tasks = list(self._task_list)

        try:
            output = initial_data or {}
            for task in tasks:
                with self._lock:
                    self._active_task_type = task.task_type
                task.set_data(output)

                filename = self._extract_filename(output)
                log_prefix = f"task={task.task_type}"
                if filename:
                    log_prefix += f" filename={filename}"

                logger.info("%s STARTED", log_prefix)
                started = time.perf_counter()
                try:
                    output = task.run_task()
                    elapsed = time.perf_counter() - started
                    log_dir = output.get("log_dir", "") if isinstance(output, dict) else ""
                    suffix = f" elapsed={elapsed:.3f}s"
                    if log_dir:
                        suffix += f" log_dir={log_dir}"
                    logger.info("%s FINISHED status=complete%s", log_prefix, suffix)
                except Exception:
                    elapsed = time.perf_counter() - started
                    logger.error("%s FAILED elapsed=%.3fs", log_prefix, elapsed, exc_info=True)
                    raise
            return output
        finally:
            with self._lock:
                self._is_doing_task = False
                self._active_task_type = None

    @staticmethod
    def _extract_filename(data: dict[str, Any]) -> str:
        for key in ("original_filename", "translated_filename"):
            value = data.get(key)
            if value:
                return str(value)
        return ""
