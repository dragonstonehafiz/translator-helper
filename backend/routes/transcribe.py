"""
Transcription routes.
"""

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile

from orchestrator.tasks.task_transcribe_file import TaskTranscribeFile
from orchestrator.tasks.task_transcribe_line import TaskTranscribeLine
from utils.api_response import error_response, processing_response

from .shared import (
    model_manager,
    run_single_task,
    save_upload_to_temp,
    task_orchestrator,
)

router = APIRouter(prefix="/transcribe")


@router.post("/transcribe-line")
async def api_transcribe_line(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form(...),
):
    """Upload an audio file and start a single-line transcription task in the background."""
    if task_orchestrator.is_running():
        return error_response("Transcription is already running")
    if not model_manager.is_audio_ready():
        return error_response("Audio model not loaded")

    try:
        tmp_file_path = await save_upload_to_temp(file)
        background_tasks.add_task(
            run_single_task,
            TaskTranscribeLine(),
            {"file_path": tmp_file_path, "language": language},
        )
        return processing_response({"task_type": TaskTranscribeLine.TASK_TYPE}, "Transcription started")
    except Exception as exc:
        return error_response(str(exc))


@router.post("/transcribe-file")
async def api_transcribe_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form(...),
):
    """Upload an audio file and start a full-file transcription task in the background."""
    if task_orchestrator.is_running():
        return error_response("Transcription is already running")
    if not model_manager.is_audio_ready():
        return error_response("Audio model not loaded")

    try:
        tmp_file_path = await save_upload_to_temp(file)
        background_tasks.add_task(
            run_single_task,
            TaskTranscribeFile(),
            {"file_path": tmp_file_path, "language": language, "original_filename": file.filename},
        )
        return processing_response({"task_type": TaskTranscribeFile.TASK_TYPE}, "File transcription started")
    except Exception as exc:
        return error_response(str(exc))
