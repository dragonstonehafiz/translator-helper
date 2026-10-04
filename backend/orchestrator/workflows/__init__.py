"""Workflow functions: each prepares typed input, builds its task list and hands it to TaskOrchestrator.run()."""

import os
from collections.abc import Callable
from pathlib import Path


def remove_files(*paths: Path) -> Callable[[], None]:
    """Return a cleanup callback that deletes the given temp files, ignoring ones already gone."""
    def cleanup() -> None:
        """Delete the workflow's temp inputs."""
        for path in paths:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
    return cleanup


def no_cleanup() -> None:
    """Cleanup callback for workflows that own no temp files."""
