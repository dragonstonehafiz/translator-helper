"""
FastAPI server for Translator Helper backend.
"""

from fastapi import FastAPI, BackgroundTasks, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from settings import settings
import threading
from typing import Optional
from business.context import generate_web_context, generate_character_list, generate_high_level_summary, generate_synopsis, generate_recap
from business.transcribe import transcribe_line
from business.translate import translate_sub, translate_subs
from langchain_tavily import TavilySearch
from utils.utils import load_sub_data
import tempfile
import os
from pprint import pprint
from utils.logger import setup_logger

# Setup logger
logger = setup_logger()

# Server state variables
tavily_api_key_available = False
openai_api_key_available = False
whisper_model_ready = False
whisper_model = None
gpt_model = None
tavily_api_key = ""
openai_api_key = ""
current_whisper_model = ""
current_device = ""
current_openai_model = ""
current_temperature = 0.5
running_translation = False
running_transcription = False
running_context = False
loading_whisper_model = False
loading_gpt_model = False
loading_tavily_api = False
context_result = None
context_error = None
transcription_result = None
transcription_error = None
translation_result = None
translation_error = None

# Startup function to load models based on settings
def startup_load_models():
    """Load models on startup based on .env configuration."""
    # Load Tavily API if key is provided
    if settings.tavily_api_key:
        print(f"Loading Tavily API on startup...")
        thread = threading.Thread(target=load_tavily_background, args=(settings.tavily_api_key,), daemon=True)
        thread.start()
    
    # Load OpenAI/GPT model if key is provided
    if settings.openai_api_key:
        print(f"Loading GPT model '{settings.openai_model}' on startup...")
        thread = threading.Thread(target=load_gpt_background, args=(settings.openai_model, settings.openai_api_key, settings.temperature), daemon=True)
        thread.start()
    
    # Load Whisper model if settings are provided
    if settings.whisper_model and settings.device:
        print(f"Loading Whisper model '{settings.whisper_model}' on device '{settings.device}' on startup...")
        thread = threading.Thread(target=load_whisper_background, args=(settings.whisper_model, settings.device), daemon=True)
        thread.start()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
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

@app.get("/api/running")
async def get_running_status():
    """Get the status of running operations."""
    return {
        "running_translation": running_translation,
        "running_transcription": running_transcription,
        "running_context": running_context,
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

@app.get("/api/server/variables")
async def get_server_variables():
    """Get current server configuration variables."""
    return {
        "whisper_model": current_whisper_model,
        "device": current_device,
        "openai_model": current_openai_model,
        "temperature": current_temperature
    }

# Request models
class LoadWhisperRequest(BaseModel):
    model_name: str
    device: str

class LoadGptRequest(BaseModel):
    model_name: str
    api_key: Optional[str] = None
    temperature: float

class LoadTavilyRequest(BaseModel):
    api_key: str

class GenerateWebContextRequest(BaseModel):
    series_name: str
    keywords: str
    input_lang: str = "ja"
    output_lang: str = "en"

class GenerateCharacterListRequest(BaseModel):
    transcript: str
    context: dict = {}
    input_lang: str = "ja"
    output_lang: str = "en"

class GenerateHighLevelSummaryRequest(BaseModel):
    transcript: str
    context: dict = {}
    input_lang: str = "ja"
    output_lang: str = "en"

class GenerateRecapRequest(BaseModel):
    contexts: list[dict]
    input_lang: str = "ja"
    output_lang: str = "en"

# Background task functions
def load_whisper_background(model_name: str, device: str):
    """Load Whisper model in background."""
    global whisper_model, whisper_model_ready, loading_whisper_model, current_whisper_model, current_device
    try:
        loading_whisper_model = True
        logger.info(f"Starting Whisper model load: model='{model_name}', device='{device}'")
        from utils.load_models import load_whisper_model
        whisper_model = load_whisper_model(model_name, device)
        whisper_model_ready = True
        current_whisper_model = model_name
        current_device = device
        logger.info(f"Successfully loaded Whisper model: model='{model_name}', device='{device}'")
    except Exception as e:
        logger.error(f"Error loading Whisper model: {e}")
        print(f"Error loading Whisper model: {e}")
        whisper_model_ready = False
    finally:
        loading_whisper_model = False
        logger.info(f"Whisper model load completed: model='{model_name}'")

def load_gpt_background(model_name: str, api_key: Optional[str], temperature: float):
    """Load GPT model in background."""
    global gpt_model, openai_api_key_available, openai_api_key, loading_gpt_model, current_openai_model, current_temperature
    try:
        loading_gpt_model = True
        logger.info(f"Starting GPT model load: model='{model_name}', temperature={temperature}")
        key_to_use = api_key or openai_api_key
        if not key_to_use:
            raise ValueError("OpenAI API key not provided and no stored key is available.")
        from utils.load_models import load_gpt_model
        gpt_model = load_gpt_model(key_to_use, model_name, temperature)
        if api_key:
            openai_api_key = api_key
        openai_api_key_available = True
        current_openai_model = model_name
        current_temperature = temperature
        logger.info(f"Successfully loaded GPT model: model='{model_name}'")
    except Exception as e:
        logger.error(f"Error loading GPT model: {e}")
        print(f"Error loading GPT model: {e}")
        openai_api_key_available = False
    finally:
        loading_gpt_model = False
        logger.info(f"GPT model load completed: model='{model_name}'")

def load_tavily_background(api_key: str):
    """Load Tavily API in background."""
    global tavily_api_key_available, tavily_api_key, loading_tavily_api
    try:
        loading_tavily_api = True
        logger.info("Starting Tavily API load")
        from utils.load_models import load_tavily_api
        load_tavily_api(api_key)
        tavily_api_key = api_key
        tavily_api_key_available = True
        logger.info("Successfully loaded Tavily API")
    except Exception as e:
        logger.error(f"Error loading Tavily API: {e}")
        print(f"Error loading Tavily API: {e}")
        tavily_api_key_available = False
    finally:
        loading_tavily_api = False
        logger.info("Tavily API load completed")

def generate_web_context_background(series_name: str, keywords: str, input_lang: str, output_lang: str):
    """Generate web context in background."""
    global running_context, context_result, context_error, gpt_model, tavily_api_key
    try:
        running_context = True
        context_result = None
        context_error = None
        logger.info(f"Starting web context generation: series='{series_name}', keywords='{keywords}'")
        search_tool = TavilySearch(api_key=tavily_api_key)
        result = generate_web_context(
            model=gpt_model,
            search_tool=search_tool,
            input_lang=input_lang,
            output_lang=output_lang,
            series_name=series_name,
            keywords=keywords
        )
        context_result = {"type": "web_context", "data": result}
        logger.info(f"Successfully completed web context generation: series='{series_name}'")
    except Exception as e:
        logger.error(f"Error generating web context: {e}")
        print(f"Error generating web context: {e}")
        context_error = str(e)
    finally:
        running_context = False
        logger.info("Web context generation process completed")

def generate_character_list_background(file_path: str, input_lang: str, output_lang: str, context: dict):
    """Generate character list in background."""
    global running_context, context_result, context_error, gpt_model
    try:
        running_context = True
        context_result = None
        context_error = None
        logger.info(f"Starting character list generation: file='{file_path}'")
        
        # Extract transcript from subtitle file
        transcript_lines = load_sub_data(file_path, include_speaker=True)
        transcript = "\n".join(transcript_lines)
        
        result = generate_character_list(
            model=gpt_model,
            input_lang=input_lang,
            output_lang=output_lang,
            transcript=transcript,
            context=context if context else None
        )
        context_result = {"type": "character_list", "data": result}
        logger.info("Successfully completed character list generation")
    except Exception as e:
        logger.error(f"Error generating character list: {e}")
        print(f"Error generating character list: {e}")
        context_error = str(e)
    finally:
        running_context = False
        logger.info("Character list generation process completed")
        # Cleanup temp file
        try:
            os.remove(file_path)
        except:
            pass

def generate_summary_background(file_path: str, input_lang: str, output_lang: str, context: dict):
    """Generate high-level summary in background."""
    global running_context, context_result, context_error, gpt_model
    try:
        running_context = True
        context_result = None
        context_error = None
        logger.info(f"Starting summary generation: file='{file_path}'")
        
        # Extract transcript from subtitle file
        transcript_lines = load_sub_data(file_path, include_speaker=True)
        transcript = "\n".join(transcript_lines)

        
        
        result = generate_high_level_summary(
            model=gpt_model,
            input_lang=input_lang,
            output_lang=output_lang,
            transcript=transcript,
            context=context if context else None
        )
        context_result = {"type": "summary", "data": result}
        logger.info("Successfully completed summary generation")
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        print(f"Error generating summary: {e}")
        context_error = str(e)
    finally:
        running_context = False
        logger.info("Summary generation process completed")
        # Cleanup temp file
        try:
            os.remove(file_path)
        except:
            pass

def generate_synopsis_background(file_path: str, input_lang: str, output_lang: str, context: dict):
    """Generate synopsis in background."""
    global running_context, context_result, context_error, gpt_model
    try:
        running_context = True
        context_result = None
        context_error = None
        logger.info(f"Starting synopsis generation: file='{file_path}'")
        
        # Extract transcript from subtitle file
        transcript_lines = load_sub_data(file_path, include_speaker=True)
        transcript = "\n".join(transcript_lines)
        
        result = generate_synopsis(
            model=gpt_model,
            input_lang=input_lang,
            output_lang=output_lang,
            transcript=transcript,
            context=context if context else None
        )
        context_result = {"type": "synopsis", "data": result}
        logger.info("Successfully completed synopsis generation")
    except Exception as e:
        logger.error(f"Error generating synopsis: {e}")
        print(f"Error generating synopsis: {e}")
        context_error = str(e)
    finally:
        running_context = False
        logger.info("Synopsis generation process completed")
        # Cleanup temp file
        try:
            os.remove(file_path)
        except:
            pass

def generate_recap_background(input_lang: str, output_lang: str, contexts: list[dict]):
    """Generate recap from multiple contexts in background."""
    global running_context, context_result, context_error, gpt_model
    try:
        running_context = True
        context_result = None
        context_error = None
        logger.info(f"Starting recap generation: contexts={len(contexts)}")
        result = generate_recap(
            model=gpt_model,
            input_lang=input_lang,
            output_lang=output_lang,
            contexts=contexts
        )
        context_result = {"type": "recap", "data": result}
        logger.info("Successfully completed recap generation")
    except Exception as e:
        logger.error(f"Error generating recap: {e}")
        print(f"Error generating recap: {e}")
        context_error = str(e)
    finally:
        running_context = False
        logger.info("Recap generation process completed")

def transcribe_line_background(file_path: str, language: str):
    """Transcribe audio in background."""
    global running_transcription, transcription_result, transcription_error, whisper_model
    try:
        running_transcription = True
        transcription_result = None
        transcription_error = None
        logger.info(f"Starting audio transcription: file='{file_path}', language='{language}'")
        
        result = transcribe_line(
            model=whisper_model,
            filepath=file_path,
            language=language
        )
        transcription_result = {"type": "transcription", "data": result}
        logger.info("Successfully completed audio transcription")
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        print(f"Error transcribing audio: {e}")
        transcription_error = str(e)
    finally:
        running_transcription = False
        logger.info("Audio transcription process completed")
        # Cleanup temp file
        try:
            os.remove(file_path)
        except:
            pass

def translate_line_background(text: str, context: dict, input_lang: str, output_lang: str):
    """Translate a single line in background."""
    global running_translation, translation_result, translation_error, gpt_model
    try:
        running_translation = True
        translation_result = None
        translation_error = None
        logger.info(f"Starting line translation: input_lang='{input_lang}', output_lang='{output_lang}'")
        
        result = translate_sub(
            llm=gpt_model,
            text=text,
            context=context if context else {},
            input_lang=input_lang,
            target_lang=output_lang
        )
        translation_result = {"type": "line_translation", "data": result}
        logger.info("Successfully completed line translation")
    except Exception as e:
        logger.error(f"Error translating line: {e}")
        print(f"Error translating line: {e}")
        translation_error = str(e)
    finally:
        running_translation = False
        logger.info("Line translation process completed")

def translate_file_background(file_path: str, context: dict, input_lang: str, output_lang: str, context_window: int):
    """Translate subtitle file in background."""
    global running_translation, translation_result, translation_error, gpt_model
    try:
        running_translation = True
        translation_result = None
        translation_error = None
        logger.info(f"Starting file translation: file='{file_path}', input_lang='{input_lang}', output_lang='{output_lang}'")
        
        # Load subtitle file
        import pysubs2
        subs = pysubs2.load(file_path)
        
        # Translate
        translated_subs = translate_subs(
            llm=gpt_model,
            subs=subs,
            context=context if context else {},
            context_window=context_window,
            input_lang=input_lang,
            target_lang=output_lang
        )
        
        # Save to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=os.path.splitext(file_path)[1], encoding='utf-8') as tmp_file:
            translated_subs.save(tmp_file.name)
            output_path = tmp_file.name
        
        # Read the file content
        with open(output_path, 'r', encoding='utf-8') as f:
            output_content = f.read()
        
        # Get original filename and create translated filename
        original_filename = os.path.basename(file_path)
        name, ext = os.path.splitext(original_filename)
        translated_filename = f"{name}_translated{ext}"
        
        translation_result = {
            "type": "file_translation", 
            "data": output_content, 
            "filename": translated_filename
        }
        logger.info("Successfully completed file translation")
        
        # Cleanup output file
        try:
            os.remove(output_path)
        except:
            pass
    except Exception as e:
        logger.error(f"Error translating file: {e}")
        print(f"Error translating file: {e}")
        translation_error = str(e)
    finally:
        running_translation = False
        logger.info("File translation process completed")
        # Cleanup input file
        try:
            os.remove(file_path)
        except:
            pass

def analyze_subtitle_file(file_path: str):
    """Return dialogue stats for an ASS/SRT subtitle file."""
    import pysubs2

    subs = pysubs2.load(file_path)
    total_lines = 0
    total_characters = 0

    for event in subs.events:
        text = event.plaintext.strip()
        if not text:
            continue

        speaker = event.name.strip() if event.name else ""
        line_text = f"{speaker}: {text}" if speaker else text
        total_lines += 1
        total_characters += len(line_text)

    average_characters = total_characters / total_lines if total_lines else 0
    return {
        "total_lines": str(total_lines),
        "character_count": str(total_characters),
        "average_character_count": f"{average_characters:.2f}"
    }

@app.post("/api/transcribe/transcribe-line")
async def api_transcribe_line(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form(...)
):
    """Transcribe audio file using Whisper model."""
    global running_transcription, whisper_model
    
    if running_transcription:
        return {"status": "error", "message": "Transcription is already running"}
    
    if not whisper_model:
        return {"status": "error", "message": "Whisper model not loaded"}
    
    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Start background transcription
        background_tasks.add_task(transcribe_line_background, tmp_file_path, language)
        
        return {"status": "processing", "message": "Transcription started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/transcribe/result")
async def get_transcription_result():
    """Get the result of the transcription."""
    global transcription_result, transcription_error, running_transcription
    
    if running_transcription:
        return {"status": "processing", "result": None, "error": None}
    elif transcription_error:
        error = transcription_error
        transcription_error = None  # Clear error after reading
        return {"status": "error", "result": None, "error": error}
    elif transcription_result:
        result = transcription_result
        transcription_result = None  # Clear result after reading
        return {"status": "complete", "result": result, "error": None}
    else:
        return {"status": "idle", "result": None, "error": None}

@app.post("/api/transcribe/get-file-info/")
async def api_get_transcribe_file_info(file: UploadFile = File(...)):
    """Return stats about an uploaded ASS or SRT subtitle file."""
    allowed_extensions = {".ass", ".srt"}
    filename_lower = file.filename.lower()
    if not any(filename_lower.endswith(ext) for ext in allowed_extensions):
        return {"status": "error", "message": "Only .ass or .srt files are supported for this endpoint"}

    try:
        suffix = os.path.splitext(file.filename)[1] or ".ass"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        stats = analyze_subtitle_file(tmp_path)
        return {"status": "success", "result": stats}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

@app.post("/api/translate/translate-line")
async def api_translate_line(
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    context: str = Form("{}"),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en")
):
    """Translate a single line of text."""
    global running_translation, gpt_model
    
    if running_translation:
        return {"status": "error", "message": "Translation is already running"}
    
    if not gpt_model:
        return {"status": "error", "message": "GPT model not loaded"}
    
    try:
        import json
        context_dict = json.loads(context) if context else {}
        context_keys = sorted(context_dict.keys()) if isinstance(context_dict, dict) else []
        logger.info(f"Translate line context keys: {context_keys if context_keys else 'none'}")
        
        # Start background translation
        background_tasks.add_task(translate_line_background, text, context_dict, input_lang, output_lang)
        
        return {"status": "processing", "message": "Translation started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/translate/translate-file")
async def api_translate_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    context: str = Form("{}"),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context_window: int = Form(3)
):
    """Translate a subtitle file (.ass or .srt)."""
    global running_translation, gpt_model
    
    if running_translation:
        return {"status": "error", "message": "Translation is already running"}
    
    if not gpt_model:
        return {"status": "error", "message": "GPT model not loaded"}
    
    try:
        import json
        context_dict = json.loads(context) if context else {}
        context_keys = sorted(context_dict.keys()) if isinstance(context_dict, dict) else []
        logger.info(f"Translate file context keys: {context_keys if context_keys else 'none'}")
        
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Start background translation
        background_tasks.add_task(translate_file_background, tmp_file_path, context_dict, input_lang, output_lang, context_window)
        
        return {"status": "processing", "message": "Translation started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/translate/result")
async def get_translation_result():
    """Get the result of the translation."""
    global translation_result, translation_error, running_translation
    
    if running_translation:
        return {"status": "processing", "result": None, "error": None}
    elif translation_error:
        error = translation_error
        translation_error = None  # Clear error after reading
        return {"status": "error", "result": None, "message": error}
    elif translation_result:
        result = translation_result
        translation_result = None  # Clear result after reading
        return {"status": "complete", "result": result}
    else:
        return {"status": "idle", "result": None, "error": None}
    
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

@app.post("/api/context/generate-web-context")
async def api_generate_web_context(request: GenerateWebContextRequest, background_tasks: BackgroundTasks):
    """Generate web context using Tavily search and GPT."""
    global gpt_model, tavily_api_key, running_context
    
    if not gpt_model:
        return {"status": "error", "message": "GPT model not loaded"}
    
    if not tavily_api_key:
        return {"status": "error", "message": "Tavily API key not loaded"}
    
    if running_context:
        return {"status": "error", "message": "Context generation already running"}
    
    background_tasks.add_task(
        generate_web_context_background,
        request.series_name,
        request.keywords,
        request.input_lang,
        request.output_lang
    )
    return {"status": "processing", "message": "Web context generation started"}

@app.post("/api/context/generate-character-list")
async def api_generate_character_list(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context: str = Form("{}")
):
    """Generate character list from subtitle file."""
    global gpt_model, running_context
    
    if not gpt_model:
        return {"status": "error", "message": "GPT model not loaded"}
    
    if running_context:
        return {"status": "error", "message": "Context generation already running"}
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    # Parse context from JSON string
    import json
    context_dict = json.loads(context) if context else {}
    
    background_tasks.add_task(
        generate_character_list_background,
        tmp_path,
        input_lang,
        output_lang,
        context_dict
    )
    return {"status": "processing", "message": "Character list generation started"}

@app.post("/api/context/generate-high-level-summary")
async def api_generate_high_level_summary(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context: str = Form("{}")
):
    """Generate high-level summary from subtitle file."""
    global gpt_model, running_context
    
    if not gpt_model:
        return {"status": "error", "message": "GPT model not loaded"}
    
    if running_context:
        return {"status": "error", "message": "Context generation already running"}
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    # Parse context from JSON string
    import json
    context_dict = json.loads(context) if context else {}
    
    background_tasks.add_task(
        generate_summary_background,
        tmp_path,
        input_lang,
        output_lang,
        context_dict
    )
    return {"status": "processing", "message": "Summary generation started"}

@app.post("/api/context/generate-synopsis")
async def api_generate_synopsis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context: str = Form("{}")
):
    """Generate synopsis from subtitle file."""
    global gpt_model, running_context
    
    if not gpt_model:
        return {"status": "error", "message": "GPT model not loaded"}
    
    if running_context:
        return {"status": "error", "message": "Context generation already running"}
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    # Parse context from JSON string
    import json
    context_dict = json.loads(context) if context else {}
    
    background_tasks.add_task(
        generate_synopsis_background,
        tmp_path,
        input_lang,
        output_lang,
        context_dict
    )
    return {"status": "processing", "message": "Synopsis generation started"}

@app.post("/api/context/generate-recap")
async def api_generate_recap(request: GenerateRecapRequest, background_tasks: BackgroundTasks):
    """Generate recap from multiple context dicts."""
    global gpt_model, running_context
    
    if not gpt_model:
        return {"status": "error", "message": "GPT model not loaded"}
    
    if running_context:
        return {"status": "error", "message": "Context generation already running"}
    
    background_tasks.add_task(
        generate_recap_background,
        request.input_lang,
        request.output_lang,
        request.contexts
    )
    return {"status": "processing", "message": "Recap generation started"}

@app.get("/api/context/result")
async def get_context_result():
    """Get the result of the last context generation operation."""
    global context_result, context_error, running_context
    
    if running_context:
        return {"status": "processing", "message": "Context generation in progress"}
    
    if context_error:
        error = context_error
        return {"status": "error", "message": error}
    
    if context_result:
        result = context_result
        return {"status": "success", "result": result}
    
    return {"status": "idle", "message": "No context generation has been run"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
