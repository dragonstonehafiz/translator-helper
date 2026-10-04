"""Base TaskData class, the extend() helper and the final outputs shared by several workflows."""

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, TypeVar


@dataclass(kw_only=True)
class TaskData:
    """Base class for all task inputs and outputs."""

    def run_label(self) -> str | None:
        """Return the input name used for this run's log folder, or None to use the workflow name."""
        return None


DataT = TypeVar("DataT", bound=TaskData)


def extend(data: TaskData, target: type[DataT], **extra: Any) -> DataT:
    """Build `target` from every field of `data` plus the new fields in `extra`."""
    values = {f.name: getattr(data, f.name) for f in fields(data)}
    values.update(extra)
    return target(**values)


@dataclass(kw_only=True)
class TextOutputData(TaskData):
    """Final result of a one-line translation or a clip transcription."""

    text: str


@dataclass(kw_only=True)
class FileOutputData(TaskData):
    """Final result of a workflow that saved a file."""

    output_path: Path


@dataclass(kw_only=True)
class ReviewFileOutputData(FileOutputData):
    """Final result of a review: the saved corrected file and how many lines were corrected."""

    corrected_count: int
