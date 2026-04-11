import threading
from interface.base_task import BaseTask
from typing import Any, Optional


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
                output = task.run_task()
            return output
        finally:
            with self._lock:
                self._is_doing_task = False
                self._active_task_type = None
