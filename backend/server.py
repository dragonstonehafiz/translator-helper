"""
FastAPI server for Translator Helper backend.
"""

import threading
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from model_manager import ModelManager
from routes import router
from utils.api_response import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background model loading on startup; shutdown handling arrives with the ModelManager rework."""
    model_manager = ModelManager.get_instance()
    threading.Thread(target=model_manager.load_llm_model, daemon=True).start()
    threading.Thread(target=model_manager.load_audio_model, daemon=True).start()
    threading.Thread(target=model_manager.load_search_model, daemon=True).start()
    yield


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
