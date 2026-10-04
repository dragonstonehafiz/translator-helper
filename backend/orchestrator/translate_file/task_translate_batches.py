import time

from anthropic import RateLimitError as AnthropicRateLimitError
from openai import RateLimitError as OpenAIRateLimitError

from models.manager import ModelManager
from orchestrator.base_task import BaseTask, ReportProgress, WriteLog
from orchestrator.task_data.translation import PlannedTranslationData, TranslatedSubtitleData
from prompts.translate import generate_translate_sub_prompt
from prompts.translate_file import generate_translate_batch_prompt
from utils.logger import setup_logger

logger = setup_logger()


class TaskTranslateBatches(BaseTask[PlannedTranslationData, TranslatedSubtitleData]):
    """Translation stage 3: translate each planned batch, with split and per-line fallbacks, then normalize quotes."""

    input_type = PlannedTranslationData
    output_type = TranslatedSubtitleData

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> TranslatedSubtitleData:
        """Translate the loaded subtitles in place and return them; the workflow saves the file."""
        data = self.get_data()
        subs = data.subtitles
        model_manager = ModelManager.get_instance()
        start_time = time.time()

        def on_progress(current: int, total: int, batch_number: int, batch_count: int):
            elapsed = time.time() - start_time
            avg = (elapsed / current) if current > 0 else 0.0
            eta = avg * (total - current) if total > current else 0.0
            report_progress(current, total, f"Batch {batch_number}/{batch_count} complete", eta)

        llm = model_manager.acquire_llm()
        try:
            report_progress(0, len(subs), f"Preparing {len(subs)} subtitle lines for translation", 0.0)
            self._translate_batches(
                llm=llm,
                subs=subs,
                batch_ranges=[(batch.start_index - 1, batch.end_index) for batch in data.batches],
                context=data.context,
                input_lang=data.input_lang,
                target_lang=data.output_lang,
                temperature=llm.config.temperature.value,
                write_log=write_log,
                progress_callback=on_progress,
            )
        finally:
            model_manager.release_llm()

        self._normalize_translated_subtitles(subs)
        return TranslatedSubtitleData(
            subtitles=subs,
            original_filename=data.original_filename,
            output_lang=data.output_lang,
        )

    def _translate_batches(
        self,
        llm,
        subs,
        batch_ranges: list[tuple[int, int]],
        context: dict,
        input_lang: str,
        target_lang: str,
        temperature: float | None,
        write_log: WriteLog,
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

        if failure_logs:
            write_log("04-translate-file-batch-failures.json", {
                "task_type": self.task_type,
                "failure_count": len(failure_logs),
                "failures": failure_logs,
            })
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
