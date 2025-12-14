"""
FastAPI server for Translator Helper backend.
"""

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Server state variables
tavily_api_key_available = False
openai_api_key_available = False
whisper_model_ready = False
whisper_model = None
gpt_model = None
tavily_api_key = ""
openai_api_key = ""
running_translation = False
running_transcription = False
loading_whisper_model = False
loading_gpt_model = False
loading_tavily_api = False

# Initialize FastAPI app
app = FastAPI(
    title="Translator Helper API",
    description="Backend API for translator helper",
    version="1.0.0"
)

# CORS configuration - allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.get("/api/health")
async def health_check():
    """Check if the server is running."""
    return {"status": "ok", "message": "Translator Helper API is running"}

@app.get("/api/running")
async def get_running_status():
    """Get the status of running operations."""
    return {
        "running_translation": running_translation,
        "running_transcription": running_transcription,
        "loading_whisper_model": loading_whisper_model,
        "loading_gpt_model": loading_gpt_model,
        "loading_tavily_api": loading_tavily_api
    }

@app.get("/api/ready")
async def get_ready_status():
    """Check if all required components are ready."""
    is_ready = tavily_api_key_available and openai_api_key_available and whisper_model_ready
    
    if is_ready:
        message = "All components are ready"
    else:
        missing = []
        if not tavily_api_key_available:
            missing.append("Tavily API key")
        if not openai_api_key_available:
            missing.append("OpenAI API key")
        if not whisper_model_ready:
            missing.append("Whisper model")
        message = f"Missing: {', '.join(missing)}"
    
    return {
        "is_ready": is_ready,
        "message": message,
        "tavily_ready": tavily_api_key_available,
        "openai_ready": openai_api_key_available,
        "whisper_ready": whisper_model_ready
    }

@app.get("/api/devices")
async def get_devices():
    """Get available devices for Whisper model."""
    from utils.load_models import get_device_map
    device_map = get_device_map()

    return {"devices": device_map}

# Request models
class LoadWhisperRequest(BaseModel):
    model_name: str
    device: str

class LoadGptRequest(BaseModel):
    model_name: str
    api_key: str
    temperature: float

class LoadTavilyRequest(BaseModel):
    api_key: str

# Background task functions
def load_whisper_background(model_name: str, device: str):
    """Load Whisper model in background."""
    global whisper_model, whisper_model_ready, loading_whisper_model
    try:
        loading_whisper_model = True
        from utils.load_models import load_whisper_model
        whisper_model = load_whisper_model(model_name, device)
        whisper_model_ready = True
    except Exception as e:
        print(f"Error loading Whisper model: {e}")
        whisper_model_ready = False
    finally:
        loading_whisper_model = False

def load_gpt_background(model_name: str, api_key: str, temperature: float):
    """Load GPT model in background."""
    global gpt_model, openai_api_key_available, openai_api_key, loading_gpt_model
    try:
        loading_gpt_model = True
        from utils.load_models import load_gpt_model
        gpt_model = load_gpt_model(api_key, model_name, temperature)
        openai_api_key = api_key
        openai_api_key_available = True
    except Exception as e:
        print(f"Error loading GPT model: {e}")
        openai_api_key_available = False
    finally:
        loading_gpt_model = False

def load_tavily_background(api_key: str):
    """Load Tavily API in background."""
    global tavily_api_key_available, tavily_api_key, loading_tavily_api
    try:
        loading_tavily_api = True
        from utils.load_models import load_tavily_api
        load_tavily_api(api_key)
        tavily_api_key = api_key
        tavily_api_key_available = True
    except Exception as e:
        print(f"Error loading Tavily API: {e}")
        tavily_api_key_available = False
    finally:
        loading_tavily_api = False

@app.post("/api/load-whisper-model")
async def load_whisper(request: LoadWhisperRequest, background_tasks: BackgroundTasks):
    """Load Whisper model in background."""
    global loading_whisper_model
    
    if loading_whisper_model:
        return {"status": "error", "message": "Whisper model is already loading"}
    
    background_tasks.add_task(load_whisper_background, request.model_name, request.device)
    return {"status": "loading", "message": "Whisper model loading started"}

@app.post("/api/load-gpt-model")
async def load_gpt(request: LoadGptRequest, background_tasks: BackgroundTasks):
    """Load GPT model in background."""
    global loading_gpt_model
    
    if loading_gpt_model:
        return {"status": "error", "message": "GPT model is already loading"}
    
    background_tasks.add_task(load_gpt_background, request.model_name, request.api_key, request.temperature)
    return {"status": "loading", "message": "GPT model loading started"}

@app.post("/api/load-tavily-api")
async def load_tavily(request: LoadTavilyRequest, background_tasks: BackgroundTasks):
    """Load Tavily API in background."""
    global loading_tavily_api
    
    if loading_tavily_api:
        return {"status": "error", "message": "Tavily API is already loading"}
    
    background_tasks.add_task(load_tavily_background, request.api_key)
    return {"status": "loading", "message": "Tavily API loading started"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
