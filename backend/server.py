"""
FastAPI server for Translator Helper backend.
"""

import asyncio
import threading
from collections.abc import Callable
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.manager import ModelManager
from routes import router
from utils.api_response import register_exception_handlers


def _background_load(load: Callable[[], None]) -> None:
    """Run one startup model load; ModelManager has already logged and stored any failure."""
    try:
        load()
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the three model loads without waiting for them; on shutdown, wait for them and release the models."""
    model_manager = ModelManager.get_instance()
    loaders = [
        threading.Thread(target=_background_load, args=(load,), daemon=True)
        for load in (model_manager.load_llm_model, model_manager.load_audio_model, model_manager.load_search_model)
    ]
    for loader in loaders:
        loader.start()
    try:
        yield
    finally:
        for loader in loaders:
            await asyncio.to_thread(loader.join)
        await asyncio.to_thread(model_manager.shutdown)


# Initialize FastAPI app
app = FastAPI(
    title="Translator Helper API",
    description="Backend API for translator helper",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration - allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(router)

if __name__ == "__main__":
    load_dotenv()
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, access_log=False, reload=True)
