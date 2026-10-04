"""
Translation routes.
"""

from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from library.repository import SeriesNotFoundError, load_series
from models.manager import ModelManager
from orchestrator.task_data.library_types import SeriesSnapshot
from orchestrator.task_orchestrator import TaskOrchestrator
from orchestrator.workflows.review_file import start_review_file
from orchestrator.workflows.translate_file import start_translate_file
from orchestrator.workflows.translate_line import start_translate_line
from utils.api_response import error_response, processing_response

from .shared import parse_json_form, remove_temp_files, save_upload_to_temp

router = APIRouter(prefix="/translate")


def _busy_or_unready(busy_message: str) -> dict | None:
    """Return an error envelope if a workflow is running or the LLM is not loaded, else None."""
    if TaskOrchestrator.get_instance().get_running_state() is not None:
        return error_response(busy_message)
    if not ModelManager.get_instance().is_llm_ready():
        return error_response("LLM not loaded")
    return None


def _series_or_none(series_id: str) -> SeriesSnapshot | None:
    """Load the series for library context; an unknown series means no library context."""
    if not series_id:
        return None
    try:
        return load_series(series_id)
    except SeriesNotFoundError:
        return None


@router.post("/translate-line")
async def api_translate_line(
    text: str = Form(...),
    context: str = Form("{}"),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
):
    """Start translating one line."""
    rejection = _busy_or_unready("Translation is already running")
    if rejection:
        return rejection
    try:
        start_translate_line(text=text, context=parse_json_form(context), input_lang=input_lang, output_lang=output_lang)
    except Exception as exc:
        return error_response(str(exc))
    return processing_response({"workflow": "translate_line"}, "Translation started")


@router.post("/translate-file")
async def api_translate_file(
    file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    batch_size: int = Form(3),
    series_id: str = Form(""),
):
    """Upload a subtitle file and start translating it."""
    rejection = _busy_or_unready("Translation is already running")
    if rejection:
        return rejection
    tmp_path: Path | None = None
    try:
        tmp_path = await save_upload_to_temp(file)
        start_translate_file(
            file_path=tmp_path,
            original_filename=file.filename or "subtitles",
            input_lang=input_lang,
            output_lang=output_lang,
            batch_size=batch_size,
            series=_series_or_none(series_id),
        )
    except Exception as exc:
        remove_temp_files(tmp_path)
        return error_response(str(exc))
    return processing_response({"workflow": "translate_file"}, "Translation started")


@router.post("/review-translated-file")
async def api_review_translated_file(
    file: UploadFile = File(...),
    translated_file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    batch_size: int = Form(50),
    series_id: str = Form(""),
):
    """Upload original and translated subtitle files and start reviewing the translation."""
    rejection = _busy_or_unready("Translation review is already running")
    if rejection:
        return rejection
    tmp_path: Path | None = None
    tmp_translated_path: Path | None = None
    try:
        tmp_path = await save_upload_to_temp(file)
        tmp_translated_path = await save_upload_to_temp(translated_file)
        start_review_file(
            file_path=tmp_path,
            translated_file_path=tmp_translated_path,
            original_filename=file.filename or "subtitles",
            translated_filename=translated_file.filename or "translated.ass",
            input_lang=input_lang,
            output_lang=output_lang,
            batch_size=batch_size,
            series=_series_or_none(series_id),
        )
    except Exception as exc:
        remove_temp_files(tmp_path, tmp_translated_path)
        return error_response(str(exc))
    return processing_response({"workflow": "review_file"}, "Translation review started")
