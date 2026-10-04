from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Generic, TypeVar

from orchestrator.task_data.base import TaskData

InputT = TypeVar("InputT", bound=TaskData)
OutputT = TypeVar("OutputT", bound=TaskData)

ReportProgress = Callable[[int, int, str, float], None]
"""report_progress(current, total, message, eta_seconds)"""

WriteLog = Callable[[str, dict[str, Any]], None]
"""write_log(filename, content): write one JSON diagnostic file into the run's log folder."""


class BaseTask(ABC, Generic[InputT, OutputT]):
    """One stage of a workflow: takes one typed input and returns one typed output."""

    input_type: type[InputT]
    output_type: type[OutputT]

    def __init__(self):
        """Create the task with no input yet; the orchestrator supplies it with set_data()."""
        self._data: InputT | None = None

    @property
    def task_type(self) -> str:
        """Return the task's name, shown as the workflow's active stage."""
        return self.__class__.__name__

    def set_data(self, data: InputT) -> None:
        """Supply the task's input (called by the orchestrator before run_task)."""
        self._data = data

    def get_data(self) -> InputT:
        """Return the task's input; raises if none has been supplied."""
        if self._data is None:
            raise RuntimeError(f"{self.task_type} has no input data.")
        return self._data

    @abstractmethod
    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> OutputT:
        """Run the stage and return its output; raise on failure (the orchestrator records the error)."""
        raise NotImplementedError
