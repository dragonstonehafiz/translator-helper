"""
Context generation routes.
"""

import json
import os

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile

from orchestrator.task_generate_character_list import TaskGenerateCharacterList
from orchestrator.task_generate_recap import TaskGenerateRecap
from orchestrator.task_generate_summary import TaskGenerateSummary
from orchestrator.task_generate_synopsis import TaskGenerateSynopsis

from .shared import (
    CONTEXT_TASK_TYPES,
    GenerateRecapRequest,
    SaveContextRequest,
    build_task_response,
    ensure_task_type,
    get_files_dir,
    model_manager,
    parse_json_form,
    run_single_task,
    save_upload_to_temp,
    task_orchestrator,
)

router = APIRouter(prefix="/context")


@router.post("/generate-character-list")
async def api_generate_character_list(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context: str = Form("{}"),
):
    if not model_manager.is_llm_ready():
        return {"status": "error", "message": "LLM not loaded"}
    if task_orchestrator.is_running():
        return {"status": "error", "message": "Context generation already running"}

    tmp_path = await save_upload_to_temp(file)
    context_dict = parse_json_form(context)
    background_tasks.add_task(
        run_single_task,
        TaskGenerateCharacterList(),
        {"file_path": tmp_path, "context": context_dict, "input_lang": input_lang, "output_lang": output_lang},
    )
    return {"status": "processing", "message": "Character list generation started"}


@router.post("/generate-high-level-summary")
async def api_generate_high_level_summary(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context: str = Form("{}"),
):
    if not model_manager.is_llm_ready():
        return {"status": "error", "message": "LLM not loaded"}
    if task_orchestrator.is_running():
        return {"status": "error", "message": "Context generation already running"}

    tmp_path = await save_upload_to_temp(file)
    context_dict = parse_json_form(context)
    background_tasks.add_task(
        run_single_task,
        TaskGenerateSummary(),
        {"file_path": tmp_path, "context": context_dict, "input_lang": input_lang, "output_lang": output_lang},
    )
    return {"status": "processing", "message": "Summary generation started"}


@router.post("/generate-synopsis")
async def api_generate_synopsis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context: str = Form("{}"),
):
    if not model_manager.is_llm_ready():
        return {"status": "error", "message": "LLM not loaded"}
    if task_orchestrator.is_running():
        return {"status": "error", "message": "Context generation already running"}

    tmp_path = await save_upload_to_temp(file)
    context_dict = parse_json_form(context)
    background_tasks.add_task(
        run_single_task,
        TaskGenerateSynopsis(),
        {"file_path": tmp_path, "context": context_dict, "input_lang": input_lang, "output_lang": output_lang},
    )
    return {"status": "processing", "message": "Synopsis generation started"}


@router.post("/generate-recap")
async def api_generate_recap(request: GenerateRecapRequest, background_tasks: BackgroundTasks):
    if not model_manager.is_llm_ready():
        return {"status": "error", "message": "LLM not loaded"}
    if task_orchestrator.is_running():
        return {"status": "error", "message": "Context generation already running"}

    background_tasks.add_task(
        run_single_task,
        TaskGenerateRecap(),
        {"contexts": request.contexts, "input_lang": request.input_lang, "output_lang": request.output_lang},
    )
    return {"status": "processing", "message": "Recap generation started"}


@router.post("/save")
async def save_context(request: SaveContextRequest):
    safe_name = os.path.basename(request.filename)
    if not safe_name.endswith(".json"):
        raise HTTPException(status_code=400, detail="Filename must end with .json")
    output_dir = get_files_dir("context-files")
    file_path = output_dir / safe_name
    with open(file_path, "w", encoding="utf-8") as file_handle:
        json.dump(request.context, file_handle, ensure_ascii=False, indent=2)
    return {"status": "success"}


@router.get("/result")
async def get_context_result(task_type: str = Query(...)):
    ensure_task_type(task_type, CONTEXT_TASK_TYPES)
    return build_task_response(task_type)
