"""
Library routes — CRUD for series, characters, glossary, and the library update chain.
"""

import shutil
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from library.repository import (
    find_character,
    find_glossary_term,
    get_series_dir,
    list_series_ids,
    load_series,
    save_series,
    unique_slug,
)
from models.manager import ModelManager
from orchestrator.task_orchestrator import TaskOrchestrator
from orchestrator.workflows.update_library import start_update_library
from utils.api_response import error_response, processing_response, success_response

from .shared import remove_temp_files, save_upload_to_temp

router = APIRouter(prefix="/library")


# ── Pydantic models ────────────────────────────────────────────────────────────

class CreateSeriesRequest(BaseModel):
    """Request body for creating a new series."""
    name: str
    input_lang: str = "ja"
    output_lang: str = "en"
    notes: str = ""


class UpdateSeriesRequest(BaseModel):
    """Request body for patching series metadata; omitted fields are left unchanged."""
    name: str | None = None
    input_lang: str | None = None
    output_lang: str | None = None
    notes: str | None = None


class CharacterRequest(BaseModel):
    """Request body for adding a new character to a series."""
    name: str
    aliases: list[str] = []
    personality: list[str] = []
    relationships: dict[str, list[str]] = {}
    history: list[str] = []


class UpdateCharacterRequest(BaseModel):
    """Request body for patching a character; omitted fields are left unchanged."""
    name: str | None = None
    aliases: list[str] | None = None
    personality: list[str] | None = None
    relationships: dict[str, list[str]] | None = None
    history: list[str] | None = None


class GlossaryTermRequest(BaseModel):
    """Request body for adding a new glossary term to a series."""
    term: str
    translation: str
    notes: str = ""


class UpdateGlossaryTermRequest(BaseModel):
    """Request body for patching a glossary term; omitted fields are left unchanged."""
    term: str | None = None
    translation: str | None = None
    notes: str | None = None


# ── Series CRUD ────────────────────────────────────────────────────────────────

@router.get("/")
async def list_series():
    """Return a summary list of all series in the library."""
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
    """Create a new series and return the full series object."""
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
    """Return the full series object including characters and glossary."""
    series = load_series(series_id)
    return success_response(series)


@router.patch("/{series_id}")
async def update_series(series_id: str, request: UpdateSeriesRequest):
    """Patch the series metadata and return the updated series object."""
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
    """Delete a series and all its associated files from the library."""
    series_dir = get_series_dir(series_id)
    if not series_dir.exists():
        return error_response(f"Series '{series_id}' not found")
    shutil.rmtree(series_dir)
    return success_response()


# ── Character CRUD ─────────────────────────────────────────────────────────────

@router.post("/{series_id}/characters")
async def add_character(series_id: str, request: CharacterRequest):
    """Add a new character to the series and return the updated series object."""
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
    """Patch a character's fields and return the updated series object."""
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
    """Remove a character from the series and return the updated series object."""
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
    """Add a new glossary term to the series and return the updated series object."""
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
    """Patch a glossary term's fields and return the updated series object."""
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
    """Remove a glossary term from the series and return the updated series object."""
    series = load_series(series_id)
    original_len = len(series.get("glossary", []))
    series["glossary"] = [t for t in series.get("glossary", []) if t["id"] != term_id]
    if len(series["glossary"]) == original_len:
        return error_response(f"Glossary term '{term_id}' not found")
    save_series(series)
    return success_response(series)


# ── Library Update ─────────────────────────────────────────────────────────────

@router.post("/{series_id}/update")
async def start_library_update(series_id: str, file: UploadFile = File(...)):
    """Upload a subtitle file and start proposing library additions for the given series."""
    if TaskOrchestrator.get_instance().get_running_state() is not None:
        return error_response("A task is already running")
    if not ModelManager.get_instance().is_llm_ready():
        return error_response("LLM not loaded")

    series = load_series(series_id)
    tmp_path: Path | None = None
    try:
        tmp_path = await save_upload_to_temp(file)
        start_update_library(file_path=tmp_path, input_filename=file.filename or "subtitles", series=series)
    except Exception as exc:
        remove_temp_files(tmp_path)
        return error_response(str(exc))
    return processing_response({"workflow": "update_library"}, "Library update started")
