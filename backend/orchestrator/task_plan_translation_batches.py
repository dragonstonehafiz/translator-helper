import json
import re
import time

import pysubs2

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.progress_handler import ProgressHandler
from orchestrator.result_handler import ResultHandler
from utils.logger import setup_logger
from utils.prompts import PromptGenerator

logger = setup_logger("task-timings")


class TaskPlanTranslationBatches(BaseTask):
    TASK_TYPE = "TaskPlanTranslationBatches"

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
        file_path = str(data.get("file_path", ""))
        context = data.get("context") or {}
        input_lang = str(data.get("input_lang", "ja"))
        output_lang = str(data.get("output_lang", "en"))
        batch_size = max(1, int(data.get("batch_size", 50)))

        result_handler.set_processing(self.task_type)
        try:
            indexed_lines, total_lines = self._load_indexed_lines(file_path)
            progress_handler.set(
                self.task_type,
                {
                    "current": 0,
                    "total": 1,
                    "status": f"Planning semantic translation batches for {total_lines} subtitle lines",
                    "eta_seconds": 0.0,
                },
            )

            llm_client.set_running(True)
            raw_output = model_manager.llm_infer(
                prompt=self._build_lines_prompt(indexed_lines),
                system_prompt=PromptGenerator().generate_batch_plan_prompt(
                    context=context if context else None,
                    input_lang=input_lang,
                    output_lang=output_lang,
                ),
                temperature=0.1,
            )
            batches = self._parse_batches(raw_output, expected_start=1, expected_end=total_lines)
            payload = {
                "batches": batches,
                "file_path": file_path,
                "context": context,
                "input_lang": input_lang,
                "output_lang": output_lang,
                "batch_size": batch_size,
            }
            progress_handler.set(
                self.task_type,
                {
                    "current": 1,
                    "total": 1,
                    "status": f"Planned {len(batches)} semantic batches",
                    "eta_seconds": 0.0,
                },
            )
            result_handler.set_complete(self.task_type, payload)
            status = "complete"
            return payload
        except Exception as exc:
            logger.error("Error planning semantic translation batches: %s", exc, exc_info=True)
            result_handler.set_error(self.task_type, str(exc))
            return {}
        finally:
            llm_client.set_running(False)
            logger.info("task=%s status=%s elapsed_seconds=%.3f", self.task_type, status, time.perf_counter() - started)

    def _load_indexed_lines(self, file_path: str) -> tuple[list[str], int]:
        subs = pysubs2.load(file_path)
        indexed_lines: list[str] = []
        for index, line in enumerate(subs, start=1):
            speaker = line.name.strip() if line.name else "Unknown"
            text = line.text.strip() or "[EMPTY]"
            indexed_lines.append(f"{index}. {speaker}: {text}")
        if not indexed_lines:
            raise ValueError("Subtitle file does not contain any subtitle lines.")
        return indexed_lines, len(indexed_lines)

    def _parse_batches(
        self,
        raw_output: str,
        expected_start: int,
        expected_end: int,
    ) -> list[dict[str, int | str]]:
        json_payload = self._extract_json_payload(raw_output)
        parsed = json.loads(json_payload)
        batches = parsed.get("batches")
        if not isinstance(batches, list) or not batches:
            raise ValueError("Batch planner output must contain a non-empty 'batches' array.")

        normalized_batches: list[dict[str, int | str]] = []
        current_start = expected_start
        for entry in batches:
            if not isinstance(entry, dict):
                raise ValueError("Each batch entry must be a JSON object.")
            start_index = entry.get("start_index")
            end_index = entry.get("end_index")
            reason = entry.get("reason")
            if not isinstance(start_index, int) or not isinstance(end_index, int):
                raise ValueError("Each batch must contain integer start_index and end_index values.")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("Each batch must contain a non-empty string reason.")
            if start_index > end_index:
                raise ValueError("Batch start_index cannot be greater than end_index.")
            if start_index != current_start:
                raise ValueError("Batch plan must cover subtitle lines contiguously without gaps or overlap.")
            if end_index > expected_end:
                raise ValueError("Batch plan references subtitle lines beyond the expected subtitle span.")

            normalized_batches.append(
                {"start_index": start_index, "end_index": end_index, "reason": reason.strip()}
            )
            current_start = end_index + 1

        if normalized_batches[0]["start_index"] != expected_start:
            raise ValueError(f"Batch plan must start at subtitle line {expected_start}.")
        if normalized_batches[-1]["end_index"] != expected_end:
            raise ValueError(f"Batch plan must end at subtitle line {expected_end}.")
        return normalized_batches

    def _build_lines_prompt(self, indexed_lines: list[str]) -> str:
        transcript = "\n".join(indexed_lines)
        return f"""
        <SUBTITLE_LINES>
        {transcript}
        </SUBTITLE_LINES>
        """.strip()

    def _extract_json_payload(self, raw_output: str) -> str:
        cleaned = raw_output.strip()
        fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
        if fenced_match:
            return fenced_match.group(1).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("Batch planner did not return a JSON object.")
        return cleaned[start:end + 1].strip()
