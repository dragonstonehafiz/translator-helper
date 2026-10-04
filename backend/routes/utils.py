"""
Utility and backend status routes.
"""

from fastapi import APIRouter, File, UploadFile
from fastapi.concurrency import run_in_threadpool

from models.config import TextOption
from models.manager import ModelManager
from orchestrator.task_orchestrator import TaskOrchestrator
from utils.api_response import error_response, success_response
from utils.subtitles import analyze_subtitle_file

from .shared import UpdateSettingsRequest, remove_temp_files, save_upload_to_temp

router = APIRouter(prefix="/utils")


def _status_values(client) -> list[dict]:
    """Return a client's non-secret setting values as label/value pairs for the status display."""
    if client is None:
        return []
    return [
        {"key": f.name, "label": f.label, "value": f.value}
        for f in client.config.get_fields()
        if not (isinstance(f.option, TextOption) and f.option.password)
    ]


def _schema(client) -> dict | None:
    """Return a client's Settings-page schema, or None if the client could not be created."""
    return client.config.to_frontend() if client is not None else None


@router.get("/running")
async def get_running_status():
    """Return the running workflow and its active stage, and which models are in use or loading."""
    model_manager = ModelManager.get_instance()
    state = TaskOrchestrator.get_instance().get_running_state()
    return success_response({
        "running": state is not None,
        "workflow": state.workflow if state else None,
        "active_task": state.active_task if state else None,
        "running_llm": model_manager.llm_in_use,
        "running_audio": model_manager.audio_in_use,
        "running_search": model_manager.search_in_use,
        "loading_llm_model": model_manager.loading_llm_model,
        "loading_audio_model": model_manager.loading_audio_model,
        "loading_search_model": model_manager.loading_search_model,
    })


@router.get("/server-variables")
async def get_server_variables():
    """Return current setting values, readiness and loading errors for the three model clients."""
    model_manager = ModelManager.get_instance()
    return success_response({
        "audio": _status_values(model_manager.get_audio_client()),
        "llm": _status_values(model_manager.get_llm_client()),
        "search": _status_values(model_manager.get_search_client()),
        "llm_ready": model_manager.is_llm_ready(),
        "audio_ready": model_manager.is_audio_ready(),
        "search_ready": model_manager.is_search_ready(),
        "llm_loading_error": model_manager.llm_loading_error,
        "audio_loading_error": model_manager.audio_loading_error,
        "search_loading_error": model_manager.search_loading_error,
    })


@router.get("/settings-schema")
async def get_settings_schema():
    """Return the Settings-page schema for each model client; a group is null if its client could not be created."""
    model_manager = ModelManager.get_instance()
    return success_response({
        "audio": _schema(model_manager.get_audio_client()),
        "llm": _schema(model_manager.get_llm_client()),
        "search": _schema(model_manager.get_search_client()),
    })


async def _load(load, settings: dict, message: str):
    """Run a manager load in a worker thread and turn a rejection or failure into an error envelope."""
    try:
        await run_in_threadpool(load, settings or None)
    except Exception as exc:
        return error_response(str(exc))
    return success_response(message=message)


@router.post("/load-audio-model")
async def load_audio_model(request: UpdateSettingsRequest):
    """Save submitted audio settings and initialize the audio model."""
    return await _load(ModelManager.get_instance().load_audio_model, request.settings, "Audio model loaded")


@router.post("/load-llm-model")
async def load_llm_model(request: UpdateSettingsRequest):
    """Save submitted LLM settings and initialize the LLM."""
    return await _load(ModelManager.get_instance().load_llm_model, request.settings, "LLM loaded")


@router.post("/load-search-model")
async def load_search_model(request: UpdateSettingsRequest):
    """Save submitted search settings and initialize web search."""
    return await _load(ModelManager.get_instance().load_search_model, request.settings, "Search model loaded")


@router.post("/get-subtitle-file-info")
async def api_get_subtitle_file_info(file: UploadFile = File(...)):
    """Upload a subtitle file and return dialogue statistics (line count, character count, average length)."""
    allowed_extensions = {".ass", ".srt"}
    filename_lower = file.filename.lower()
    if not any(filename_lower.endswith(ext) for ext in allowed_extensions):
        return error_response("Only .ass or .srt files are supported for this endpoint")

    tmp_path = None
    try:
        tmp_path = await save_upload_to_temp(file, default_suffix=".ass")
        return success_response(analyze_subtitle_file(str(tmp_path)))
    except Exception as exc:
        return error_response(str(exc))
    finally:
        remove_temp_files(tmp_path)
