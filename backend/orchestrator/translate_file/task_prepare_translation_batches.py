from models.manager import ModelManager
from orchestrator.base_task import BaseTask, ReportProgress, WriteLog
from orchestrator.task_data.base import extend
from orchestrator.task_data.translation import PlannedTranslationData, TranslationData
from orchestrator.translate_file.batch_preparation import plan_batches, split_oversized_batches, validate_final_batches
from utils.subtitles import numbered_lines


class TaskPrepareTranslationBatches(BaseTask[TranslationData, PlannedTranslationData]):
    """Translation stage 1: plan semantic batches with the LLM, then split any batch larger than batch_size."""

    input_type = TranslationData
    output_type = PlannedTranslationData

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> PlannedTranslationData:
        """Plan, repair and validate the batches; logs the model's plan and every repair separately."""
        data = self.get_data()
        model_manager = ModelManager.get_instance()
        indexed_lines = numbered_lines(data.subtitles)
        total_lines = len(indexed_lines)
        log_header = {
            "original_filename": data.original_filename,
            "input_lang": data.input_lang,
            "output_lang": data.output_lang,
            "batch_size": data.batch_size,
            "total_lines": total_lines,
        }

        llm = model_manager.get_llm_client()
        report_progress(0, 1, f"Planning semantic translation batches for {total_lines} subtitle lines", 0.0)
        planned = plan_batches(llm, indexed_lines, data.context, data.input_lang, data.output_lang)
        write_log("01-plan-translation-batches.json", {
            "task_type": self.task_type,
            **log_header,
            "batch_count": len(planned),
            "batches": [batch.to_log() for batch in planned],
        })
        report_progress(1, 1, f"Planned {len(planned)} semantic batches", 0.0)

        oversized = [batch for batch in planned if batch.size > data.batch_size]
        if oversized:
            report_progress(0, len(oversized), f"Splitting {len(oversized)} oversized semantic batches", 0.0)
        batches, repairs = split_oversized_batches(
            llm=llm,
            indexed_lines=indexed_lines,
            batches=planned,
            max_batch_size=data.batch_size,
            context=data.context,
            input_lang=data.input_lang,
            output_lang=data.output_lang,
            on_repaired=lambda done, total: report_progress(done, total, f"Split {done}/{total} oversized batches", 0.0),
        )
        validate_final_batches(batches, total_lines, data.batch_size)
        write_log("02-split-oversized-batches.json", {
            "task_type": self.task_type,
            **log_header,
            "input_batch_count": len(planned),
            "oversized_batch_count": len(oversized),
            "final_batch_count": len(batches),
            "repairs": repairs,
            "batches": [batch.to_log() for batch in batches],
        })

        return extend(data, PlannedTranslationData, batches=batches)
