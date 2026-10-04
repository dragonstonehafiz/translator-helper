from models.manager import ModelManager
from orchestrator.base_task import BaseTask, ReportProgress, WriteLog
from orchestrator.task_data.translation import CorrectedSubtitleData, ReviewedData
from orchestrator.workflows.file_output import reviewed_filename
from prompts.review_file import generate_line_retranslation_prompt


class TaskRetranslateReviewedLines(BaseTask[ReviewedData, CorrectedSubtitleData]):
    """Review stage 4: retranslate each flagged line using its review reason; the workflow saves the file."""

    input_type = ReviewedData
    output_type = CorrectedSubtitleData

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> CorrectedSubtitleData:
        """Replace each flagged translated line with a new translation and return the corrected subtitles."""
        data = self.get_data()
        corrections = data.corrections
        original_subs = data.subtitles
        translated_subs = data.translated_subtitles
        model_manager = ModelManager.get_instance()
        correction_logs = []

        llm = model_manager.acquire_llm()
        try:
            report_progress(0, max(1, len(corrections)), f"Retranslating {len(corrections)} reviewed subtitle lines", 0.0)
            for correction_number, correction in enumerate(corrections, start=1):
                index = correction.index
                if index < 1 or index > len(original_subs):
                    raise ValueError(f"Correction index {index} is outside the subtitle file.")

                original_line = original_subs[index - 1]
                translated_line = translated_subs[index - 1]
                corrected_text = llm.infer(
                    prompt=self._build_retranslation_prompt(index, original_line, translated_line, correction.reason),
                    system_prompt=generate_line_retranslation_prompt(
                        context=data.context if data.context else None,
                        input_lang=data.input_lang,
                        output_lang=data.output_lang,
                    ),
                    temperature=llm.config.temperature.value,
                ).strip()
                previous_text = translated_line.text
                translated_line.text = corrected_text.replace("\\N", " ").strip()
                correction_logs.append({
                    "index": index,
                    "reason": correction.reason,
                    "original_text": original_line.text,
                    "previous_translation": previous_text,
                    "corrected_translation": translated_line.text,
                })
                report_progress(correction_number, max(1, len(corrections)), f"Retranslated line {correction_number}/{len(corrections)}", 0.0)
        finally:
            model_manager.release_llm()

        write_log("04-retranslate-reviewed-lines.json", {
            "task_type": self.task_type,
            "output_filename": reviewed_filename(data.translated_filename),
            "corrected_count": len(correction_logs),
            "corrections": correction_logs,
        })
        return CorrectedSubtitleData(
            subtitles=translated_subs,
            translated_filename=data.translated_filename,
            corrected_count=len(corrections),
        )

    def _build_retranslation_prompt(self, index: int, original_line, translated_line, reason: str) -> str:
        """Build the user-turn prompt containing the line index, original, current translation, and review reason."""
        original_speaker = original_line.name.strip() if original_line.name else "Unknown"
        translated_speaker = translated_line.name.strip() if translated_line.name else "Unknown"
        return f"""
        <LINE_INDEX>{index}</LINE_INDEX>
        <ORIGINAL_LINE>{original_speaker}: {original_line.text}</ORIGINAL_LINE>
        <CURRENT_TRANSLATED_LINE>{translated_speaker}: {translated_line.text}</CURRENT_TRANSLATED_LINE>
        <REVIEW_REASON>{reason}</REVIEW_REASON>
        """.strip()
