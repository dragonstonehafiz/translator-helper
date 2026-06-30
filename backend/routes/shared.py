"""
Shared helpers and state for backend route modules.
"""

from pathlib import Path
from typing import Any
from datetime import datetime
import json
import os
import tempfile

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel

from models.model_manager import ModelManager
from orchestrator.progress_handler import ProgressHandler
from orchestrator.result_handler import ResultHandler
from orchestrator.library.task_check_against_library import TaskCheckAgainstLibrary
from orchestrator.library.task_deduplicate_proposals import TaskDeduplicateProposals
from orchestrator.library.task_generate_library_proposals import TaskGenerateLibraryProposals
from orchestrator.library.task_generate_search_queries import TaskGenerateSearchQueries
from orchestrator.library.task_scan_subtitle_file import TaskScanSubtitleFile
from orchestrator.library.task_web_search import TaskWebSearch
from orchestrator.task_orchestrator import TaskOrchestrator
from orchestrator.translate_file.task_plan_translation_batches import TaskPlanTranslationBatches
from orchestrator.translate_file.task_select_library_context import TaskSelectLibraryContext
from orchestrator.review_file.task_select_library_context_for_review import TaskSelectLibraryContextForReview
from orchestrator.review_file.task_plan_translation_review_batches import TaskPlanTranslationReviewBatches
from orchestrator.review_file.task_retranslate_reviewed_lines import TaskRetranslateReviewedLines
from orchestrator.review_file.task_review_translated_batches import TaskReviewTranslatedBatches
from orchestrator.translate_file.task_split_oversized_batches import TaskSplitOversizedBatches
from orchestrator.tasks.task_transcribe_file import TaskTranscribeFile
from orchestrator.tasks.task_transcribe_line import TaskTranscribeLine
from orchestrator.translate_file.task_translate_file import TaskTranslateFile
from orchestrator.tasks.task_translate_line import TaskTranslateLine
from utils.api_response import complete_response, error_response, idle_response, processing_response, task_result_data

model_manager = ModelManager.get_instance()
task_orchestrator = TaskOrchestrator.get_instance()
result_handler = ResultHandler.get_instance()
progress_handler = ProgressHandler.get_instance()

LIBRARY_TASK_TYPES = {
    TaskScanSubtitleFile.TASK_TYPE,
    TaskCheckAgainstLibrary.TASK_TYPE,
    TaskGenerateSearchQueries.TASK_TYPE,
    TaskWebSearch.TASK_TYPE,
    TaskGenerateLibraryProposals.TASK_TYPE,
    TaskDeduplicateProposals.TASK_TYPE,
}
LLM_TASK_TYPES = {
    TaskTranslateLine.TASK_TYPE,
    TaskTranslateFile.TASK_TYPE,
    TaskPlanTranslationBatches.TASK_TYPE,
    TaskSelectLibraryContext.TASK_TYPE,
    TaskSelectLibraryContextForReview.TASK_TYPE,
    TaskPlanTranslationReviewBatches.TASK_TYPE,
    TaskReviewTranslatedBatches.TASK_TYPE,
    TaskRetranslateReviewedLines.TASK_TYPE,
    TaskSplitOversizedBatches.TASK_TYPE,
    TaskScanSubtitleFile.TASK_TYPE,
    TaskGenerateSearchQueries.TASK_TYPE,
    TaskGenerateLibraryProposals.TASK_TYPE,
}
AUDIO_TASK_TYPES = {
    TaskTranscribeLine.TASK_TYPE,
    TaskTranscribeFile.TASK_TYPE,
}
TRANSLATE_TASK_TYPES = [
    TaskTranslateLine.TASK_TYPE,
    TaskTranslateFile.TASK_TYPE,
    TaskRetranslateReviewedLines.TASK_TYPE,
]
TRANSCRIBE_TASK_TYPES = [TaskTranscribeLine.TASK_TYPE, TaskTranscribeFile.TASK_TYPE]
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"


class UpdateSettingsRequest(BaseModel):
    provider: str
    settings: dict



def run_single_task(task, data: dict):
    """Run a task through the orchestrator, writing any exception to ResultHandler as an error."""
    try:
        task_orchestrator.run_task(task, data)
    except Exception as exc:
        result_handler.set_error(task.task_type, str(exc))


def ensure_task_type(task_type: str, allowed_task_types: list[str] | set[str]) -> str:
    """Validate that task_type is in the allowed set, raising 400 if not."""
    if task_type not in allowed_task_types:
        raise HTTPException(status_code=400, detail="Invalid task_type")
    return task_type


def build_task_response(task_type: str) -> dict[str, Any]:
    """
    Build the polling response for a given task type.

    If the orchestrator is running and the task has no result yet, the task is
    in-progress (either queued or currently executing). Return the active task's
    progress from ProgressHandler so the frontend always sees live status regardless
    of which task in the chain is currently executing.
    """
    record = result_handler.get(task_type)
    progress = progress_handler.get(task_type)
    active_task_type = task_orchestrator.get_active_task_type()

    if task_orchestrator.is_running() and record is None:
        active_progress = progress_handler.get(active_task_type) if active_task_type else None
        return processing_response(task_result_data(task_type, progress=active_progress or progress))

    if record is None:
        return idle_response(task_result_data(task_type, progress=progress))

    if record["status"] == "error":
        return error_response(record["error"], task_result_data(task_type, progress=progress))

    if record["status"] == "complete":
        return complete_response(task_result_data(task_type, result=record["result"], progress=progress))

    return processing_response(task_result_data(task_type, progress=progress))


async def save_upload_to_temp(file: UploadFile, default_suffix: str = "") -> str:
    """Save an uploaded file to a temp path and return the path."""
    suffix = os.path.splitext(file.filename)[1] or default_suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(await file.read())
        return tmp_file.name


def parse_json_form(value: str, fallback: dict | None = None) -> dict:
    """Parse a JSON string from a form field, returning fallback if empty."""
    if value:
        return json.loads(value)
    return fallback or {}


def analyze_subtitle_file(file_path: str):
    """Return dialogue stats for an ASS/SRT subtitle file."""
    import pysubs2

    subs = pysubs2.load(file_path)
    total_lines = 0
    total_characters = 0
    for event in subs.events:
        text = event.plaintext.strip()
        if not text:
            continue
        speaker = event.name.strip() if event.name else ""
        line_text = f"{speaker}: {text}" if speaker else text
        total_lines += 1
        total_characters += len(line_text)

    average_characters = total_characters / total_lines if total_lines else 0
    return {
        "total_lines": str(total_lines),
        "character_count": str(total_characters),
        "average_character_count": f"{average_characters:.2f}",
    }


def get_files_dir(folder: str) -> Path:
    if not folder or not all(ch.isalnum() or ch in "-_" for ch in folder):
        raise HTTPException(status_code=400, detail="Invalid folder name")
    output_dir = OUTPUTS_DIR / folder
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def build_file_list(output_dir: Path) -> list[dict]:
    files = []
    for entry in output_dir.iterdir():
        if entry.is_file():
            stat = entry.stat()
            files.append({
                "name": entry.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    files.sort(key=lambda item: item["modified"], reverse=True)
    return files
