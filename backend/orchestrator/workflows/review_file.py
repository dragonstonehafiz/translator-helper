from pathlib import Path

from orchestrator.review_file.task_prepare_review_batches import TaskPrepareReviewBatches
from orchestrator.review_file.task_retranslate_reviewed_lines import TaskRetranslateReviewedLines
from orchestrator.review_file.task_review_translated_batches import TaskReviewTranslatedBatches
from orchestrator.task_data.base import ReviewFileOutputData, TaskData
from orchestrator.task_data.library_types import SeriesSnapshot
from orchestrator.task_data.translation import CorrectedSubtitleData, PlannedReviewData, ReviewData
from orchestrator.task_orchestrator import TaskOrchestrator
from orchestrator.translate_file.task_select_library_context import TaskSelectLibraryContext
from orchestrator.workflows import remove_files
from orchestrator.workflows.file_output import reviewed_filename, save_subtitles
from utils.subtitles import load_subtitles

WORKFLOW = "review_file"


def start_review_file(
    file_path: Path,
    translated_file_path: Path,
    original_filename: str,
    translated_filename: str,
    input_lang: str,
    output_lang: str,
    batch_size: int,
    series: SeriesSnapshot | None,
) -> None:
    """Load and check both files before any LLM call, then start the review; both temp files are deleted when the run ends."""
    subtitles = load_subtitles(str(file_path))
    translated_subtitles = load_subtitles(str(translated_file_path))
    if len(subtitles) != len(translated_subtitles):
        raise ValueError("Original and translated subtitle files must contain the same number of subtitle lines.")

    data = ReviewData(
        original_filename=original_filename,
        subtitles=subtitles,
        input_lang=input_lang,
        output_lang=output_lang,
        batch_size=max(1, batch_size),
        context={},
        series=series,
        library_context=None,
        translated_filename=translated_filename,
        translated_subtitles=translated_subtitles,
    )
    tasks = [
        TaskPrepareReviewBatches(),
        TaskSelectLibraryContext(PlannedReviewData),
        TaskReviewTranslatedBatches(),
        TaskRetranslateReviewedLines(),
    ]
    TaskOrchestrator.get_instance().run(
        WORKFLOW, tasks, data, finish=_finish, cleanup=remove_files(file_path, translated_file_path),
    )


def _finish(data: TaskData) -> ReviewFileOutputData:
    """Save the corrected file as <translated stem>.corrected<suffix> under outputs/reviewed/."""
    if not isinstance(data, CorrectedSubtitleData):
        raise TypeError(f"{WORKFLOW} finish expects CorrectedSubtitleData, got {type(data).__name__}.")
    output_path = save_subtitles(data.subtitles, "reviewed", reviewed_filename(data.translated_filename))
    return ReviewFileOutputData(output_path=output_path, corrected_count=data.corrected_count)
