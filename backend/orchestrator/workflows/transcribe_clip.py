from pathlib import Path

from orchestrator.task_data.base import TaskData
from orchestrator.task_data.general import TranscribeClipData
from orchestrator.task_orchestrator import TaskOrchestrator
from orchestrator.tasks.task_transcribe_clip import TaskTranscribeClip
from orchestrator.workflows import remove_files

WORKFLOW = "transcribe_clip"


def start_transcribe_clip(audio_path: Path, language: str) -> None:
    """Start transcribing a clip; the temp audio file is deleted when the run ends."""
    data = TranscribeClipData(audio_path=audio_path, language=language)
    TaskOrchestrator.get_instance().run(
        WORKFLOW, [TaskTranscribeClip()], data, finish=_finish, cleanup=remove_files(audio_path),
    )


def _finish(data: TaskData) -> TaskData:
    """The transcript is already the final result."""
    return data
