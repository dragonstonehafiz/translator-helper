import json
import os
import time

import pysubs2

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.progress_handler import ProgressHandler
from orchestrator.result_handler import ResultHandler
from utils.logger import setup_logger
from utils.translate_subs import _is_rate_limit_error, translate_single_line, translate_sub, translate_file_logger

logger = setup_logger("task-timings")
app_logger = setup_logger("translator-helper")


class TaskTranslateFile(BaseTask):
    TASK_TYPE = "TaskTranslateFile"

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
        original_filename = str(data.get("original_filename", "subs.ass"))
        context = data.get("context") or {}
        input_lang = str(data.get("input_lang", "ja"))
        output_lang = str(data.get("output_lang", "en"))
        batch_size = int(data.get("batch_size", 3))

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
                progress_callback=on_progress,
            )

            safe_original_name = os.path.basename(original_filename)
            name_parts = safe_original_name.split(".")
            ext = name_parts[-1]
            base_name = name_parts[0]
            safe_lang = "".join(char for char in output_lang if char.isalnum() or char in ("-", "_")) or "lang"
            translated_filename = f"{base_name}.{safe_lang}.{ext}"
            output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "sub-files")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, translated_filename)
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

            payload = {"type": "file_translation", "filename": translated_filename}
            result_handler.set_complete(self.task_type, payload)
            status = "complete"
            return payload
        except Exception as exc:
            logger.error("Error translating subtitle file: %s", exc, exc_info=True)
            result_handler.set_error(self.task_type, str(exc))
            return {}
        finally:
            llm_client.set_running(False)
            if file_path:
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            logger.info("task=%s status=%s elapsed_seconds=%.3f", self.task_type, status, time.perf_counter() - started)

    def _build_batch_ranges(self, subs, batches: list[dict], batch_size: int) -> list[tuple[int, int]]:
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
        progress_callback=None,
    ):
        processed = 0
        total_lines = len(subs)
        total_batches = len(batch_ranges)

        for batch_number, (start, end) in enumerate(batch_ranges, start=1):
            pending_chunks = [{
                "batch": subs[start:end],
                "allow_split_retry": True,
            }]
            context_dict = context.copy()

            while pending_chunks:
                chunk = pending_chunks.pop(0)
                batch = chunk["batch"]
                allow_split_retry = bool(chunk["allow_split_retry"])
                batch_lines = self._build_batch_lines(batch)
                malformed_error: Exception | None = None
                malformed_output: str | None = None

                for _ in range(3):
                    try:
                        translated_lines = translate_sub(
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
                            if ":" not in translated:
                                raise ValueError("Missing ':' delimiter in batch translation output.")
                            _, translated_text = translated.split(":", 1)
                            original_line = f"{line.text}"
                            line.text = translated_text.replace("\\N", " ").strip()
                            translate_file_logger.info("Original: %s | Translated: %s", original_line, line.text)
                            processed += 1
                            if progress_callback:
                                progress_callback(processed, total_lines, batch_number, total_batches)
                        malformed_error = None
                        malformed_output = None
                        break
                    except Exception as exc:
                        if _is_rate_limit_error(exc):
                            time.sleep(1.5)
                            continue
                        malformed_error = exc
                        malformed_output = json.dumps(translated_lines, ensure_ascii=False) if "translated_lines" in locals() else None
                        break

                if malformed_error is None:
                    continue

                if allow_split_retry and len(batch) > 1:
                    midpoint = len(batch) // 2
                    app_logger.warning(
                        "Batch translation format failure; splitting batch=%s/%s size=%s failure=%s failed_output=%s",
                        batch_number,
                        total_batches,
                        len(batch),
                        str(malformed_error),
                        malformed_output or "[]",
                    )
                    pending_chunks.insert(0, {
                        "batch": batch[midpoint:],
                        "allow_split_retry": False,
                    })
                    pending_chunks.insert(0, {
                        "batch": batch[:midpoint],
                        "allow_split_retry": False,
                    })
                    continue

                app_logger.warning(
                    "Batch translation fallback to per-line mode; batch=%s/%s size=%s failure=%s failed_output=%s",
                    batch_number,
                    total_batches,
                    len(batch),
                    str(malformed_error),
                    malformed_output or "[]",
                )
                for line in batch:
                    translated_text = translate_single_line(
                        llm=llm,
                        line=line.text,
                        context=context_dict,
                        input_lang=input_lang,
                        target_lang=target_lang,
                        temperature=temperature,
                    )
                    original_line = f"{line.text}"
                    line.text = translated_text.replace("\\N", " ").strip()
                    translate_file_logger.info("Original: %s | Translated: %s", original_line, line.text)
                    processed += 1
                    if progress_callback:
                        progress_callback(processed, total_lines, batch_number, total_batches)

        return subs

    def _build_batch_lines(self, batch) -> list[str]:
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
