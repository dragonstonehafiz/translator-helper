import os

from orchestrator.base_task import BaseTask
from models.manager import ModelManager
from orchestrator.result_handler import ResultHandler
from utils.config import OUTPUTS_DIR


class TaskTranscribeFile(BaseTask):
    """Standalone task: transcribe a full audio file to an ASS subtitle file saved under OUTPUTS_DIR/transcribed/."""

    TASK_TYPE = "TaskTranscribeFile"

    @property
    def task_type(self) -> str:
        """Return the task type identifier."""
        return self.TASK_TYPE

    def run_task(self) -> dict:
        """Transcribe data['file_path'] to a subtitle file and store a complete result with no payload; cleans up the temp file after completion."""
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
            model_manager.acquire_audio()
            subs = audio_client.transcribe_file(file_path, language)
            self._save_subtitles(subs, original_filename, language)
            result_handler.set_complete(self.task_type)
            return {}
        except Exception as exc:
            result_handler.set_error(self.task_type, str(exc))
            raise
        finally:
            model_manager.release_audio()
            if file_path:
                try:
                    os.remove(file_path)
                except Exception:
                    pass

    def _save_subtitles(self, subs, original_filename: str, language: str) -> str:
        """Save subtitles as <first filename segment>.<sanitized language>.ass under OUTPUTS_DIR/transcribed/ and return the path."""
        base_name = os.path.basename(original_filename).split(".")[0]
        safe_lang = "".join(char for char in language if char.isalnum() or char in ("-", "_")) or "lang"
        output_dir = OUTPUTS_DIR / "transcribed"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"{base_name}.{safe_lang}.ass")
        subs.save(output_path)
        return output_path
