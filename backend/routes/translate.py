"""
Translation routes.
"""

from fastapi import APIRouter, BackgroundTasks, File, Form, Query, UploadFile

from orchestrator.task_translate_file import TaskTranslateFile
from orchestrator.task_translate_line import TaskTranslateLine

from .shared import (
    TRANSLATE_TASK_TYPES,
    build_task_response,
    ensure_task_type,
    model_manager,
    parse_json_form,
    run_translation_file_chain,
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
            run_translation_file_chain,
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
async def get_translation_result(task_type: str = Query(...)):
    ensure_task_type(task_type, TRANSLATE_TASK_TYPES)
    return build_task_response(task_type)
