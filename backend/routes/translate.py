"""
Translation routes.
"""

from datetime import datetime
import os

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile

from orchestrator.task_plan_translation_batches import TaskPlanTranslationBatches
from orchestrator.task_plan_translation_review_batches import TaskPlanTranslationReviewBatches
from orchestrator.task_retranslate_reviewed_lines import TaskRetranslateReviewedLines
from orchestrator.task_review_translated_batches import TaskReviewTranslatedBatches
from orchestrator.task_split_oversized_batches import TaskSplitOversizedBatches
from orchestrator.task_translate_file import TaskTranslateFile
from orchestrator.task_translate_line import TaskTranslateLine
from utils.logger import setup_logger
from utils.api_response import error_response, processing_response

from .shared import (
    OUTPUTS_DIR,
    model_manager,
    parse_json_form,
    progress_handler,
    result_handler,
    run_single_task,
    save_upload_to_temp,
    task_orchestrator,
)

router = APIRouter(prefix="/translate")
logger = setup_logger()


def _safe_log_filename(filename: str) -> str:
    original_filename = os.path.basename(str(filename or "subtitles")).strip() or "subtitles"
    return "".join(
        char if char.isalnum() or char in "._-" else "_" for char in original_filename
    ).strip("._") or "subtitles"


def run_translation_file_chain(data: dict):
    final_task_type = TaskTranslateFile.TASK_TYPE
    try:
        data = dict(data)
        safe_filename = _safe_log_filename(str(data.get("original_filename", "subtitles")))
        log_dir = OUTPUTS_DIR / "translate-file-logs" / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe_filename}"
        log_dir.mkdir(parents=True, exist_ok=True)
        data["log_dir"] = str(log_dir)
        result_handler.set_processing(final_task_type)
        progress_handler.set(
            final_task_type,
            {
                "current": 0,
                "total": 1,
                "status": "Planning translation batches",
                "eta_seconds": 0.0,
            },
        )
        task_orchestrator.clear_tasks()
        task_orchestrator.add_task(TaskPlanTranslationBatches())
        task_orchestrator.add_task(TaskSplitOversizedBatches())
        task_orchestrator.add_task(TaskTranslateFile())
        task_orchestrator.run_tasks(initial_data=data)
    except Exception as exc:
        logger.error("Task execution failed (%s): %s", final_task_type, exc, exc_info=True)
        result_handler.set_error(final_task_type, str(exc))


def run_review_translated_file_chain(data: dict):
    final_task_type = TaskRetranslateReviewedLines.TASK_TYPE
    temp_paths = []
    try:
        data = dict(data)
        temp_paths = [
            str(data.get("file_path", "")),
            str(data.get("translated_file_path", "")),
        ]
        safe_filename = _safe_log_filename(str(data.get("translated_filename") or data.get("original_filename") or "subtitles"))
        log_dir = OUTPUTS_DIR / "review-file-logs" / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe_filename}"
        log_dir.mkdir(parents=True, exist_ok=True)
        data["log_dir"] = str(log_dir)
        result_handler.set_processing(final_task_type)
        progress_handler.set(
            final_task_type,
            {
                "current": 0,
                "total": 1,
                "status": "Planning review batches",
                "eta_seconds": 0.0,
            },
        )
        task_orchestrator.clear_tasks()
        task_orchestrator.add_task(TaskPlanTranslationReviewBatches())
        task_orchestrator.add_task(TaskReviewTranslatedBatches())
        task_orchestrator.add_task(TaskRetranslateReviewedLines())
        task_orchestrator.run_tasks(initial_data=data)
    except Exception as exc:
        logger.error("Task execution failed (%s): %s", final_task_type, exc, exc_info=True)
        result_handler.set_error(final_task_type, str(exc))
    finally:
        for temp_path in temp_paths:
            if temp_path:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass


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


@router.post("/review-translated-file")
async def api_review_translated_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    translated_file: UploadFile = File(...),
    context: str = Form("{}"),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    batch_size: int = Form(50),
):
    if task_orchestrator.is_running():
        return error_response("Translation review is already running")
    if not model_manager.is_llm_ready():
        return error_response("LLM not loaded")

    try:
        context_dict = parse_json_form(context)
        tmp_file_path = await save_upload_to_temp(file)
        tmp_translated_file_path = await save_upload_to_temp(translated_file)
        background_tasks.add_task(
            run_review_translated_file_chain,
            {
                "file_path": tmp_file_path,
                "translated_file_path": tmp_translated_file_path,
                "original_filename": file.filename,
                "translated_filename": translated_file.filename,
                "context": context_dict,
                "input_lang": input_lang,
                "output_lang": output_lang,
                "batch_size": batch_size,
            },
        )
        return processing_response({"task_type": TaskRetranslateReviewedLines.TASK_TYPE}, "Translation review started")
    except Exception as exc:
        return error_response(str(exc))
