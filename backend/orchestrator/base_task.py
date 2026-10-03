from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseTask(ABC):
    """Abstract base class for all orchestrator tasks."""

    def __init__(self, data: Optional[dict[str, Any]] = None):
        """Initialize the task with an optional pre-seeded data dict."""
        if data is None:
            self._data = {}
        else:
            self._data = data

    def set_data(self, data: dict[str, Any]):
        """Replace the task's internal data dict (called by the orchestrator before run_task)."""
        self._data = data

    def get_data(self) -> dict[str, Any]:
        """Return the current pass-through data dict."""
        return self._data

    @property
    def task_type(self) -> str:
        """Return the task type identifier string."""
        return self.__class__.__name__

    @abstractmethod
    def run_task(self) -> dict[str, Any]:
        """Execute the task and return a pass-through dict containing all upstream keys plus new outputs."""
        raise NotImplementedError

