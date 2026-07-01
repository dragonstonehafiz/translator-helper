import json
import os
import time
from pathlib import Path

import pysubs2
from anthropic import RateLimitError as AnthropicRateLimitError
from openai import RateLimitError as OpenAIRateLimitError

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.progress_handler import ProgressHandler
from orchestrator.result_handler import ResultHandler
from prompts.translate import generate_translate_sub_prompt
from prompts.translate_file import generate_translate_batch_prompt
from utils.logger import setup_logger

logger = setup_logger()


class TaskTranslateFile(BaseTask):
    """Chain task (slot 04/final): translate all planned batches and save the result as an ASS subtitle file."""

    TASK_TYPE = "TaskTranslateFile"

    @property
    def task_type(self) -> str:
        """Return the task type identifier."""
        return self.TASK_TYPE

    def run_task(self) -> dict:
        """Translate each batch with retry/split fallback, normalize quotes, save the output file, and mark the chain complete."""
        model_manager = ModelManager.get_instance()
        result_handler = ResultHandler.get_instance()
        progress_handler = ProgressHandler.get_instance()
        llm_client = model_manager.get_llm_client()
        if llm_client is None:
            result_handler.set_error(self.task_type, "LLM model not initialized")
            raise RuntimeError("LLM model not initialized")

        data = self.get_data()
        batches = data.get("batches") or []
        file_path = str(data.get("file_path", ""))
        original_filename = str(data.get("original_filename", "subs.ass"))
        context = data.get("context") or {}
        input_lang = str(data.get("input_lang", "ja"))
        output_lang = str(data.get("output_lang", "en"))
        batch_size = int(data.get("batch_size", 3))
        log_dir = str(data.get("log_dir", ""))

        result_handler.set_processing(self.task_type)
        start_time = time.time()

        def on_progress(current: int, total: int, batch_number: int, batch_count: int):
            elapsed = time.time() - start_time
            avg = (elapsed / current) if current > 0 else 0.0
            eta = avg * (total - current) if total > current else 0.0
            progress_handler.set(
                self.task_type,
                {
                    "current": current,
                    "total": total,
                    "status": f"Batch {batch_number}/{batch_count} complete",
                    "eta_seconds": eta,
                },
            )

        try:
            llm_client.set_running(True)
            subs = pysubs2.load(file_path)
            progress_handler.set(
                self.task_type,
                {
                    "current": 0,
                    "total": len(subs),
                    "status": f"Preparing {len(subs)} subtitle lines for translation",
                    "eta_seconds": 0.0,
                },
            )

            batch_ranges = self._build_batch_ranges(subs=subs, batches=batches, batch_size=batch_size)
            translated_subs = self._translate_batches(
                llm=llm_client,
                subs=subs,
                batch_ranges=batch_ranges,
                context=context,
                input_lang=input_lang,
                target_lang=output_lang,
                temperature=llm_client.get_temperature(),
                log_dir=log_dir,
                progress_callback=on_progress,
            )
            self._normalize_translated_subtitles(translated_subs)

            safe_original_name = os.path.basename(original_filename)
            name_parts = safe_original_name.split(".")
            ext = name_parts[-1]
            base_name = name_parts[0]
            safe_lang = "".join(char for char in output_lang if char.isalnum() or char in ("-", "_")) or "lang"
            translated_filename = f"{base_name}.{safe_lang}.{ext}"
            from utils.config import OUTPUTS_DIR
            output_dir = OUTPUTS_DIR / "sub-files" / "translated"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / translated_filename
            translated_subs.save(output_path)

            progress_handler.set(
                self.task_type,
                {
                    "current": len(subs),
                    "total": len(subs),
                    "status": "Saving translated subtitle file",
                    "eta_seconds": 0.0,
                },
            )

            result_handler.set_complete(self.task_type)
            return {}
        except Exception as exc:
            result_handler.set_error(self.task_type, str(exc))
            raise
        finally:
            llm_client.set_running(False)
            if file_path:
                try:
                    os.remove(file_path)
                except Exception:
                    pass

    def _build_batch_ranges(self, subs, batches: list[dict], batch_size: int) -> list[tuple[int, int]]:
        """Convert planned batch dicts to (start, end) index tuples; falls back to fixed-size slicing if no batches provided."""
        total_lines = len(subs)
        if batches:
            return [
                (int(batch["start_index"]) - 1, int(batch["end_index"]))
                for batch in batches
            ]
        return [
            (start, min(start + batch_size, total_lines))
            for start in range(0, total_lines, batch_size)
        ]

    def _translate_batches(
        self,
        llm,
        subs,
        batch_ranges: list[tuple[int, int]],
        context: dict,
        input_lang: str,
        target_lang: str,
        temperature: float | None,
        log_dir: str = "",
        progress_callback=None,
    ):
        """Translate subtitle lines in batches, splitting on format errors and falling back to per-line translation if needed."""
        processed = 0
        total_lines = len(subs)
        total_batches = len(batch_ranges)
        failure_logs: list[dict] = []

        for batch_number, (start, end) in enumerate(batch_ranges, start=1):
            pending_chunks = [{
                "batch": subs[start:end],
                "start_index": start + 1,
                "end_index": end,
                "allow_split_retry": True,
            }]
            context_dict = context.copy()

            while pending_chunks:
                chunk = pending_chunks.pop(0)
                batch = chunk["batch"]
                chunk_start_index = int(chunk["start_index"])
                chunk_end_index = int(chunk["end_index"])
                allow_split_retry = bool(chunk["allow_split_retry"])
                batch_lines = self._build_batch_lines(batch)
                malformed_error: Exception | None = None
                malformed_lines: list[str] | None = None

                for _ in range(3):
                    translated_lines: list[str] | None = None
                    try:
                        translated_lines = self._translate_batch(
                            llm,
                            batch_lines,
                            context=context_dict,
                            input_lang=input_lang,
                            target_lang=target_lang,
                            temperature=temperature,
                        )
                        if len(translated_lines) != len(batch_lines):
                            raise ValueError("Batch translation output line count mismatch.")

                        for line, translated in zip(batch, translated_lines):
                            line.text = translated.replace("\\N", " ").strip()
                            processed += 1
                            if progress_callback:
                                progress_callback(processed, total_lines, batch_number, total_batches)
                        malformed_error = None
                        malformed_output = None
                        break
                    except Exception as exc:
                        if self._is_rate_limit_error(exc):
                            time.sleep(1.5)
                            continue
                        malformed_error = exc
                        malformed_lines = list(translated_lines) if translated_lines is not None else None
                        break

                if malformed_error is None:
                    continue

                if allow_split_retry and len(batch) > 1:
                    midpoint = len(batch) // 2
                    failure_logs.append(
                        self._build_failure_log(
                            phase="split",
                            batch_number=batch_number,
                            total_batches=total_batches,
                            start_index=chunk_start_index,
                            end_index=chunk_end_index,
                            expected_lines=batch_lines,
                            actual_lines=malformed_lines,
                            failure=str(malformed_error),
                        )
                    )
                    logger.warning(
                        "Batch translation format failure; splitting batch=%s/%s span=%s-%s size=%s failure=%s",
                        batch_number,
                        total_batches,
                        chunk_start_index,
                        chunk_end_index,
                        len(batch),
                        str(malformed_error),
                    )
                    pending_chunks.insert(0, {
                        "batch": batch[midpoint:],
                        "start_index": chunk_start_index + midpoint,
                        "end_index": chunk_end_index,
                        "allow_split_retry": False,
                    })
                    pending_chunks.insert(0, {
                        "batch": batch[:midpoint],
                        "start_index": chunk_start_index,
                        "end_index": chunk_start_index + midpoint - 1,
                        "allow_split_retry": False,
                    })
                    continue

                failure_logs.append(
                    self._build_failure_log(
                        phase="per-line-fallback",
                        batch_number=batch_number,
                        total_batches=total_batches,
                        start_index=chunk_start_index,
                        end_index=chunk_end_index,
                        expected_lines=batch_lines,
                        actual_lines=malformed_lines,
                        failure=str(malformed_error),
                    )
                )
                logger.warning(
                    "Batch translation fallback to per-line mode; batch=%s/%s span=%s-%s size=%s failure=%s",
                    batch_number,
                    total_batches,
                    chunk_start_index,
                    chunk_end_index,
                    len(batch),
                    str(malformed_error),
                )
                for line in batch:
                    translated_text = self._translate_single_line(
                        llm=llm,
                        line=line.text,
                        context=context_dict,
                        input_lang=input_lang,
                        target_lang=target_lang,
                        temperature=temperature,
                    )
                    line.text = translated_text.replace("\\N", " ").strip()
                    processed += 1
                    if progress_callback:
                        progress_callback(processed, total_lines, batch_number, total_batches)

        self._write_failure_log(log_dir=log_dir, failure_logs=failure_logs)
        return subs

    def _translate_batch(
        self,
        llm,
        lines: list[str],
        context: dict | None = None,
        input_lang: str = "ja",
        target_lang: str = "en",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> list[str]:
        """Send a batch of subtitle lines to the LLM and return the translated lines split by newline."""
        system_prompt = generate_translate_batch_prompt(
            context=context,
            input_lang=input_lang,
            target_lang=target_lang,
        )
        response = llm.infer(
            prompt="\n".join(lines),
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        ).strip()
        return [line for line in response.splitlines() if line.strip()]

    def _translate_single_line(
        self,
        llm,
        line: str,
        context: dict | None = None,
        input_lang: str = "ja",
        target_lang: str = "en",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Translate a single subtitle line using the single-line prompt (used as a per-line fallback)."""
        system_prompt = generate_translate_sub_prompt(
            context=context,
            input_lang=input_lang,
            target_lang=target_lang,
        )
        return llm.infer(
            prompt=line,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        ).strip()

    def _build_batch_lines(self, batch) -> list[str]:
        """Format subtitle events as numbered lines with speaker and duration for the LLM batch prompt."""
        batch_lines: list[str] = []
        for i, line in enumerate(batch, start=1):
            speaker = line.name.strip() if line.name else "Line"
            length_seconds = None
            if hasattr(line, "start") and hasattr(line, "end"):
                length_seconds = max(0.0, (float(line.end) - float(line.start)) / 1000.0)
            elif hasattr(line, "length"):
                length_seconds = max(0.0, float(line.length) / 1000.0)
            length_label = f"{length_seconds:.2f}s" if length_seconds is not None else "0.00s"
            batch_lines.append(f"{i}. {speaker} ({length_label}): {line.text}")
        return batch_lines

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        """Return True if the exception is an OpenAI or Anthropic rate limit error (triggers a retry sleep)."""
        return isinstance(exc, (OpenAIRateLimitError, AnthropicRateLimitError))

    def _normalize_translated_subtitles(self, subs):
        """Strip matching outer quote/asterisk pairs from every subtitle line (LLMs sometimes wrap output in quotes)."""
        quote_pairs = {
            '"': '"',
            "'": "'",
            "“": "”",
            "‘": "’",
            "*": "*",
        }
        for line in subs:
            if not isinstance(line.text, str):
                continue

            stripped = line.text.strip()
            if len(stripped) < 2:
                line.text = stripped
                continue

            opening = stripped[0]
            closing = stripped[-1]
            expected_closing = quote_pairs.get(opening)
            if expected_closing and closing == expected_closing:
                line.text = stripped[1:-1].strip()
            else:
                line.text = stripped

    def _build_failure_log(
        self,
        phase: str,
        batch_number: int,
        total_batches: int,
        start_index: int,
        end_index: int,
        expected_lines: list[str],
        actual_lines: list[str] | None,
        failure: str,
    ) -> dict:
        """Build a structured failure log entry recording the batch span, expected/actual output, and error message."""
        return {
            "phase": phase,
            "batch": {
                "number": batch_number,
                "total": total_batches,
                "start_index": start_index,
                "end_index": end_index,
                "size": len(expected_lines),
            },
            "failure": failure,
            "expected": {
                "shape": "one translated line per input subtitle line",
                "line_count": len(expected_lines),
                "lines": expected_lines,
            },
            "actual": {
                "shape": "newline-split translated output returned by the model",
                "line_count": len(actual_lines or []),
                "lines": actual_lines or [],
            },
        }

    def _write_failure_log(self, log_dir: str, failure_logs: list[dict]):
        """Write batch failure entries to 04-translate-file-batch-failures.json; skips if there are no failures."""
        if not log_dir or not failure_logs:
            return

        output_dir = Path(log_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "04-translate-file-batch-failures.json"
        log_payload = {
            "task_type": self.task_type,
            "failure_count": len(failure_logs),
            "failures": failure_logs,
        }
        with open(output_path, "w", encoding="utf-8") as file_handle:
            json.dump(log_payload, file_handle, ensure_ascii=False, indent=2)
