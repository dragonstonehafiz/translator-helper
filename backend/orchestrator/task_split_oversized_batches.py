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
app_logger = setup_logger("translator-helper")


class TaskSplitOversizedBatches(BaseTask):
    TASK_TYPE = "TaskSplitOversizedBatches"

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
        original_filename = data.get("original_filename")
        context = data.get("context") or {}
        input_lang = str(data.get("input_lang", "ja"))
        output_lang = str(data.get("output_lang", "en"))
        batch_size = max(1, int(data.get("batch_size", 50)))

        result_handler.set_processing(self.task_type)
        try:
            indexed_lines, total_lines = self._load_indexed_lines(file_path)
            oversized_batches = self._find_oversized_batches(batches, batch_size)
            if oversized_batches:
                progress_handler.set(
                    self.task_type,
                    {
                        "current": 0,
                        "total": len(oversized_batches),
                        "status": f"Splitting {len(oversized_batches)} oversized semantic batches",
                        "eta_seconds": 0.0,
                    },
                )

            llm_client.set_running(True)
            repaired_batches = self._split_oversized_batches(
                indexed_lines=indexed_lines,
                batches=batches,
                oversized_batches=oversized_batches,
                max_batch_size=batch_size,
                context=context,
                input_lang=input_lang,
                output_lang=output_lang,
                model_manager=model_manager,
                progress_handler=progress_handler,
            )
            self._validate_final_batches(repaired_batches, total_lines, batch_size)
            payload = {
                "batches": repaired_batches,
                "file_path": file_path,
                "original_filename": original_filename,
                "context": context,
                "input_lang": input_lang,
                "output_lang": output_lang,
                "batch_size": batch_size,
            }
            result_handler.set_complete(self.task_type, payload)
            status = "complete"
            return payload
        except Exception as exc:
            logger.error("Error splitting oversized translation batches: %s", exc, exc_info=True)
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

    def _find_oversized_batches(
        self,
        batches: list[dict[str, int | str]],
        max_batch_size: int,
    ) -> list[dict[str, int | str]]:
        oversized_batches: list[dict[str, int | str]] = []
        for batch in batches:
            start_index = int(batch["start_index"])
            end_index = int(batch["end_index"])
            size = end_index - start_index + 1
            if size > max_batch_size:
                oversized_batches.append(
                    {
                        "start_index": start_index,
                        "end_index": end_index,
                        "reason": str(batch["reason"]),
                        "size": size,
                        "max_batch_size": max_batch_size,
                    }
                )
        return oversized_batches

    def _split_oversized_batches(
        self,
        indexed_lines: list[str],
        batches: list[dict[str, int | str]],
        oversized_batches: list[dict[str, int | str]],
        max_batch_size: int,
        context: dict,
        input_lang: str,
        output_lang: str,
        model_manager: ModelManager,
        progress_handler: ProgressHandler,
    ) -> list[dict[str, int | str]]:
        oversized_lookup = {
            (int(batch["start_index"]), int(batch["end_index"])): batch for batch in oversized_batches
        }
        repaired_batches: list[dict[str, int | str]] = []
        repaired_count = 0

        for batch in batches:
            start_index = int(batch["start_index"])
            end_index = int(batch["end_index"])
            oversized = oversized_lookup.get((start_index, end_index))
            if not oversized:
                repaired_batches.append(batch)
                continue

            slice_lines = indexed_lines[start_index - 1:end_index]
            raw_output = ""
            try:
                raw_output = model_manager.llm_infer(
                    prompt=self._build_lines_prompt(slice_lines),
                    system_prompt=PromptGenerator().generate_split_batch_plan_prompt(
                        context=context if context else None,
                        input_lang=input_lang,
                        output_lang=output_lang,
                        max_batch_size=max_batch_size,
                        original_reason=str(batch["reason"]),
                    ),
                    temperature=0.1,
                )
                split_batches = self._parse_and_validate_split_batches(
                    raw_output=raw_output,
                    expected_start=start_index,
                    expected_end=end_index,
                    max_batch_size=max_batch_size,
                )
            except Exception as exc:
                split_batches = self._build_fallback_batches(
                    start_index=start_index,
                    end_index=end_index,
                    max_batch_size=max_batch_size,
                    original_reason=str(batch["reason"]),
                )
                replacement_spans = ",".join(
                    f"{int(fallback_batch['start_index'])}-{int(fallback_batch['end_index'])}"
                    for fallback_batch in split_batches
                )
                app_logger.warning(
                    "Oversized batch fallback: original=%s-%s deterministic_split=%s max_batch_size=%s failure=%s",
                    start_index,
                    end_index,
                    replacement_spans,
                    max_batch_size,
                    str(exc),
                )

            repaired_batches.extend(split_batches)
            repaired_count += 1
            progress_handler.set(
                self.task_type,
                {
                    "current": repaired_count,
                    "total": max(1, len(oversized_batches)),
                    "status": f"Split {repaired_count}/{len(oversized_batches)} oversized batches",
                    "eta_seconds": 0.0,
                },
            )
        return repaired_batches

    def _validate_final_batches(
        self,
        batches: list[dict[str, int | str]],
        expected_end: int,
        max_batch_size: int,
        expected_start: int = 1,
    ):
        if not batches:
            raise ValueError("Batch planner output must contain a non-empty 'batches' array.")

        contiguous_start = expected_start
        oversized_lines: list[str] = []
        for batch in batches:
            start_index = int(batch["start_index"])
            end_index = int(batch["end_index"])
            reason = str(batch["reason"]).strip()
            if start_index != contiguous_start:
                raise ValueError("Batch plan must cover subtitle lines contiguously without gaps or overlap.")
            if end_index < start_index:
                raise ValueError("Batch start_index cannot be greater than end_index.")
            size = end_index - start_index + 1
            if size > max_batch_size:
                oversized_lines.append(f"- {start_index}-{end_index} (size {size}, max {max_batch_size}): {reason}")
            contiguous_start = end_index + 1

        if batches[0]["start_index"] != expected_start:
            raise ValueError(f"Batch plan must start at subtitle line {expected_start}.")
        if batches[-1]["end_index"] != expected_end:
            raise ValueError(f"Batch plan must end at subtitle line {expected_end}.")
        if oversized_lines:
            details = "\n".join(oversized_lines)
            raise ValueError(
                "Batch plan contains batches larger than the requested maximum batch size:\n"
                f"{details}"
            )

    def _build_fallback_batches(
        self,
        start_index: int,
        end_index: int,
        max_batch_size: int,
        original_reason: str,
    ) -> list[dict[str, int | str]]:
        fallback_batches: list[dict[str, int | str]] = []
        current_start = start_index
        total_parts = ((end_index - start_index + 1) + max_batch_size - 1) // max_batch_size

        for part_index in range(total_parts):
            current_end = min(current_start + max_batch_size - 1, end_index)
            fallback_batches.append(
                {
                    "start_index": current_start,
                    "end_index": current_end,
                    "reason": f"{original_reason} (deterministic split {part_index + 1}/{total_parts})".strip(),
                }
            )
            current_start = current_end + 1

        return fallback_batches

    def _parse_and_validate_split_batches(
        self,
        raw_output: str,
        expected_start: int,
        expected_end: int,
        max_batch_size: int,
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
            if end_index - start_index + 1 > max_batch_size:
                raise ValueError(
                    "Batch plan contains batches larger than the requested maximum batch size:\n"
                    f"- {start_index}-{end_index} "
                    f"(size {end_index - start_index + 1}, max {max_batch_size}): {reason.strip()}"
                )
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
