"""
Series library persistence.

Storage layout per series:
  library/<series_id>/series.json      — series metadata (id, name, langs, notes)
  library/<series_id>/characters.json  — list of character objects
  library/<series_id>/glossary.json    — list of glossary term objects
"""

import json
import re
from pathlib import Path
from typing import Optional

from utils.config import LIBRARY_DIR


class InvalidSeriesIdError(ValueError):
    """Raised when a series ID is not a valid kebab-case slug."""


class SeriesNotFoundError(LookupError):
    """Raised when no series.json exists for a series ID."""


def get_library_dir() -> Path:
    """Return the library root directory, creating it if necessary."""
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    return LIBRARY_DIR


def get_series_dir(series_id: str) -> Path:
    """Return the directory path for a series, validating the ID first."""
    _validate_series_id(series_id)
    return get_library_dir() / series_id


def slugify(name: str) -> str:
    """Convert a display name into a lowercase kebab-case slug safe for use as a directory name."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug or "series"


def unique_slug(base: str, existing: set[str]) -> str:
    """Return a slug derived from `base` that does not collide with any slug in `existing`, appending -2, -3, etc. as needed."""
    slug = slugify(base)
    if slug not in existing:
        return slug
    i = 2
    while f"{slug}-{i}" in existing:
        i += 1
    return f"{slug}-{i}"


def list_series_ids() -> list[str]:
    """Return all series IDs (subdirectory names) that have a series.json file."""
    lib_dir = get_library_dir()
    return [
        d.name for d in lib_dir.iterdir()
        if d.is_dir() and (d / "series.json").exists()
    ]


def load_series(series_id: str) -> dict:
    """Load and merge series.json, characters.json, and glossary.json into a single dict; raises SeriesNotFoundError if not found."""
    series_dir = get_series_dir(series_id)
    meta_path = series_dir / "series.json"
    if not meta_path.exists():
        raise SeriesNotFoundError(f"Series '{series_id}' not found")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    chars_path = series_dir / "characters.json"
    glossary_path = series_dir / "glossary.json"
    characters = json.loads(chars_path.read_text(encoding="utf-8")) if chars_path.exists() else []
    glossary = json.loads(glossary_path.read_text(encoding="utf-8")) if glossary_path.exists() else []

    return {**meta, "characters": characters, "glossary": glossary}


def save_series(series: dict) -> None:
    """Atomically write series metadata, characters, and glossary to their respective JSON files, then restore the lists on the caller's dict."""
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
    """Return the character dict with the given id from the series, or None if not found."""
    for char in series.get("characters", []):
        if char["id"] == character_id:
            return char
    return None


def find_glossary_term(series: dict, term_id: str) -> Optional[dict]:
    """Return the glossary term dict with the given id from the series, or None if not found."""
    for term in series.get("glossary", []):
        if term["id"] == term_id:
            return term
    return None


def _write_json(path: Path, data) -> None:
    """Write `data` as indented UTF-8 JSON to `path`."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _validate_series_id(series_id: str) -> None:
    """Raise InvalidSeriesIdError if series_id is not a valid kebab-case slug."""
    if not series_id or not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", series_id):
        raise InvalidSeriesIdError("Invalid series ID")
