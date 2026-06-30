import json
import os
from pathlib import Path

import pysubs2

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.progress_handler import ProgressHandler
from orchestrator.result_handler import ResultHandler
from prompts.review_file import generate_line_retranslation_prompt


class TaskRetranslateReviewedLines(BaseTask):
    TASK_TYPE = "TaskRetranslateReviewedLines"

    @property
    def task_type(self) -> str:
        return self.TASK_TYPE

    def run_task(self) -> dict:
        model_manager = ModelManager.get_instance()
        result_handler = ResultHandler.get_instance()
        progress_handler = ProgressHandler.get_instance()
        llm_client = model_manager.get_llm_client()
        if llm_client is None:
            result_handler.set_error(self.task_type, "LLM model not initialized")
            return {}

        data = self.get_data()
        file_path = str(data.get("file_path", ""))
        translated_file_path = str(data.get("translated_file_path", ""))
        translated_filename = str(data.get("translated_filename") or "translated.ass")
        corrections = data.get("corrections") or []
        context = data.get("context") or {}
        input_lang = str(data.get("input_lang", "ja"))
        output_lang = str(data.get("output_lang", "en"))
        log_dir = str(data.get("log_dir", ""))

        result_handler.set_processing(self.task_type)
        try:
            if not file_path or not translated_file_path:
                raise ValueError(
                    "Translation review could not continue because the upstream review stage did not provide subtitle file paths."
                )
            original_subs = pysubs2.load(file_path)
            translated_subs = pysubs2.load(translated_file_path)
            if len(original_subs) != len(translated_subs):
                raise ValueError(
                    "Original and translated subtitle files must contain the same number of subtitle lines."
                )

            progress_handler.set(
                self.task_type,
                {
                    "current": 0,
                    "total": max(1, len(corrections)),
                    "status": f"Retranslating {len(corrections)} reviewed subtitle lines",
                    "eta_seconds": 0.0,
                },
            )

            llm_client.set_running(True)
            correction_logs = []
            for correction_number, correction in enumerate(corrections, start=1):
                index = int(correction["index"])
                reason = str(correction["reason"]).strip()
                if index < 1 or index > len(original_subs):
                    raise ValueError(f"Correction index {index} is outside the subtitle file.")

                original_line = original_subs[index - 1]
                translated_line = translated_subs[index - 1]
                corrected_text = model_manager.llm_infer(
                    prompt=self._build_retranslation_prompt(index, original_line, translated_line, reason),
                    system_prompt=generate_line_retranslation_prompt(
                        context=context if context else None,
                        input_lang=input_lang,
                        output_lang=output_lang,
                    ),
                    temperature=llm_client.get_temperature(),
                ).strip()
                previous_text = translated_line.text
                translated_line.text = corrected_text.replace("\\N", " ").strip()
                correction_logs.append(
                    {
                        "index": index,
                        "reason": reason,
                        "original_text": original_line.text,
                        "previous_translation": previous_text,
                        "corrected_translation": translated_line.text,
                    }
                )
                progress_handler.set(
                    self.task_type,
                    {
                        "current": correction_number,
                        "total": max(1, len(corrections)),
                        "status": f"Retranslated line {correction_number}/{len(corrections)}",
                        "eta_seconds": 0.0,
                    },
                )

            output_path = self._save_corrected_file(translated_subs, translated_filename)
            self._write_retranslation_log(
                log_dir=log_dir,
                output_path=output_path,
                correction_logs=correction_logs,
            )

            payload = {
                "corrected_count": len(corrections),
                "output_filename": Path(output_path).name,
            }
            result_handler.set_complete(self.task_type, payload)
            return payload
        except Exception as exc:
            result_handler.set_error(self.task_type, str(exc))
            raise
        finally:
            llm_client.set_running(False)

    def _build_retranslation_prompt(self, index: int, original_line, translated_line, reason: str) -> str:
        original_speaker = original_line.name.strip() if original_line.name else "Unknown"
        translated_speaker = translated_line.name.strip() if translated_line.name else "Unknown"
        return f"""
        <LINE_INDEX>{index}</LINE_INDEX>
        <ORIGINAL_LINE>{original_speaker}: {original_line.text}</ORIGINAL_LINE>
        <CURRENT_TRANSLATED_LINE>{translated_speaker}: {translated_line.text}</CURRENT_TRANSLATED_LINE>
        <REVIEW_REASON>{reason}</REVIEW_REASON>
        """.strip()

    def _save_corrected_file(self, translated_subs, translated_filename: str) -> str:
        safe_name = os.path.basename(translated_filename) or "translated.ass"
        path = Path(safe_name)
        suffix = path.suffix or ".ass"
        corrected_filename = f"{path.stem}.corrected{suffix}"
        from utils.config import OUTPUTS_DIR
        output_dir = OUTPUTS_DIR / "sub-files"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / corrected_filename
        translated_subs.save(str(output_path))
        return str(output_path)

    def _write_retranslation_log(
        self,
        log_dir: str,
        output_path: str,
        correction_logs: list[dict],
    ):
        if not log_dir:
            return

        output_dir = Path(log_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        log_payload = {
            "task_type": self.task_type,
            "output_filename": Path(output_path).name,
            "corrected_count": len(correction_logs),
            "corrections": correction_logs,
        }
        with open(output_dir / "04-retranslate-reviewed-lines.json", "w", encoding="utf-8") as file_handle:
            json.dump(log_payload, file_handle, ensure_ascii=False, indent=2)
