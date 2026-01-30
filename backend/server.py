"""
FastAPI server for Translator Helper backend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from routes import router, startup_load_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    startup_load_models()
    yield
    # Shutdown (if needed in the future)


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

app.include_router(router)

if __name__ == "__main__":
    load_dotenv()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)
