from models.manager import ModelManager
from orchestrator.base_task import BaseTask, ReportProgress, WriteLog
from orchestrator.task_data.base import TextOutputData
from orchestrator.task_data.general import TranscribeClipData


class TaskTranscribeClip(BaseTask[TranscribeClipData, TextOutputData]):
    """Transcribe a short audio clip to one line of text."""

    input_type = TranscribeClipData
    output_type = TextOutputData

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> TextOutputData:
        """Transcribe the clip and return the text."""
        data = self.get_data()
        model_manager = ModelManager.get_instance()
        audio = model_manager.get_audio_client()
        report_progress(0, 1, "Transcribing the selected audio clip", 0.0)
        transcript = audio.transcribe_line(str(data.audio_path), data.language)
        report_progress(1, 1, "Transcription complete", 0.0)
        return TextOutputData(text=transcript)
