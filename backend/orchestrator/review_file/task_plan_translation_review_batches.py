from orchestrator.result_handler import ResultHandler
from orchestrator.translate_file.task_plan_translation_batches import TaskPlanTranslationBatches


class TaskPlanTranslationReviewBatches(TaskPlanTranslationBatches):
    """Review chain task (slot 01): plan translation batches for review, then forward translated_file_path into the data dict."""

    TASK_TYPE = "TaskPlanTranslationReviewBatches"

    @property
    def task_type(self) -> str:
        """Return the task type identifier."""
        return self.TASK_TYPE

    def run_task(self) -> dict:
        """Delegate to the parent batch planner and inject translated_file_path and translated_filename into the result."""
        data = self.get_data()
        payload = super().run_task()
        if not payload:
            record = ResultHandler.get_instance().get(self.task_type)
            error_message = (
                record["error"]
                if record and record.get("status") == "error" and record.get("error")
                else "Translation review batch planning failed."
            )
            raise RuntimeError(error_message)

        payload["translated_file_path"] = data["translated_file_path"]
        payload["translated_filename"] = data.get("translated_filename")
        return payload
