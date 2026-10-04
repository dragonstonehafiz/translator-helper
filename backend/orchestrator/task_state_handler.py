import copy
import threading
from dataclasses import dataclass
from typing import Literal

from orchestrator.task_data.base import TaskData


@dataclass(kw_only=True)
class TaskState:
    """One workflow's status, active stage, progress, result and error, read together by the polling endpoint."""

    workflow: str
    status: Literal["processing", "complete", "error"]
    active_task: str | None = None
    progress: tuple[int, int] = (0, 0)
    message: str = ""
    eta_seconds: float = 0.0
    result: TaskData | None = None
    error: str | None = None


class TaskStateHandler:
    """Latest state record per workflow; only TaskOrchestrator writes it, and get() returns a copy."""

    def __init__(self):
        """Create an empty record store."""
        self._lock = threading.Lock()
        self._records: dict[str, TaskState] = {}

    def start_workflow(self, workflow: str) -> None:
        """Replace the workflow's previous record with a fresh processing record."""
        with self._lock:
            self._records[workflow] = TaskState(workflow=workflow, status="processing")

    def start_stage(self, workflow: str, task_type: str) -> None:
        """Mark a new active stage and reset its progress, message and ETA."""
        with self._lock:
            record = self._records[workflow]
            record.active_task = task_type
            record.progress = (0, 0)
            record.message = ""
            record.eta_seconds = 0.0

    def report_progress(self, workflow: str, current: int, total: int, message: str, eta_seconds: float) -> None:
        """Store the active stage's progress."""
        with self._lock:
            record = self._records[workflow]
            record.progress = (int(current), int(total))
            record.message = str(message)
            record.eta_seconds = float(eta_seconds)

    def complete(self, workflow: str, result: TaskData) -> None:
        """Mark the workflow complete with its final result."""
        with self._lock:
            record = self._records[workflow]
            record.status = "complete"
            record.active_task = None
            record.result = result
            record.error = None

    def fail(self, workflow: str, error: str) -> None:
        """Mark the workflow failed, keeping the failed stage and its last progress."""
        with self._lock:
            record = self._records[workflow]
            record.status = "error"
            record.error = error

    def get(self, workflow: str) -> TaskState | None:
        """Return a copy of the workflow's record, or None if it has never run."""
        with self._lock:
            record = self._records.get(workflow)
            return copy.deepcopy(record) if record is not None else None

    def restore(self, workflow: str, record: TaskState | None) -> None:
        """Put back a record saved before a rejected start, or remove the workflow's record if there was none."""
        with self._lock:
            if record is None:
                self._records.pop(workflow, None)
            else:
                self._records[workflow] = record
