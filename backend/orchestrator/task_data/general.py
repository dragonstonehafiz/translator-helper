"""Data for the single-task workflows: translate_line, transcribe_clip and transcribe_file."""

from dataclasses import dataclass
from pathlib import Path

import pysubs2

from orchestrator.task_data.base import TaskData


@dataclass(kw_only=True)
class TranslateLineData(TaskData):
    """Input of a one-line translation."""

    text: str
    context: dict[str, str]
    input_lang: str
    output_lang: str


@dataclass(kw_only=True)
class TranscribeClipData(TaskData):
    """Input of a clip transcription: a managed temp audio file."""

    audio_path: Path
    language: str


@dataclass(kw_only=True)
class TranscribeFileData(TaskData):
    """Input of a file transcription: a managed temp audio file and the name it was uploaded with."""

    audio_path: Path
    original_filename: str
    language: str

    def run_label(self) -> str | None:
        """Use the uploaded filename for the log folder."""
        return self.original_filename


@dataclass(kw_only=True)
class TranscribedSubtitleData(TaskData):
    """Subtitles produced by file transcription, with the metadata needed to name the saved file."""

    subtitles: pysubs2.SSAFile
    original_filename: str
    language: str
