"""
HTTP-only helpers shared by route modules: request models, upload handling and file listing.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel

from utils.config import OUTPUTS_DIR


class UpdateSettingsRequest(BaseModel):
    """Request body for model settings update endpoints."""
    provider: str
    settings: dict


async def save_upload_to_temp(file: UploadFile, default_suffix: str = "") -> Path:
    """Save an uploaded file to a temp path and return the path; the caller owns deleting it."""
    suffix = os.path.splitext(file.filename or "")[1] or default_suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(await file.read())
        return Path(tmp_file.name)


def remove_temp_files(*paths: Path | None) -> None:
    """Delete temp files the request still owns (after a rejected or failed start)."""
    for path in paths:
        if path is not None:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass


def parse_json_form(value: str, fallback: dict | None = None) -> dict:
    """Parse a JSON string from a form field, returning fallback if empty."""
    if value:
        return json.loads(value)
    return fallback or {}


def get_files_dir(folder: str) -> Path:
    """Resolve and return the output subdirectory for `folder`, raising 400 on invalid or traversal-attempting paths."""
    segments = folder.split("/") if folder else []
    if not segments or not all(segment and all(ch.isalnum() or ch in "-_" for ch in segment) for segment in segments):
        raise HTTPException(status_code=400, detail="Invalid folder name")
    output_dir = OUTPUTS_DIR.joinpath(*segments)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def build_file_list(output_dir: Path) -> list[dict]:
    """Return a list of file metadata dicts for all files in `output_dir`, sorted by modification time descending."""
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
    return files
