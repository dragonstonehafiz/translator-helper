"""
Translation routes.
"""

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile

from orchestrator.task_translate_file import TaskTranslateFile
from orchestrator.task_translate_line import TaskTranslateLine

from .shared import (
    TRANSLATE_TASK_TYPES,
    model_manager,
    parse_json_form,
    progress_handler,
    read_latest,
    run_single_task,
    save_upload_to_temp,
    task_orchestrator,
)

router = APIRouter(prefix="/translate")


@router.post("/translate-line")
async def api_translate_line(
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    context: str = Form("{}"),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
):
    if task_orchestrator.is_running():
        return {"status": "error", "message": "Translation is already running"}
    if not model_manager.is_llm_ready():
        return {"status": "error", "message": "LLM not loaded"}

    try:
        context_dict = parse_json_form(context)
        background_tasks.add_task(
            run_single_task,
            TaskTranslateLine(),
            {
                "text": text,
                "context": context_dict,
                "input_lang": input_lang,
                "output_lang": output_lang,
            },
        )
        return {"status": "processing", "message": "Translation started"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@router.post("/translate-file")
async def api_translate_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    context: str = Form("{}"),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    batch_size: int = Form(3),
):
    if task_orchestrator.is_running():
        return {"status": "error", "message": "Translation is already running"}
    if not model_manager.is_llm_ready():
        return {"status": "error", "message": "LLM not loaded"}

    try:
        context_dict = parse_json_form(context)
        tmp_file_path = await save_upload_to_temp(file)
        background_tasks.add_task(
            run_single_task,
            TaskTranslateFile(),
            {
                "file_path": tmp_file_path,
                "original_filename": file.filename,
                "context": context_dict,
                "input_lang": input_lang,
                "output_lang": output_lang,
                "batch_size": batch_size,
            },
        )
        return {"status": "processing", "message": "Translation started"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@router.get("/result")
async def get_translation_result():
    active_task_type = task_orchestrator.get_active_task_type()
    if task_orchestrator.is_running() and active_task_type in set(TRANSLATE_TASK_TYPES):
        active_progress = progress_handler.get(active_task_type) if active_task_type else None
        if active_progress and active_progress.get("total", 0) > 0:
            return {"status": "translating", "result": None, "error": None, "progress": active_progress}
        return {"status": "processing", "result": None, "error": None}

    record, progress = read_latest(TRANSLATE_TASK_TYPES)
    if record is None:
        return {"status": "idle", "result": None, "error": None}

    if record["status"] == "error":
        return {"status": "error", "result": None, "message": record["error"], "progress": progress}
    if record["status"] == "complete":
        return {"status": "complete", "result": record["result"], "progress": progress}
    if progress:
        return {"status": "translating", "result": None, "error": None, "progress": progress}
    return {"status": "processing", "result": None, "error": None}
