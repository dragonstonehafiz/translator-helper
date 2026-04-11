import os
import time

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.result_handler import ResultHandler
from utils.logger import setup_logger

logger = setup_logger("task-timings")


class TaskTranscribeLine(BaseTask):
    TASK_TYPE = "TaskTranscribeLine"

    @property
    def task_type(self) -> str:
        return self.TASK_TYPE

    def run_task(self) -> dict:
        started = time.perf_counter()
        status = "error"
        model_manager = ModelManager.get_instance()
        result_handler = ResultHandler.get_instance()
        audio_client = model_manager.get_audio_client()
        if audio_client is None:
            result_handler.set_error(self.task_type, "Audio model not initialized")
            return {}

        data = self.get_data()
        file_path = str(data.get("file_path", ""))
        language = str(data.get("language", "ja"))

        result_handler.set_processing(self.task_type)
        try:
            audio_client.set_running(True)
            transcript = model_manager.audio_transcribe_line(file_path, language)
            payload = {"type": "transcription", "data": transcript}
            result_handler.set_complete(self.task_type, payload)
            status = "complete"
            return payload
        except Exception as exc:
            logger.error("Error transcribing audio line: %s", exc, exc_info=True)
            result_handler.set_error(self.task_type, str(exc))
            return {}
        finally:
            audio_client.set_running(False)
            if file_path:
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            logger.info("task=%s status=%s elapsed_seconds=%.3f", self.task_type, status, time.perf_counter() - started)
