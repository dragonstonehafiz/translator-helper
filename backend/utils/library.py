"""
Utility helpers for the series library.

Storage layout per series:
  library/<series_id>/series.json      — series metadata (id, name, langs, notes)
  library/<series_id>/characters.json  — list of character objects
  library/<series_id>/glossary.json    — list of glossary term objects
"""

import json
import re
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
LIBRARY_DIR = OUTPUTS_DIR / "library"


def get_library_dir() -> Path:
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    return LIBRARY_DIR


def get_series_dir(series_id: str) -> Path:
    _validate_series_id(series_id)
    return get_library_dir() / series_id


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug or "series"


def unique_slug(base: str, existing: set[str]) -> str:
    slug = slugify(base)
    if slug not in existing:
        return slug
    i = 2
    while f"{slug}-{i}" in existing:
        i += 1
    return f"{slug}-{i}"


def list_series_ids() -> list[str]:
    lib_dir = get_library_dir()
    return [
        d.name for d in lib_dir.iterdir()
        if d.is_dir() and (d / "series.json").exists()
    ]


def load_series(series_id: str) -> dict:
    series_dir = get_series_dir(series_id)
    meta_path = series_dir / "series.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail=f"Series '{series_id}' not found")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    chars_path = series_dir / "characters.json"
    glossary_path = series_dir / "glossary.json"
    characters = json.loads(chars_path.read_text(encoding="utf-8")) if chars_path.exists() else []
    glossary = json.loads(glossary_path.read_text(encoding="utf-8")) if glossary_path.exists() else []

    return {**meta, "characters": characters, "glossary": glossary}


def save_series(series: dict) -> None:
    series_id = series["id"]
    series_dir = get_series_dir(series_id)
    series_dir.mkdir(parents=True, exist_ok=True)

    characters = series.pop("characters", [])
    glossary = series.pop("glossary", [])

    _write_json(series_dir / "series.json", series)
    _write_json(series_dir / "characters.json", characters)
    _write_json(series_dir / "glossary.json", glossary)

    # Restore the lists so the caller's dict is unaffected
    series["characters"] = characters
    series["glossary"] = glossary


def find_character(series: dict, character_id: str) -> Optional[dict]:
    for char in series.get("characters", []):
        if char["id"] == character_id:
            return char
    return None


def find_glossary_term(series: dict, term_id: str) -> Optional[dict]:
    for term in series.get("glossary", []):
        if term["id"] == term_id:
            return term
    return None


def _write_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _validate_series_id(series_id: str) -> None:
    if not series_id or not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", series_id):
        raise HTTPException(status_code=400, detail="Invalid series ID")
