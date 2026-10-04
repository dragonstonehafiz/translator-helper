from models.manager import ModelManager
from orchestrator.base_task import BaseTask, ReportProgress, WriteLog
from orchestrator.task_data.base import extend
from orchestrator.task_data.translation import PlannedReviewData, ReviewData
from orchestrator.translate_file.batch_preparation import plan_batches
from utils.subtitles import numbered_lines


class TaskPrepareReviewBatches(BaseTask[ReviewData, PlannedReviewData]):
    """Review stage 1: plan semantic batches with the LLM; review keeps the model's batch sizes as planned."""

    input_type = ReviewData
    output_type = PlannedReviewData

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> PlannedReviewData:
        """Plan the batches over the original subtitles and log the plan."""
        data = self.get_data()
        model_manager = ModelManager.get_instance()
        indexed_lines = numbered_lines(data.subtitles)
        total_lines = len(indexed_lines)

        llm = model_manager.get_llm_client()
        report_progress(0, 1, f"Planning semantic review batches for {total_lines} subtitle lines", 0.0)
        batches = plan_batches(llm, indexed_lines, data.context, data.input_lang, data.output_lang)

        write_log("01-plan-translation-batches.json", {
            "task_type": self.task_type,
            "original_filename": data.original_filename,
            "translated_filename": data.translated_filename,
            "input_lang": data.input_lang,
            "output_lang": data.output_lang,
            "batch_size": data.batch_size,
            "total_lines": total_lines,
            "batch_count": len(batches),
            "batches": [batch.to_log() for batch in batches],
        })
        report_progress(1, 1, f"Planned {len(batches)} semantic batches", 0.0)
        return extend(data, PlannedReviewData, batches=batches)
