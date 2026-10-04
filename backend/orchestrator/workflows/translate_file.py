from pathlib import Path

from orchestrator.task_data.base import FileOutputData, TaskData
from orchestrator.task_data.library_types import SeriesSnapshot
from orchestrator.task_data.translation import PlannedTranslationData, TranslatedSubtitleData, TranslationData
from orchestrator.task_orchestrator import TaskOrchestrator
from orchestrator.translate_file.task_prepare_translation_batches import TaskPrepareTranslationBatches
from orchestrator.translate_file.task_select_library_context import TaskSelectLibraryContext
from orchestrator.translate_file.task_translate_batches import TaskTranslateBatches
from orchestrator.workflows import remove_files
from orchestrator.workflows.file_output import save_subtitles, translated_filename
from utils.subtitles import load_subtitles

WORKFLOW = "translate_file"


def start_translate_file(
    file_path: Path,
    original_filename: str,
    input_lang: str,
    output_lang: str,
    batch_size: int,
    series: SeriesSnapshot | None,
) -> None:
    """Load the subtitles once, then start the translation; the temp file is deleted when the run ends."""
    data = TranslationData(
        original_filename=original_filename,
        subtitles=load_subtitles(str(file_path)),
        input_lang=input_lang,
        output_lang=output_lang,
        batch_size=max(1, batch_size),
        context={},
        series=series,
        library_context=None,
    )
    tasks = [
        TaskPrepareTranslationBatches(),
        TaskSelectLibraryContext(PlannedTranslationData),
        TaskTranslateBatches(),
    ]
    TaskOrchestrator.get_instance().run(WORKFLOW, tasks, data, finish=_finish, cleanup=remove_files(file_path))


def _finish(data: TaskData) -> FileOutputData:
    """Save the translation as <name>.<language>.<ext> under outputs/translated/."""
    if not isinstance(data, TranslatedSubtitleData):
        raise TypeError(f"{WORKFLOW} finish expects TranslatedSubtitleData, got {type(data).__name__}.")
    filename = translated_filename(data.original_filename, data.output_lang)
    return FileOutputData(output_path=save_subtitles(data.subtitles, "translated", filename))
