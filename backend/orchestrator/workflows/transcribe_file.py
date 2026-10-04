from pathlib import Path

from orchestrator.task_data.base import FileOutputData, TaskData
from orchestrator.task_data.general import TranscribeFileData, TranscribedSubtitleData
from orchestrator.task_orchestrator import TaskOrchestrator
from orchestrator.tasks.task_transcribe_file import TaskTranscribeFile
from orchestrator.workflows import remove_files
from orchestrator.workflows.file_output import save_subtitles, transcribed_filename

WORKFLOW = "transcribe_file"


def start_transcribe_file(audio_path: Path, original_filename: str, language: str) -> None:
    """Start transcribing a full audio file; the temp audio file is deleted when the run ends."""
    data = TranscribeFileData(audio_path=audio_path, original_filename=original_filename, language=language)
    TaskOrchestrator.get_instance().run(
        WORKFLOW, [TaskTranscribeFile()], data, finish=_finish, cleanup=remove_files(audio_path),
    )


def _finish(data: TaskData) -> FileOutputData:
    """Save the subtitles as <name>.<language>.ass under outputs/transcribed/."""
    if not isinstance(data, TranscribedSubtitleData):
        raise TypeError(f"{WORKFLOW} finish expects TranscribedSubtitleData, got {type(data).__name__}.")
    filename = transcribed_filename(data.original_filename, data.language)
    return FileOutputData(output_path=save_subtitles(data.subtitles, "transcribed", filename))
