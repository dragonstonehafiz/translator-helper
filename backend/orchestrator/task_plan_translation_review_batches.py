from orchestrator.task_plan_translation_batches import TaskPlanTranslationBatches


class TaskPlanTranslationReviewBatches(TaskPlanTranslationBatches):
    TASK_TYPE = "TaskPlanTranslationReviewBatches"

    @property
    def task_type(self) -> str:
        return self.TASK_TYPE

    def run_task(self) -> dict:
        data = self.get_data()
        payload = super().run_task()
        if not payload:
            return {}

        payload["translated_file_path"] = data["translated_file_path"]
        payload["translated_filename"] = data.get("translated_filename")
        return payload
