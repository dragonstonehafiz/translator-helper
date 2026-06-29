"""
Library routes — CRUD for series, characters, glossary, and the library update chain.
"""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, UploadFile
from pydantic import BaseModel

from orchestrator.library.task_check_against_library import TaskCheckAgainstLibrary
from orchestrator.library.task_deduplicate_proposals import TaskDeduplicateProposals
from orchestrator.library.task_generate_library_proposals import TaskGenerateLibraryProposals
from orchestrator.library.task_generate_search_queries import TaskGenerateSearchQueries
from orchestrator.library.task_scan_subtitle_file import TaskScanSubtitleFile
from orchestrator.library.task_web_search import TaskWebSearch
from utils.api_response import error_response, processing_response, success_response
from utils.library import (
    find_character,
    find_glossary_term,
    get_library_dir,
    get_series_dir,
    list_series_ids,
    load_series,
    save_series,
    slugify,
    unique_slug,
)

from .shared import model_manager, save_upload_to_temp, task_orchestrator, result_handler

router = APIRouter(prefix="/library")


# ── Pydantic models ────────────────────────────────────────────────────────────

class CreateSeriesRequest(BaseModel):
    name: str
    input_lang: str = "ja"
    output_lang: str = "en"
    notes: str = ""


class UpdateSeriesRequest(BaseModel):
    name: str | None = None
    input_lang: str | None = None
    output_lang: str | None = None
    notes: str | None = None


class CharacterRequest(BaseModel):
    name: str
    aliases: list[str] = []
    personality: list[str] = []
    relationships: dict[str, list[str]] = {}
    history: list[str] = []


class UpdateCharacterRequest(BaseModel):
    name: str | None = None
    aliases: list[str] | None = None
    personality: list[str] | None = None
    relationships: dict[str, list[str]] | None = None
    history: list[str] | None = None


class GlossaryTermRequest(BaseModel):
    term: str
    translation: str
    notes: str = ""


class UpdateGlossaryTermRequest(BaseModel):
    term: str | None = None
    translation: str | None = None
    notes: str | None = None


# ── Series CRUD ────────────────────────────────────────────────────────────────

@router.get("/")
async def list_series():
    ids = list_series_ids()
    result = []
    for series_id in ids:
        try:
            s = load_series(series_id)
            result.append({
                "id": s["id"],
                "name": s["name"],
                "input_lang": s.get("input_lang", "ja"),
                "output_lang": s.get("output_lang", "en"),
                "character_count": len(s.get("characters", [])),
                "glossary_count": len(s.get("glossary", [])),
            })
        except Exception:
            continue
    return success_response({"series": result})


@router.post("/")
async def create_series(request: CreateSeriesRequest):
    existing = set(list_series_ids())
    series_id = unique_slug(request.name, existing)
    series = {
        "id": series_id,
        "name": request.name,
        "input_lang": request.input_lang,
        "output_lang": request.output_lang,
        "notes": request.notes,
        "characters": [],
        "glossary": [],
    }
    save_series(series)
    return success_response(series)


@router.get("/{series_id}")
async def get_series(series_id: str):
    series = load_series(series_id)
    return success_response(series)


@router.patch("/{series_id}")
async def update_series(series_id: str, request: UpdateSeriesRequest):
    series = load_series(series_id)
    if request.name is not None:
        series["name"] = request.name
    if request.input_lang is not None:
        series["input_lang"] = request.input_lang
    if request.output_lang is not None:
        series["output_lang"] = request.output_lang
    if request.notes is not None:
        series["notes"] = request.notes
    save_series(series)
    return success_response(series)


@router.delete("/{series_id}")
async def delete_series(series_id: str):
    series_dir = get_series_dir(series_id)
    if not series_dir.exists():
        return error_response(f"Series '{series_id}' not found")
    shutil.rmtree(series_dir)
    return success_response()


# ── Character CRUD ─────────────────────────────────────────────────────────────

@router.post("/{series_id}/characters")
async def add_character(series_id: str, request: CharacterRequest):
    series = load_series(series_id)
    existing_ids = {c["id"] for c in series.get("characters", [])}
    char_id = unique_slug(request.name, existing_ids)
    character = {
        "id": char_id,
        "name": request.name,
        "aliases": request.aliases,
        "personality": request.personality,
        "relationships": request.relationships,
        "history": request.history,
    }
    series.setdefault("characters", []).append(character)
    save_series(series)
    return success_response(series)


@router.patch("/{series_id}/characters/{character_id}")
async def update_character(series_id: str, character_id: str, request: UpdateCharacterRequest):
    series = load_series(series_id)
    char = find_character(series, character_id)
    if char is None:
        return error_response(f"Character '{character_id}' not found")
    if request.name is not None:
        char["name"] = request.name
    if request.aliases is not None:
        char["aliases"] = request.aliases
    if request.personality is not None:
        char["personality"] = request.personality
    if request.relationships is not None:
        char["relationships"] = request.relationships
    if request.history is not None:
        char["history"] = request.history
    save_series(series)
    return success_response(series)


@router.delete("/{series_id}/characters/{character_id}")
async def delete_character(series_id: str, character_id: str):
    series = load_series(series_id)
    original_len = len(series.get("characters", []))
    series["characters"] = [c for c in series.get("characters", []) if c["id"] != character_id]
    if len(series["characters"]) == original_len:
        return error_response(f"Character '{character_id}' not found")
    save_series(series)
    return success_response(series)


# ── Glossary CRUD ──────────────────────────────────────────────────────────────

@router.post("/{series_id}/glossary")
async def add_glossary_term(series_id: str, request: GlossaryTermRequest):
    series = load_series(series_id)
    existing_ids = {t["id"] for t in series.get("glossary", [])}
    term_id = unique_slug(request.term, existing_ids)
    term = {
        "id": term_id,
        "term": request.term,
        "translation": request.translation,
        "notes": request.notes,
    }
    series.setdefault("glossary", []).append(term)
    save_series(series)
    return success_response(series)


@router.patch("/{series_id}/glossary/{term_id}")
async def update_glossary_term(series_id: str, term_id: str, request: UpdateGlossaryTermRequest):
    series = load_series(series_id)
    term = find_glossary_term(series, term_id)
    if term is None:
        return error_response(f"Glossary term '{term_id}' not found")
    if request.term is not None:
        term["term"] = request.term
    if request.translation is not None:
        term["translation"] = request.translation
    if request.notes is not None:
        term["notes"] = request.notes
    save_series(series)
    return success_response(series)


@router.delete("/{series_id}/glossary/{term_id}")
async def delete_glossary_term(series_id: str, term_id: str):
    series = load_series(series_id)
    original_len = len(series.get("glossary", []))
    series["glossary"] = [t for t in series.get("glossary", []) if t["id"] != term_id]
    if len(series["glossary"]) == original_len:
        return error_response(f"Glossary term '{term_id}' not found")
    save_series(series)
    return success_response(series)


# ── Library Update Chain ───────────────────────────────────────────────────────

def _run_library_update_chain(data: dict):
    try:
        task_orchestrator.clear_tasks()
        task_orchestrator.add_task(TaskScanSubtitleFile())
        task_orchestrator.add_task(TaskCheckAgainstLibrary())
        task_orchestrator.add_task(TaskGenerateSearchQueries())
        task_orchestrator.add_task(TaskWebSearch())
        task_orchestrator.add_task(TaskGenerateLibraryProposals())
        task_orchestrator.add_task(TaskDeduplicateProposals())
        task_orchestrator.run_tasks(initial_data=data)
    except Exception as exc:
        result_handler.set_error(TaskDeduplicateProposals.TASK_TYPE, str(exc))


@router.post("/{series_id}/update")
async def start_library_update(
    series_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not model_manager.is_llm_ready():
        return error_response("LLM not loaded")
    if task_orchestrator.is_running():
        return error_response("A task is already running")

    result_handler.clear(TaskDeduplicateProposals.TASK_TYPE)
    series = load_series(series_id)
    tmp_path = await save_upload_to_temp(file)

    safe_name = re.sub(r"[^\w\-]", "_", series.get("name", series_id))[:40]
    log_dir = Path(__file__).parent.parent / "outputs" / "library-update-logs" / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe_name}"
    log_dir.mkdir(parents=True, exist_ok=True)

    known_names = []
    for char in series.get("characters", []):
        known_names.append(char["name"])
        known_names.extend(char.get("aliases", []))
    known_terms = [t["term"] for t in series.get("glossary", [])]

    data = {
        "file_path": tmp_path,
        "series_id": series_id,
        "series": series,
        "log_dir": str(log_dir),
        "known_names": known_names,
        "known_terms": known_terms,
    }
    background_tasks.add_task(_run_library_update_chain, data)
    return processing_response(
        {"task_type": TaskGenerateLibraryProposals.TASK_TYPE},
        "Library update started",
    )
