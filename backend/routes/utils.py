"""
Utility and backend status routes.
"""

import os

from fastapi import APIRouter, BackgroundTasks, File, UploadFile

from .shared import (
    AUDIO_TASK_TYPES,
    LLM_TASK_TYPES,
    UpdateSettingsRequest,
    analyze_subtitle_file,
    model_manager,
    save_upload_to_temp,
    task_orchestrator,
)

router = APIRouter(prefix="/utils")


@router.get("/running")
async def get_running_status():
    active_task_type = task_orchestrator.get_active_task_type()
    running = task_orchestrator.is_running()
    return {
        "running_llm": bool(running and active_task_type in LLM_TASK_TYPES),
        "running_audio": bool(running and active_task_type in AUDIO_TASK_TYPES),
        "loading_audio_model": model_manager.loading_audio_model,
        "loading_llm_model": model_manager.loading_llm_model,
    }


@router.get("/server-variables")
async def get_server_variables():
    llm_client = model_manager.get_llm_client()
    audio_client = model_manager.get_audio_client()
    return {
        "audio": (audio_client.get_server_variables() if audio_client else []),
        "llm": (llm_client.get_server_variables() if llm_client else []),
        "llm_ready": model_manager.is_llm_ready(),
        "audio_ready": model_manager.is_audio_ready(),
        "llm_loading_error": model_manager.llm_loading_error,
        "audio_loading_error": model_manager.audio_loading_error,
    }


@router.get("/settings-schema")
async def get_settings_schema():
    audio_client = model_manager.get_audio_client()
    llm_client = model_manager.get_llm_client()
    audio_schema = audio_client.get_settings_schema() if audio_client else {}
    llm_schema = llm_client.get_settings_schema() if llm_client else {}
    return {"audio": audio_schema, "llm": llm_schema}


@router.post("/load-audio-model")
async def load_audio_model(request: UpdateSettingsRequest, background_tasks: BackgroundTasks):
    if model_manager.loading_audio_model:
        return {"status": "error", "message": "Audio model is already loading"}
    model_manager.update_audio_settings(request.settings or {})
    background_tasks.add_task(model_manager.load_audio_model)
    return {"status": "loading", "message": "Audio model loading started"}


@router.post("/load-llm-model")
async def load_llm_model(request: UpdateSettingsRequest, background_tasks: BackgroundTasks):
    if model_manager.loading_llm_model:
        return {"status": "error", "message": "LLM is already loading"}
    model_manager.update_llm_settings(request.settings or {})
    background_tasks.add_task(model_manager.load_llm_model)
    return {"status": "loading", "message": "LLM loading started"}


@router.post("/get-subtitle-file-info")
async def api_get_subtitle_file_info(file: UploadFile = File(...)):
    allowed_extensions = {".ass", ".srt"}
    filename_lower = file.filename.lower()
    if not any(filename_lower.endswith(ext) for ext in allowed_extensions):
        return {"status": "error", "message": "Only .ass or .srt files are supported for this endpoint"}

    tmp_path = ""
    try:
        tmp_path = await save_upload_to_temp(file, default_suffix=".ass")
        stats = analyze_subtitle_file(tmp_path)
        return {"status": "success", "result": stats}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
