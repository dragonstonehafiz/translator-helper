from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseTask(ABC):
    def __init__(self, data: Optional[dict[str, Any]] = None):
        if data is None:
            self._data = {}
        else:
            self._data = data

    def set_data(self, data: dict[str, Any]):
        self._data = data

    def get_data(self) -> dict[str, Any]:
        return self._data

    @property
    def task_type(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def run_task(self) -> dict[str, Any]:
        # returns results of task as a dict
        raise NotImplementedError

    # Temporary alias while task classes are being migrated.
    def runTask(self) -> dict[str, Any]:
        return self.run_task()

