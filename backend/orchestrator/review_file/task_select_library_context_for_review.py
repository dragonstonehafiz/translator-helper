from orchestrator.translate_file.task_select_library_context import TaskSelectLibraryContext


class TaskSelectLibraryContextForReview(TaskSelectLibraryContext):
    """Select relevant library context for the review chain (slot 02)."""

    TASK_TYPE = "TaskSelectLibraryContextForReview"
    LOG_FILENAME = "02-select-library-context.json"

    @property
    def task_type(self) -> str:
        return self.TASK_TYPE
