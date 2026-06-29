import os

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.result_handler import ResultHandler


class TaskTranscribeFile(BaseTask):
    TASK_TYPE = "TaskTranscribeFile"

    @property
    def task_type(self) -> str:
        return self.TASK_TYPE

    def run_task(self) -> dict:
        model_manager = ModelManager.get_instance()
        result_handler = ResultHandler.get_instance()
        audio_client = model_manager.get_audio_client()
        if audio_client is None:
            result_handler.set_error(self.task_type, "Audio model not initialized")
            raise RuntimeError("Audio model not initialized")

        data = self.get_data()
        file_path = str(data.get("file_path", ""))
        language = str(data.get("language", "ja"))
        original_filename = str(data.get("original_filename", "audio.wav"))

        result_handler.set_processing(self.task_type)
        try:
            audio_client.set_running(True)
            model_manager.audio_transcribe_file(file_path, language, original_filename)
            result_handler.set_complete(self.task_type)
            return {}
        except Exception as exc:
            result_handler.set_error(self.task_type, str(exc))
            raise
        finally:
            audio_client.set_running(False)
            if file_path:
                try:
                    os.remove(file_path)
                except Exception:
                    pass
