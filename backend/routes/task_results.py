"""
Shared task-result polling route.
"""

from fastapi import APIRouter

from .shared import AUDIO_TASK_TYPES, CONTEXT_TASK_TYPES, TRANSLATE_TASK_TYPES, build_task_response, ensure_task_type

router = APIRouter(prefix="/task-results")

TASK_RESULT_TYPES = set(CONTEXT_TASK_TYPES) | set(TRANSLATE_TASK_TYPES) | set(AUDIO_TASK_TYPES)


@router.get("/{task_type}")
async def get_task_result(task_type: str):
    ensure_task_type(task_type, TASK_RESULT_TYPES)
    return build_task_response(task_type)
