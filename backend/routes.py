"""
Route definitions for Translator Helper backend.
"""

from datetime import datetime
from pathlib import Path
import json
import os
import tempfile
import threading

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from models.model_manager import ModelManager
from orchestrator.progress_handler import ProgressHandler
from orchestrator.result_handler import ResultHandler
from orchestrator.task_generate_character_list import TaskGenerateCharacterList
from orchestrator.task_generate_recap import TaskGenerateRecap
from orchestrator.task_generate_summary import TaskGenerateSummary
from orchestrator.task_generate_synopsis import TaskGenerateSynopsis
from orchestrator.task_orchestrator import TaskOrchestrator
from orchestrator.task_transcribe_file import TaskTranscribeFile
from orchestrator.task_transcribe_line import TaskTranscribeLine
from orchestrator.task_translate_file import TaskTranslateFile
from orchestrator.task_translate_line import TaskTranslateLine
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger()

model_manager = ModelManager.get_instance()
task_orchestrator = TaskOrchestrator.get_instance()
result_handler = ResultHandler.get_instance()
progress_handler = ProgressHandler.get_instance()

LLM_TASK_TYPES = {
    TaskTranslateLine.TASK_TYPE,
    TaskTranslateFile.TASK_TYPE,
    TaskGenerateCharacterList.TASK_TYPE,
    TaskGenerateSynopsis.TASK_TYPE,
    TaskGenerateSummary.TASK_TYPE,
    TaskGenerateRecap.TASK_TYPE,
}
WHISPER_TASK_TYPES = {
    TaskTranscribeLine.TASK_TYPE,
    TaskTranscribeFile.TASK_TYPE,
}


def startup_load_models():
    """Reload models on startup."""
    threading.Thread(target=model_manager.load_llm_model, daemon=True).start()
    threading.Thread(target=model_manager.load_audio_model, daemon=True).start()


class UpdateSettingsRequest(BaseModel):
    provider: str
    settings: dict


class GenerateRecapRequest(BaseModel):
    contexts: list[dict]
    input_lang: str = "ja"
    output_lang: str = "en"


class SaveContextRequest(BaseModel):
    filename: str
    context: dict


def _run_single_task(task, data: dict):
    try:
        task_orchestrator.run_task(task, data)
    except Exception as exc:
        logger.error("Task execution failed (%s): %s", task.task_type, exc, exc_info=True)
        result_handler.set_error(task.task_type, str(exc))


def _read_latest(task_types: list[str]):
    record = result_handler.get_latest(task_types)
    if record is None:
        return None, None
    progress = progress_handler.get(record["task_type"])
    return record, progress


def analyze_subtitle_file(file_path: str):
    """Return dialogue stats for an ASS/SRT subtitle file."""
    import pysubs2

    subs = pysubs2.load(file_path)
    total_lines = 0
    total_characters = 0
    for event in subs.events:
        text = event.plaintext.strip()
        if not text:
            continue
        speaker = event.name.strip() if event.name else ""
        line_text = f"{speaker}: {text}" if speaker else text
        total_lines += 1
        total_characters += len(line_text)

    average_characters = total_characters / total_lines if total_lines else 0
    return {
        "total_lines": str(total_lines),
        "character_count": str(total_characters),
        "average_character_count": f"{average_characters:.2f}",
    }


@router.get("/api/running")
async def get_running_status():
    active_task_type = task_orchestrator.get_active_task_type()
    running = task_orchestrator.is_running()
    return {
        "running_llm": bool(running and active_task_type in LLM_TASK_TYPES),
        "running_whisper": bool(running and active_task_type in WHISPER_TASK_TYPES),
        "loading_whisper_model": model_manager.loading_audio_model,
        "loading_gpt_model": model_manager.loading_llm_model,
    }


@router.get("/api/server/variables")
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


@router.get("/api/settings/schema")
async def get_settings_schema():
    audio_client = model_manager.get_audio_client()
    llm_client = model_manager.get_llm_client()
    audio_schema = audio_client.get_settings_schema() if audio_client else {}
    llm_schema = llm_client.get_settings_schema() if llm_client else {}
    return {"audio": audio_schema, "llm": llm_schema}


@router.post("/api/transcribe/transcribe-line")
async def api_transcribe_line(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form(...),
):
    if task_orchestrator.is_running():
        return {"status": "error", "message": "Transcription is already running"}
    if not model_manager.is_audio_ready():
        return {"status": "error", "message": "Whisper model not loaded"}

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            tmp_file.write(await file.read())
            tmp_file_path = tmp_file.name

        background_tasks.add_task(
            _run_single_task,
            TaskTranscribeLine(),
            {"file_path": tmp_file_path, "language": language},
        )
        return {"status": "processing", "message": "Transcription started"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@router.get("/api/transcribe/result")
async def get_transcription_result():
    active_task_type = task_orchestrator.get_active_task_type()
    if task_orchestrator.is_running() and active_task_type in WHISPER_TASK_TYPES:
        return {"status": "processing", "result": None, "error": None}

    record, _ = _read_latest([TaskTranscribeLine.TASK_TYPE, TaskTranscribeFile.TASK_TYPE])
    if record is None:
        return {"status": "idle", "result": None, "error": None}

    if record["status"] == "error":
        return {"status": "error", "result": None, "error": record["error"], "message": record["error"]}
    if record["status"] == "complete":
        return {"status": "complete", "result": record["result"], "error": None}
    return {"status": "processing", "result": None, "error": None}


@router.post("/api/transcribe/transcribe-file")
async def api_transcribe_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form(...),
):
    if task_orchestrator.is_running():
        return {"status": "error", "message": "Transcription is already running"}
    if not model_manager.is_audio_ready():
        return {"status": "error", "message": "Whisper model not loaded"}

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            tmp_file.write(await file.read())
            tmp_file_path = tmp_file.name

        background_tasks.add_task(
            _run_single_task,
            TaskTranscribeFile(),
            {"file_path": tmp_file_path, "language": language, "original_filename": file.filename},
        )
        return {"status": "processing", "message": "File transcription started"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@router.post("/api/utils/get-subtitle-file-info/")
async def api_get_subtitle_file_info(file: UploadFile = File(...)):
    allowed_extensions = {".ass", ".srt"}
    filename_lower = file.filename.lower()
    if not any(filename_lower.endswith(ext) for ext in allowed_extensions):
        return {"status": "error", "message": "Only .ass or .srt files are supported for this endpoint"}

    try:
        suffix = os.path.splitext(file.filename)[1] or ".ass"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(await file.read())
            tmp_path = tmp_file.name
        stats = analyze_subtitle_file(tmp_path)
        return {"status": "success", "result": stats}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
    finally:
        if "tmp_path" in locals() and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@router.post("/api/translate/translate-line")
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
        return {"status": "error", "message": "GPT model not loaded"}

    try:
        context_dict = json.loads(context) if context else {}
        background_tasks.add_task(
            _run_single_task,
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


@router.post("/api/translate/translate-file")
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
        return {"status": "error", "message": "GPT model not loaded"}

    try:
        context_dict = json.loads(context) if context else {}
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            tmp_file.write(await file.read())
            tmp_file_path = tmp_file.name

        background_tasks.add_task(
            _run_single_task,
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


@router.get("/api/translate/result")
async def get_translation_result():
    active_task_type = task_orchestrator.get_active_task_type()
    if task_orchestrator.is_running() and active_task_type in {TaskTranslateLine.TASK_TYPE, TaskTranslateFile.TASK_TYPE}:
        active_progress = progress_handler.get(active_task_type) if active_task_type else None
        if active_progress and active_progress.get("total", 0) > 0:
            return {"status": "translating", "result": None, "error": None, "progress": active_progress}
        return {"status": "processing", "result": None, "error": None}

    record, progress = _read_latest([TaskTranslateLine.TASK_TYPE, TaskTranslateFile.TASK_TYPE])
    if record is None:
        return {"status": "idle", "result": None, "error": None}

    if record["status"] == "error":
        return {"status": "error", "result": None, "message": record["error"], "progress": progress}
    if record["status"] == "complete":
        return {"status": "complete", "result": record["result"], "progress": progress}
    if progress:
        return {"status": "translating", "result": None, "error": None, "progress": progress}
    return {"status": "processing", "result": None, "error": None}


def _get_files_dir(folder: str) -> Path:
    if not folder or not all(ch.isalnum() or ch in "-_" for ch in folder):
        raise HTTPException(status_code=400, detail="Invalid folder name")
    output_dir = Path(__file__).resolve().parent / "outputs" / folder
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@router.get("/api/file-management/{folder}")
async def list_files(folder: str):
    output_dir = _get_files_dir(folder)
    files = []
    for entry in output_dir.iterdir():
        if entry.is_file():
            stat = entry.stat()
            files.append({
                "name": entry.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    files.sort(key=lambda item: item["modified"], reverse=True)
    return {"status": "success", "files": files}


@router.get("/api/file-management/{folder}/{filename}")
async def download_file(folder: str, filename: str):
    output_dir = _get_files_dir(folder).resolve()
    safe_name = os.path.basename(filename)
    file_path = (output_dir / safe_name).resolve()
    if output_dir not in file_path.parents or not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=safe_name, media_type="application/octet-stream")


@router.delete("/api/file-management/{folder}/{filename}")
async def delete_file(folder: str, filename: str):
    output_dir = _get_files_dir(folder).resolve()
    safe_name = os.path.basename(filename)
    file_path = (output_dir / safe_name).resolve()
    if output_dir not in file_path.parents or not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        file_path.unlink()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {exc}")
    return {"status": "success"}


@router.post("/api/load-audio-model")
async def load_audio_model(request: UpdateSettingsRequest, background_tasks: BackgroundTasks):
    if model_manager.loading_audio_model:
        return {"status": "error", "message": "Whisper model is already loading"}
    model_manager.update_audio_settings(request.settings or {})
    background_tasks.add_task(model_manager.load_audio_model)
    return {"status": "loading", "message": "Whisper model loading started"}


@router.post("/api/load-llm-model")
async def load_llm_model(request: UpdateSettingsRequest, background_tasks: BackgroundTasks):
    if model_manager.loading_llm_model:
        return {"status": "error", "message": "GPT model is already loading"}
    model_manager.update_llm_settings(request.settings or {})
    background_tasks.add_task(model_manager.load_llm_model)
    return {"status": "loading", "message": "GPT model loading started"}


@router.post("/api/context/generate-character-list")
async def api_generate_character_list(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context: str = Form("{}"),
):
    if not model_manager.is_llm_ready():
        return {"status": "error", "message": "GPT model not loaded"}
    if task_orchestrator.is_running():
        return {"status": "error", "message": "Context generation already running"}

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    context_dict = json.loads(context) if context else {}
    background_tasks.add_task(
        _run_single_task,
        TaskGenerateCharacterList(),
        {"file_path": tmp_path, "context": context_dict, "input_lang": input_lang, "output_lang": output_lang},
    )
    return {"status": "processing", "message": "Character list generation started"}


@router.post("/api/context/generate-high-level-summary")
async def api_generate_high_level_summary(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context: str = Form("{}"),
):
    if not model_manager.is_llm_ready():
        return {"status": "error", "message": "GPT model not loaded"}
    if task_orchestrator.is_running():
        return {"status": "error", "message": "Context generation already running"}

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    context_dict = json.loads(context) if context else {}
    background_tasks.add_task(
        _run_single_task,
        TaskGenerateSummary(),
        {"file_path": tmp_path, "context": context_dict, "input_lang": input_lang, "output_lang": output_lang},
    )
    return {"status": "processing", "message": "Summary generation started"}


@router.post("/api/context/generate-synopsis")
async def api_generate_synopsis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context: str = Form("{}"),
):
    if not model_manager.is_llm_ready():
        return {"status": "error", "message": "GPT model not loaded"}
    if task_orchestrator.is_running():
        return {"status": "error", "message": "Context generation already running"}

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    context_dict = json.loads(context) if context else {}
    background_tasks.add_task(
        _run_single_task,
        TaskGenerateSynopsis(),
        {"file_path": tmp_path, "context": context_dict, "input_lang": input_lang, "output_lang": output_lang},
    )
    return {"status": "processing", "message": "Synopsis generation started"}


@router.post("/api/context/generate-recap")
async def api_generate_recap(request: GenerateRecapRequest, background_tasks: BackgroundTasks):
    if not model_manager.is_llm_ready():
        return {"status": "error", "message": "GPT model not loaded"}
    if task_orchestrator.is_running():
        return {"status": "error", "message": "Context generation already running"}

    background_tasks.add_task(
        _run_single_task,
        TaskGenerateRecap(),
        {"contexts": request.contexts, "input_lang": request.input_lang, "output_lang": request.output_lang},
    )
    return {"status": "processing", "message": "Recap generation started"}


@router.post("/api/context/save")
async def save_context(request: SaveContextRequest):
    safe_name = os.path.basename(request.filename)
    if not safe_name.endswith(".json"):
        raise HTTPException(status_code=400, detail="Filename must end with .json")
    output_dir = _get_files_dir("context-files")
    file_path = output_dir / safe_name
    with open(file_path, "w", encoding="utf-8") as file_handle:
        json.dump(request.context, file_handle, ensure_ascii=False, indent=2)
    return {"status": "success"}


@router.get("/api/context/result")
async def get_context_result():
    context_task_types = [
        TaskGenerateCharacterList.TASK_TYPE,
        TaskGenerateSynopsis.TASK_TYPE,
        TaskGenerateSummary.TASK_TYPE,
        TaskGenerateRecap.TASK_TYPE,
    ]

    active_task_type = task_orchestrator.get_active_task_type()
    if task_orchestrator.is_running() and active_task_type in context_task_types:
        return {"status": "processing", "message": "Context generation in progress"}

    record, _ = _read_latest(context_task_types)
    if record is None:
        return {"status": "idle", "message": "No context generation has been run"}
    if record["status"] == "error":
        return {"status": "error", "message": record["error"]}
    if record["status"] == "complete":
        return {"status": "success", "result": record["result"]}
    return {"status": "processing", "message": "Context generation in progress"}
