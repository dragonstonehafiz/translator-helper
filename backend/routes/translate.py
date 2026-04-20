"""
Translation routes.
"""

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile

from orchestrator.task_translate_file import TaskTranslateFile
from orchestrator.task_translate_line import TaskTranslateLine
from utils.api_response import error_response, processing_response

from .shared import (
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
        return error_response("Translation is already running")
    if not model_manager.is_llm_ready():
        return error_response("LLM not loaded")

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
        return processing_response({"task_type": TaskTranslateLine.TASK_TYPE}, "Translation started")
    except Exception as exc:
        return error_response(str(exc))


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
        return error_response("Translation is already running")
    if not model_manager.is_llm_ready():
        return error_response("LLM not loaded")

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
        return processing_response({"task_type": TaskTranslateFile.TASK_TYPE}, "Translation started")
    except Exception as exc:
        return error_response(str(exc))
