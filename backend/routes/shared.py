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
from orchestrator.task_generate_character_list import TaskGenerateCharacterList
from orchestrator.task_generate_summary import TaskGenerateSummary
from orchestrator.task_generate_synopsis import TaskGenerateSynopsis
from orchestrator.task_orchestrator import TaskOrchestrator
from orchestrator.task_plan_translation_batches import TaskPlanTranslationBatches
from orchestrator.task_split_oversized_batches import TaskSplitOversizedBatches
from orchestrator.task_transcribe_file import TaskTranscribeFile
from orchestrator.task_transcribe_line import TaskTranscribeLine
from orchestrator.task_translate_file import TaskTranslateFile
from orchestrator.task_translate_line import TaskTranslateLine
from utils.api_response import complete_response, error_response, idle_response, processing_response, task_result_data
from utils.logger import setup_logger

logger = setup_logger()

model_manager = ModelManager.get_instance()
task_orchestrator = TaskOrchestrator.get_instance()
result_handler = ResultHandler.get_instance()
progress_handler = ProgressHandler.get_instance()

LLM_TASK_TYPES = {
    TaskTranslateLine.TASK_TYPE,
    TaskTranslateFile.TASK_TYPE,
    TaskGenerateCharacterList.TASK_TYPE,
    TaskGenerateSynopsis.TASK_TYPE,
    TaskGenerateSummary.TASK_TYPE,
    TaskPlanTranslationBatches.TASK_TYPE,
    TaskSplitOversizedBatches.TASK_TYPE,
}
AUDIO_TASK_TYPES = {
    TaskTranscribeLine.TASK_TYPE,
    TaskTranscribeFile.TASK_TYPE,
}
CONTEXT_TASK_TYPES = [
    TaskGenerateCharacterList.TASK_TYPE,
    TaskGenerateSynopsis.TASK_TYPE,
    TaskGenerateSummary.TASK_TYPE,
]
TRANSLATE_TASK_TYPES = [TaskTranslateLine.TASK_TYPE, TaskTranslateFile.TASK_TYPE]
TRANSCRIBE_TASK_TYPES = [TaskTranscribeLine.TASK_TYPE, TaskTranscribeFile.TASK_TYPE]
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"


class UpdateSettingsRequest(BaseModel):
    provider: str
    settings: dict


class SaveContextRequest(BaseModel):
    filename: str
    context: dict


def run_single_task(task, data: dict):
    try:
        task_orchestrator.run_task(task, data)
    except Exception as exc:
        logger.error("Task execution failed (%s): %s", task.task_type, exc, exc_info=True)
        result_handler.set_error(task.task_type, str(exc))


def ensure_task_type(task_type: str, allowed_task_types: list[str] | set[str]) -> str:
    if task_type not in allowed_task_types:
        raise HTTPException(status_code=400, detail="Invalid task_type")
    return task_type


def build_task_response(task_type: str) -> dict[str, Any]:
    record = result_handler.get(task_type)
    progress = progress_handler.get(task_type)
    active_task_type = task_orchestrator.get_active_task_type()
    translate_chain_task_types = {
        TaskPlanTranslationBatches.TASK_TYPE,
        TaskSplitOversizedBatches.TASK_TYPE,
        TaskTranslateFile.TASK_TYPE,
    }

    if (
        task_type == TaskTranslateFile.TASK_TYPE
        and task_orchestrator.is_running()
        and active_task_type in translate_chain_task_types
    ):
        active_progress = progress_handler.get(active_task_type) if active_task_type else None
        return processing_response(task_result_data(task_type, progress=active_progress or progress))

    if task_orchestrator.is_running() and active_task_type == task_type:
        return processing_response(task_result_data(task_type, progress=progress))

    if record is None:
        return idle_response(task_result_data(task_type, progress=progress))

    if record["status"] == "error":
        return error_response(record["error"], task_result_data(task_type, progress=progress))

    if record["status"] == "complete":
        return complete_response(task_result_data(task_type, result=record["result"], progress=progress))

    return processing_response(task_result_data(task_type, progress=progress))


async def save_upload_to_temp(file: UploadFile, default_suffix: str = "") -> str:
    suffix = os.path.splitext(file.filename)[1] or default_suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(await file.read())
        return tmp_file.name


def parse_json_form(value: str, fallback: dict | None = None) -> dict:
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
