"""Data for the translate_file and review_file workflows; review data extends translation data."""

from dataclasses import dataclass

import pysubs2

from orchestrator.task_data.base import TaskData
from orchestrator.task_data.library_types import LibraryContext, SeriesSnapshot


@dataclass(kw_only=True)
class TranslationBatch:
    """A contiguous, inclusive, one-based range of subtitle lines translated or reviewed together."""

    start_index: int
    end_index: int
    reason: str

    @property
    def size(self) -> int:
        """Return the number of lines in the batch."""
        return self.end_index - self.start_index + 1

    def to_log(self) -> dict[str, int | str]:
        """Return the batch as a JSON-ready dict including its size."""
        return {"start_index": self.start_index, "end_index": self.end_index, "reason": self.reason, "size": self.size}


@dataclass(kw_only=True)
class TranslationData(TaskData):
    """Prepared input of a file translation; also the base of review data."""

    original_filename: str
    subtitles: pysubs2.SSAFile
    input_lang: str
    output_lang: str
    batch_size: int
    context: dict[str, str]
    series: SeriesSnapshot | None
    library_context: LibraryContext | None

    def run_label(self) -> str | None:
        """Use the uploaded filename for the log folder."""
        return self.original_filename


@dataclass(kw_only=True)
class PlannedTranslationData(TranslationData):
    """Translation data with its batch plan."""

    batches: list[TranslationBatch]


@dataclass(kw_only=True)
class TranslatedSubtitleData(TaskData):
    """Translated subtitles with the metadata needed to name the saved file."""

    subtitles: pysubs2.SSAFile
    original_filename: str
    output_lang: str


@dataclass(kw_only=True)
class ReviewData(TranslationData):
    """Prepared input of a review: the original subtitles plus the translation being reviewed."""

    translated_filename: str
    translated_subtitles: pysubs2.SSAFile

    def run_label(self) -> str | None:
        """Use the translated filename for the log folder."""
        return self.translated_filename or self.original_filename


@dataclass(kw_only=True)
class PlannedReviewData(ReviewData):
    """Review data with its batch plan."""

    batches: list[TranslationBatch]


@dataclass(kw_only=True)
class Correction:
    """A translated line the reviewer flagged, with the reason."""

    index: int
    reason: str


@dataclass(kw_only=True)
class ReviewedData(PlannedReviewData):
    """Review data with the merged list of flagged lines."""

    corrections: list[Correction]


@dataclass(kw_only=True)
class CorrectedSubtitleData(TaskData):
    """Corrected translated subtitles with the metadata needed to name the saved file."""

    subtitles: pysubs2.SSAFile
    translated_filename: str
    corrected_count: int
