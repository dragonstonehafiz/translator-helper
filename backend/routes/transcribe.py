"""
Transcription routes.
"""

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile

from orchestrator.task_transcribe_file import TaskTranscribeFile
from orchestrator.task_transcribe_line import TaskTranscribeLine

from .shared import (
    AUDIO_TASK_TYPES,
    TRANSCRIBE_TASK_TYPES,
    model_manager,
    read_latest,
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
    if task_orchestrator.is_running():
        return {"status": "error", "message": "Transcription is already running"}
    if not model_manager.is_audio_ready():
        return {"status": "error", "message": "Audio model not loaded"}

    try:
        tmp_file_path = await save_upload_to_temp(file)
        background_tasks.add_task(
            run_single_task,
            TaskTranscribeLine(),
            {"file_path": tmp_file_path, "language": language},
        )
        return {"status": "processing", "message": "Transcription started"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@router.post("/transcribe-file")
async def api_transcribe_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form(...),
):
    if task_orchestrator.is_running():
        return {"status": "error", "message": "Transcription is already running"}
    if not model_manager.is_audio_ready():
        return {"status": "error", "message": "Audio model not loaded"}

    try:
        tmp_file_path = await save_upload_to_temp(file)
        background_tasks.add_task(
            run_single_task,
            TaskTranscribeFile(),
            {"file_path": tmp_file_path, "language": language, "original_filename": file.filename},
        )
        return {"status": "processing", "message": "File transcription started"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@router.get("/result")
async def get_transcription_result():
    active_task_type = task_orchestrator.get_active_task_type()
    if task_orchestrator.is_running() and active_task_type in AUDIO_TASK_TYPES:
        return {"status": "processing", "result": None, "error": None}

    record, _ = read_latest(TRANSCRIBE_TASK_TYPES)
    if record is None:
        return {"status": "idle", "result": None, "error": None}

    if record["status"] == "error":
        return {"status": "error", "result": None, "error": record["error"], "message": record["error"]}
    if record["status"] == "complete":
        return {"status": "complete", "result": record["result"], "error": None}
    return {"status": "processing", "result": None, "error": None}
