"""
File management routes.
"""

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from utils.api_response import success_response

from .shared import build_file_list, get_files_dir

router = APIRouter(prefix="/file-management")


@router.get("/{folder}")
async def list_files(folder: str):
    output_dir = get_files_dir(folder)
    return success_response({"files": build_file_list(output_dir)})


@router.get("/{folder}/{filename}")
async def download_file(folder: str, filename: str):
    output_dir = get_files_dir(folder).resolve()
    safe_name = os.path.basename(filename)
    file_path = (output_dir / safe_name).resolve()
    if output_dir not in file_path.parents or not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=safe_name, media_type="application/octet-stream")


@router.delete("/{folder}/{filename}")
async def delete_file(folder: str, filename: str):
    output_dir = get_files_dir(folder).resolve()
    safe_name = os.path.basename(filename)
    file_path = (output_dir / safe_name).resolve()
    if output_dir not in file_path.parents or not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        file_path.unlink()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {exc}")
    return success_response()
