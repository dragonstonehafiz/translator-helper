import json
import re
import time
from pathlib import Path

import pysubs2

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.progress_handler import ProgressHandler
from orchestrator.result_handler import ResultHandler
from prompts.review_file import generate_batch_review_prompt
from utils.logger import setup_logger

logger = setup_logger("task-timings")


class TaskReviewTranslatedBatches(BaseTask):
    TASK_TYPE = "TaskReviewTranslatedBatches"

    @property
    def task_type(self) -> str:
        return self.TASK_TYPE

    def run_task(self) -> dict:
        started = time.perf_counter()
        status = "error"
        model_manager = ModelManager.get_instance()
        result_handler = ResultHandler.get_instance()
        progress_handler = ProgressHandler.get_instance()
        llm_client = model_manager.get_llm_client()
        if llm_client is None:
            result_handler.set_error(self.task_type, "LLM model not initialized")
            return {}

        data = self.get_data()
        batches = data.get("batches") or []
        file_path = str(data.get("file_path", ""))
        translated_file_path = str(data.get("translated_file_path", ""))
        context = data.get("context") or {}
        input_lang = str(data.get("input_lang", "ja"))
        output_lang = str(data.get("output_lang", "en"))
        log_dir = str(data.get("log_dir", ""))

        result_handler.set_processing(self.task_type)
        try:
            original_subs = pysubs2.load(file_path)
            translated_subs = pysubs2.load(translated_file_path)
            if len(original_subs) != len(translated_subs):
                raise ValueError(
                    "Original and translated subtitle files must contain the same number of subtitle lines."
                )
            if not batches:
                raise ValueError("Review requires at least one planned batch.")

            progress_handler.set(
                self.task_type,
                {
                    "current": 0,
                    "total": len(batches),
                    "status": f"Reviewing {len(batches)} translation batches",
                    "eta_seconds": 0.0,
                },
            )

            llm_client.set_running(True)
            corrections_by_index: dict[int, dict[str, int | str]] = {}
            batch_logs = []

            for batch_number, batch in enumerate(batches, start=1):
                start_index = int(batch["start_index"])
                end_index = int(batch["end_index"])
                original_lines = self._build_indexed_lines(original_subs, start_index, end_index)
                translated_lines = self._build_indexed_lines(translated_subs, start_index, end_index)
                raw_output = model_manager.llm_infer(
                    prompt=self._build_review_prompt(original_lines, translated_lines),
                    system_prompt=generate_batch_review_prompt(
                        context=context if context else None,
                        input_lang=input_lang,
                        output_lang=output_lang,
                    ),
                    temperature=0.1,
                )
                try:
                    batch_corrections = self._parse_corrections(raw_output, start_index, end_index)
                except ValueError as exc:
                    raise ValueError(
                        "Generated review output is malformed JSON. "
                        f"Batch {start_index}-{end_index} must return exactly one JSON object with a 'corrections' array."
                    ) from exc
                for correction in batch_corrections:
                    index = int(correction["index"])
                    reason = str(correction["reason"]).strip()
                    if index in corrections_by_index:
                        existing_reason = str(corrections_by_index[index]["reason"])
                        if reason not in existing_reason:
                            corrections_by_index[index]["reason"] = f"{existing_reason} {reason}".strip()
                    else:
                        corrections_by_index[index] = {"index": index, "reason": reason}

                batch_logs.append(
                    {
                        "batch": batch,
                        "corrections": batch_corrections,
                    }
                )
                progress_handler.set(
                    self.task_type,
                    {
                        "current": batch_number,
                        "total": len(batches),
                        "status": f"Reviewed batch {batch_number}/{len(batches)}",
                        "eta_seconds": 0.0,
                    },
                )

            corrections = [corrections_by_index[index] for index in sorted(corrections_by_index)]
            payload = dict(data)
            payload["corrections"] = corrections

            self._write_review_log(
                log_dir=log_dir,
                batch_count=len(batches),
                correction_count=len(corrections),
                batch_logs=batch_logs,
                corrections=corrections,
            )
            result_handler.set_complete(self.task_type)
            status = "complete"
            return payload
        except Exception as exc:
            logger.error("Error reviewing translated subtitle batches: %s", exc, exc_info=True)
            result_handler.set_error(self.task_type, str(exc))
            raise
        finally:
            llm_client.set_running(False)
            logger.info("task=%s status=%s elapsed_seconds=%.3f", self.task_type, status, time.perf_counter() - started)

    def _build_indexed_lines(self, subs, start_index: int, end_index: int) -> list[str]:
        lines = []
        for index in range(start_index, end_index + 1):
            line = subs[index - 1]
            speaker = line.name.strip() if line.name else "Unknown"
            text = line.text.strip() or "[EMPTY]"
            lines.append(f"{index}. {speaker}: {text}")
        return lines

    def _build_review_prompt(self, original_lines: list[str], translated_lines: list[str]) -> str:
        return f"""
        <ORIGINAL_LINES>
        {chr(10).join(original_lines)}
        </ORIGINAL_LINES>

        <TRANSLATED_LINES>
        {chr(10).join(translated_lines)}
        </TRANSLATED_LINES>
        """.strip()

    def _parse_corrections(
        self,
        raw_output: str,
        start_index: int,
        end_index: int,
    ) -> list[dict[str, int | str]]:
        json_payload = self._extract_json_payload(raw_output)
        try:
            parsed = json.loads(json_payload)
        except json.JSONDecodeError as exc:
            raise ValueError("Review output did not contain exactly one valid JSON object.") from exc
        corrections = parsed.get("corrections")
        if not isinstance(corrections, list):
            raise ValueError("Review output must contain a 'corrections' array.")

        normalized = []
        seen_indexes = set()
        for entry in corrections:
            if not isinstance(entry, dict):
                raise ValueError("Each correction entry must be a JSON object.")
            index = entry.get("index")
            reason = entry.get("reason")
            if not isinstance(index, int):
                raise ValueError("Each correction must contain an integer index.")
            if index < start_index or index > end_index:
                raise ValueError("Correction index must be within the reviewed batch span.")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("Each correction must contain a non-empty reason.")
            if index in seen_indexes:
                continue
            seen_indexes.add(index)
            normalized.append({"index": index, "reason": reason.strip()})
        return normalized

    def _extract_json_payload(self, raw_output: str) -> str:
        cleaned = raw_output.strip()
        fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
        if fenced_match:
            return fenced_match.group(1).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("Review did not return a JSON object.")
        return cleaned[start:end + 1].strip()

    def _write_review_log(
        self,
        log_dir: str,
        batch_count: int,
        correction_count: int,
        batch_logs: list[dict],
        corrections: list[dict[str, int | str]],
    ):
        if not log_dir:
            return

        output_dir = Path(log_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        log_payload = {
            "task_type": self.task_type,
            "batch_count": batch_count,
            "correction_count": correction_count,
            "batches": batch_logs,
            "corrections": corrections,
        }
        with open(output_dir / "02-review-translated-batches.json", "w", encoding="utf-8") as file_handle:
            json.dump(log_payload, file_handle, ensure_ascii=False, indent=2)
