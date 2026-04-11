import os
import time

import pysubs2

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.progress_handler import ProgressHandler
from orchestrator.result_handler import ResultHandler
from utils.logger import setup_logger
from utils.translate_subs import translate_subs

logger = setup_logger("task-timings")


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
        file_path = str(data.get("file_path", ""))
        original_filename = str(data.get("original_filename", "subs.ass"))
        context = data.get("context") or {}
        input_lang = str(data.get("input_lang", "ja"))
        output_lang = str(data.get("output_lang", "en"))
        batch_size = int(data.get("batch_size", 3))

        result_handler.set_processing(self.task_type)
        start_time = time.time()

        def on_progress(current: int, total: int):
            elapsed = time.time() - start_time
            avg = (elapsed / current) if current > 0 else 0.0
            eta = avg * (total - current) if total > current else 0.0
            progress_handler.set(
                self.task_type,
                {
                    "current": current,
                    "total": total,
                    "avg_seconds_per_line": avg,
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
                    "avg_seconds_per_line": 0.0,
                    "eta_seconds": 0.0,
                },
            )

            translated_subs = translate_subs(
                llm=llm_client,
                subs=subs,
                context=context,
                batch_size=batch_size,
                input_lang=input_lang,
                target_lang=output_lang,
                temperature=llm_client.get_temperature(),
                progress_callback=on_progress,
            )

            safe_original_name = os.path.basename(original_filename)
            base_name = safe_original_name.split(".")[0]
            _, ext = os.path.splitext(safe_original_name)
            safe_lang = "".join(char for char in output_lang if char.isalnum() or char in ("-", "_")) or "lang"
            translated_filename = f"{base_name}.{safe_lang}{ext}"
            output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "sub-files")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, translated_filename)
            translated_subs.save(output_path)

            final_progress = progress_handler.get(self.task_type) or {}
            progress_handler.set(
                self.task_type,
                {
                    "current": final_progress.get("total", len(subs)),
                    "total": final_progress.get("total", len(subs)),
                    "avg_seconds_per_line": final_progress.get("avg_seconds_per_line", 0.0),
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
