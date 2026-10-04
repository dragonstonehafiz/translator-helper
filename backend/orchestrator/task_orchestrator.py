import json
import re
import threading
import time
from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any, Optional

from orchestrator.base_task import BaseTask
from orchestrator.task_data.base import TaskData
from orchestrator.task_state_handler import TaskState, TaskStateHandler
from utils.config import LOGS_DIR
from utils.logger import setup_logger

logger = setup_logger()

WORKFLOWS = ("translate_line", "translate_file", "review_file", "transcribe_clip", "transcribe_file", "update_library")


class RunLog:
    """A run's log folder, logs/<workflow>/<start timestamp>-<input name or workflow>/, created on the first write.

    Runs whose tasks write no diagnostics leave no folder behind.
    """

    def __init__(self, workflow: str, data: TaskData):
        """Name the folder from the workflow, the run's start time and its input name."""
        label = data.run_label() or workflow
        safe_label = re.sub(r"[^\w.\-]", "_", Path(label).name).strip("._") or workflow
        self._parent = LOGS_DIR / workflow
        self._name = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe_label}"
        self.path: Path | None = None

    def write(self, filename: str, content: dict[str, Any]) -> None:
        """Write one JSON diagnostic file, creating the folder first if this is the run's first log."""
        if Path(filename).name != filename or not filename.endswith(".json"):
            raise ValueError(f"Invalid log filename '{filename}'.")
        if self.path is None:
            self.path = self._create_folder()
        with open(self.path / filename, "w", encoding="utf-8") as log_file:
            json.dump(content, log_file, ensure_ascii=False, indent=2)

    def _create_folder(self) -> Path:
        """Create the folder, adding -2, -3, ... if a run with the same name already exists."""
        self._parent.mkdir(parents=True, exist_ok=True)
        candidate = self._parent / self._name
        suffix = 2
        while True:
            try:
                candidate.mkdir()
                return candidate
            except FileExistsError:
                candidate = self._parent / f"{self._name}-{suffix}"
                suffix += 1


class TaskOrchestrator:
    """Singleton that runs one workflow at a time on its own background worker and records its state."""

    _instance: Optional["TaskOrchestrator"] = None

    def __init__(self):
        """Create the state store and the single-worker executor; use get_instance() instead."""
        if TaskOrchestrator._instance is not None:
            raise RuntimeError("Use TaskOrchestrator.get_instance()")
        self._state = TaskStateHandler()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="workflow")
        self._lock = threading.Lock()
        self._running: Optional[str] = None
        self._future: Optional[Future] = None
        self._closed = False

    @staticmethod
    def get_instance() -> "TaskOrchestrator":
        """Return the singleton TaskOrchestrator, creating it on first call."""
        if TaskOrchestrator._instance is None:
            TaskOrchestrator._instance = TaskOrchestrator()
        return TaskOrchestrator._instance

    def get_state_handler(self) -> TaskStateHandler:
        """Return the workflow state store (read-only for callers)."""
        return self._state

    def get_running_state(self) -> TaskState | None:
        """Return the running workflow's state, or None when idle."""
        with self._lock:
            workflow = self._running
        return self._state.get(workflow) if workflow else None

    def run(
        self,
        workflow: str,
        tasks: Sequence[BaseTask],
        data: TaskData,
        *,
        finish: Callable[[TaskData], TaskData],
        cleanup: Callable[[], None],
    ) -> None:
        """Schedule a workflow and return once it is accepted; raises without side effects if it is rejected.

        After this returns, the orchestrator owns the run: `finish` turns the last task's output into the
        workflow's result, and `cleanup` always runs afterwards, on success and failure alike.
        """
        if workflow not in WORKFLOWS:
            raise ValueError(f"Unknown workflow '{workflow}'.")
        tasks = list(tasks)
        if not tasks:
            raise ValueError("A workflow needs at least one task.")

        with self._lock:
            if self._closed:
                raise RuntimeError("The server is shutting down.")
            if self._running is not None:
                raise RuntimeError("Another task is already running.")
            previous = self._state.get(workflow)
            self._running = workflow
            self._state.start_workflow(workflow)
            try:
                self._future = self._executor.submit(self._execute, workflow, tasks, data, finish, cleanup)
            except Exception:
                self._state.restore(workflow, previous)
                self._running = None
                raise

    def shutdown(self) -> None:
        """Refuse new workflows and wait for the running one, including its cleanup, to finish."""
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=True)

    def _execute(
        self,
        workflow: str,
        tasks: list[BaseTask],
        data: TaskData,
        finish: Callable[[TaskData], TaskData],
        cleanup: Callable[[], None],
    ) -> None:
        """Run the tasks in order, then finish and cleanup; record completion or the first error."""
        error: Exception | None = None
        result: TaskData | None = None
        try:
            try:
                run_log = RunLog(workflow, data)
                current = data
                for task in tasks:
                    current = self._run_task(workflow, task, current, run_log)
                result = finish(current)
                if not isinstance(result, TaskData):
                    raise TypeError(f"Workflow '{workflow}' finish returned {type(result).__name__}, not TaskData.")
            except Exception as exc:
                error = exc
                logger.error("workflow=%s FAILED error=%s", workflow, exc, exc_info=True)
            finally:
                try:
                    cleanup()
                except Exception as exc:
                    logger.error("workflow=%s cleanup FAILED error=%s", workflow, exc, exc_info=True)
                    if error is None:
                        error = exc

            if error is not None:
                self._state.fail(workflow, str(error))
            else:
                self._state.complete(workflow, result)
                logger.info("workflow=%s FINISHED status=complete", workflow)
        finally:
            with self._lock:
                self._running = None

    def _run_task(self, workflow: str, task: BaseTask, data: TaskData, run_log: RunLog) -> TaskData:
        """Check the task's input and output types around one run, reporting progress and logs to this workflow."""
        self._state.start_stage(workflow, task.task_type)
        if not isinstance(data, task.input_type):
            raise TypeError(f"{task.task_type} expects {task.input_type.__name__}, got {type(data).__name__}.")
        task.set_data(data)

        log_prefix = f"workflow={workflow} task={task.task_type}"
        logger.info("%s STARTED", log_prefix)
        started = time.perf_counter()
        try:
            output = task.run_task(
                report_progress=partial(self._state.report_progress, workflow),
                write_log=run_log.write,
            )
        except Exception:
            logger.error("%s FAILED elapsed=%.3fs", log_prefix, time.perf_counter() - started, exc_info=True)
            raise
        if not isinstance(output, task.output_type):
            raise TypeError(f"{task.task_type} must return {task.output_type.__name__}, got {type(output).__name__}.")
        logger.info("%s FINISHED elapsed=%.3fs log_dir=%s", log_prefix, time.perf_counter() - started, run_log.path)
        return output
