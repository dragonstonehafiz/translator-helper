"""
Route package for Translator Helper backend.
"""

import threading

from fastapi import APIRouter

from .context import router as context_router
from .file_management import router as file_management_router
from .shared import model_manager
from .task_results import router as task_results_router
from .transcribe import router as transcribe_router
from .translate import router as translate_router
from .utils import router as utils_router

router = APIRouter()
router.include_router(context_router)
router.include_router(transcribe_router)
router.include_router(translate_router)
router.include_router(file_management_router)
router.include_router(utils_router)
router.include_router(task_results_router)


def startup_load_models():
    """Reload models on startup."""
    threading.Thread(target=model_manager.load_llm_model, daemon=True).start()
    threading.Thread(target=model_manager.load_audio_model, daemon=True).start()
