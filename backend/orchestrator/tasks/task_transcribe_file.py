from models.manager import ModelManager
from orchestrator.base_task import BaseTask, ReportProgress, WriteLog
from orchestrator.task_data.general import TranscribeFileData, TranscribedSubtitleData


class TaskTranscribeFile(BaseTask[TranscribeFileData, TranscribedSubtitleData]):
    """Transcribe a full audio file to subtitles; the workflow saves them."""

    input_type = TranscribeFileData
    output_type = TranscribedSubtitleData

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> TranscribedSubtitleData:
        """Transcribe the file and return the subtitles with their naming metadata."""
        data = self.get_data()
        model_manager = ModelManager.get_instance()
        audio = model_manager.get_audio_client()
        report_progress(0, 1, "Transcribing the uploaded audio file", 0.0)
        subtitles = audio.transcribe_file(str(data.audio_path), data.language)
        report_progress(1, 1, f"Transcribed {len(subtitles)} subtitle lines", 0.0)
        return TranscribedSubtitleData(
            subtitles=subtitles,
            original_filename=data.original_filename,
            language=data.language,
        )
