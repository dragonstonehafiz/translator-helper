import json
import re

from models.manager import ModelManager
from orchestrator.base_task import BaseTask, ReportProgress, WriteLog
from orchestrator.task_data.base import extend
from orchestrator.task_data.translation import Correction, PlannedReviewData, ReviewedData
from prompts.review_file import generate_batch_review_prompt
from utils.subtitles import numbered_lines


class TaskReviewTranslatedBatches(BaseTask[PlannedReviewData, ReviewedData]):
    """Review stage 3: compare original and translated lines batch by batch and collect lines to correct."""

    input_type = PlannedReviewData
    output_type = ReviewedData

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> ReviewedData:
        """Review each batch with the LLM and merge the flagged lines into one sorted correction list."""
        data = self.get_data()
        batches = data.batches
        model_manager = ModelManager.get_instance()
        corrections_by_index: dict[int, Correction] = {}
        batch_logs = []

        llm = model_manager.acquire_llm()
        try:
            report_progress(0, len(batches), f"Reviewing {len(batches)} translation batches", 0.0)
            for batch_number, batch in enumerate(batches, start=1):
                original_lines = numbered_lines(data.subtitles, batch.start_index, batch.end_index)
                translated_lines = numbered_lines(data.translated_subtitles, batch.start_index, batch.end_index)
                raw_output = llm.infer(
                    prompt=self._build_review_prompt(original_lines, translated_lines),
                    system_prompt=generate_batch_review_prompt(
                        context=data.context if data.context else None,
                        input_lang=data.input_lang,
                        output_lang=data.output_lang,
                    ),
                    temperature=0.1,
                )
                try:
                    batch_corrections = self._parse_corrections(raw_output, batch.start_index, batch.end_index)
                except ValueError as exc:
                    write_log("03-review-translated-batch-failures.json", {
                        "task_type": self.task_type,
                        "failure_count": 1,
                        "failures": [self._build_failure_log(
                            batch_number=batch_number,
                            total_batches=len(batches),
                            start_index=batch.start_index,
                            end_index=batch.end_index,
                            original_lines=original_lines,
                            translated_lines=translated_lines,
                            raw_output=raw_output,
                            failure=str(exc),
                        )],
                    })
                    raise ValueError(
                        "Generated review output is malformed JSON. "
                        f"Batch {batch.start_index}-{batch.end_index} must return exactly one JSON object with a 'corrections' array."
                    ) from exc

                for correction in batch_corrections:
                    index = int(correction["index"])
                    reason = str(correction["reason"]).strip()
                    existing = corrections_by_index.get(index)
                    if existing is None:
                        corrections_by_index[index] = Correction(index=index, reason=reason)
                    elif reason not in existing.reason:
                        existing.reason = f"{existing.reason} {reason}".strip()

                batch_logs.append({"batch": batch.to_log(), "corrections": batch_corrections})
                report_progress(batch_number, len(batches), f"Reviewed batch {batch_number}/{len(batches)}", 0.0)
        finally:
            model_manager.release_llm()

        corrections = [corrections_by_index[index] for index in sorted(corrections_by_index)]
        write_log("03-review-translated-batches.json", {
            "task_type": self.task_type,
            "batch_count": len(batches),
            "correction_count": len(corrections),
            "batches": batch_logs,
            "corrections": [
                {
                    "index": c.index,
                    "reason": c.reason,
                    "original": data.subtitles[c.index - 1].text.strip(),
                    "translated": data.translated_subtitles[c.index - 1].text.strip(),
                }
                for c in corrections
            ],
        })
        return extend(data, ReviewedData, corrections=corrections)

    def _build_review_prompt(self, original_lines: list[str], translated_lines: list[str]) -> str:
        """Build the user-turn prompt pairing original and translated subtitle lines for the LLM reviewer."""
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
        """Parse and validate the LLM's correction JSON, ensuring indices are within the reviewed batch span."""
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
        """Extract the first JSON object from the LLM's raw output, stripping any markdown code fences."""
        cleaned = raw_output.strip()
        fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
        if fenced_match:
            return fenced_match.group(1).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("Review did not return a JSON object.")
        return cleaned[start:end + 1].strip()

    def _build_failure_log(
        self,
        batch_number: int,
        total_batches: int,
        start_index: int,
        end_index: int,
        original_lines: list[str],
        translated_lines: list[str],
        raw_output: str,
        failure: str,
    ) -> dict:
        """Build a structured failure log entry recording the batch span, inputs, raw model output, and error."""
        return {
            "batch": {
                "number": batch_number,
                "total": total_batches,
                "start_index": start_index,
                "end_index": end_index,
                "size": len(original_lines),
            },
            "failure": failure,
            "expected": {
                "shape": "exactly one JSON object with a 'corrections' array",
                "schema": {
                    "corrections": [
                        {
                            "index": "integer within the reviewed batch span",
                            "reason": "non-empty string",
                        }
                    ]
                },
                "inputs": {
                    "original_lines": original_lines,
                    "translated_lines": translated_lines,
                },
            },
            "actual": {
                "shape": "raw model output text",
                "text": raw_output,
            },
        }
