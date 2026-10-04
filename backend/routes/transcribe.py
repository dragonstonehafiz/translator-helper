"""
Transcription routes.
"""

from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from models.manager import ModelManager
from orchestrator.task_orchestrator import TaskOrchestrator
from orchestrator.workflows.transcribe_clip import start_transcribe_clip
from orchestrator.workflows.transcribe_file import start_transcribe_file
from utils.api_response import error_response, processing_response

from .shared import remove_temp_files, save_upload_to_temp

router = APIRouter(prefix="/transcribe")


def _busy_or_unready() -> dict | None:
    """Return an error envelope if a workflow is running or the audio model is not loaded, else None."""
    if TaskOrchestrator.get_instance().get_running_state() is not None:
        return error_response("Transcription is already running")
    if not ModelManager.get_instance().is_audio_ready():
        return error_response("Audio model not loaded")
    return None


@router.post("/transcribe-line")
async def api_transcribe_line(
    file: UploadFile = File(...),
    language: str = Form(...),
):
    """Upload an audio clip and start transcribing it."""
    rejection = _busy_or_unready()
    if rejection:
        return rejection
    tmp_path: Path | None = None
    try:
        tmp_path = await save_upload_to_temp(file)
        start_transcribe_clip(audio_path=tmp_path, language=language)
    except Exception as exc:
        remove_temp_files(tmp_path)
        return error_response(str(exc))
    return processing_response({"workflow": "transcribe_clip"}, "Transcription started")


@router.post("/transcribe-file")
async def api_transcribe_file(
    file: UploadFile = File(...),
    language: str = Form(...),
):
    """Upload an audio file and start transcribing it to subtitles."""
    rejection = _busy_or_unready()
    if rejection:
        return rejection
    tmp_path: Path | None = None
    try:
        tmp_path = await save_upload_to_temp(file)
        start_transcribe_file(audio_path=tmp_path, original_filename=file.filename or "audio.wav", language=language)
    except Exception as exc:
        remove_temp_files(tmp_path)
        return error_response(str(exc))
    return processing_response({"workflow": "transcribe_file"}, "File transcription started")
