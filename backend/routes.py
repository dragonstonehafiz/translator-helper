"""
Route definitions for Translator Helper backend.
"""

from fastapi import APIRouter, BackgroundTasks, File, UploadFile, Form
from pydantic import BaseModel
from typing import Optional
import threading
import tempfile
import os
from utils.model_manager import ModelManager
from utils.prompts import PromptGenerator
from utils.utils import load_sub_data
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger()

model_manager = ModelManager()


# Startup function to load models based on settings
def startup_load_models():
    """Load models on startup based on .env configuration."""
    print("Loading LLM model on startup...")
    threading.Thread(target=model_manager.load_llm_model, daemon=True).start()

    print("Loading Whisper model on startup...")
    threading.Thread(target=model_manager.load_audio_model, daemon=True).start()


class UpdateSettingsRequest(BaseModel):
    provider: str
    settings: dict


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


@router.get("/api/running")
async def get_running_status():
    """Get the status of running operations."""
    return {
        "running_llm": model_manager.is_llm_running(),
        "running_whisper": model_manager.is_audio_running(),
        "loading_whisper_model": model_manager.loading_audio_model,
        "loading_gpt_model": model_manager.loading_llm_model
    }


@router.get("/api/server/variables")
async def get_server_variables():
    """Get current server configuration variables."""
    llm_ready = model_manager.is_llm_ready()
    audio_ready = model_manager.is_audio_ready()
    return {
        "audio": (model_manager.audio_client.get_server_variables() if model_manager.audio_client else {}),
        "llm": (model_manager.llm_client.get_server_variables() if model_manager.llm_client else {}),
        "llm_ready": llm_ready,
        "audio_ready": audio_ready,
    }


@router.get("/api/settings/schema")
async def get_settings_schema():
    """Get settings schema for model configuration."""
    audio_schema = model_manager.audio_client.get_settings_schema() if model_manager.audio_client else {}
    llm_schema = model_manager.llm_client.get_settings_schema() if model_manager.llm_client else {}
    return {"audio": audio_schema, "llm": llm_schema}


@router.post("/api/transcribe/transcribe-line")
async def api_transcribe_line(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form(...)
):
    """Transcribe audio file using Whisper model."""
    if model_manager.is_audio_running():
        return {"status": "error", "message": "Transcription is already running"}

    if not model_manager.is_audio_ready():
        return {"status": "error", "message": "Whisper model not loaded"}

    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        # Start background transcription
        background_tasks.add_task(model_manager.run_transcription_task, tmp_file_path, language)

        return {"status": "processing", "message": "Transcription started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/api/transcribe/result")
async def get_transcription_result():
    """Get the result of the transcription."""
    if model_manager.is_audio_running():
        return {"status": "processing", "result": None, "error": None}
    elif model_manager.transcription_error:
        error = model_manager.transcription_error
        model_manager.transcription_error = None
        return {"status": "error", "result": None, "error": error}
    elif model_manager.transcription_result:
        result = model_manager.transcription_result
        model_manager.transcription_result = None
        return {"status": "complete", "result": result, "error": None}
    else:
        return {"status": "idle", "result": None, "error": None}


@router.post("/api/utils/get-subtitle-file-info/")
async def api_get_subtitle_file_info(file: UploadFile = File(...)):
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


@router.post("/api/translate/translate-line")
async def api_translate_line(
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    context: str = Form("{}"),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en")
):
    """Translate a single line of text."""
    if model_manager.is_llm_running():
        return {"status": "error", "message": "Translation is already running"}

    if not model_manager.is_llm_ready():
        return {"status": "error", "message": "GPT model not loaded"}

    try:
        import json
        context_dict = json.loads(context) if context else {}
        context_keys = sorted(context_dict.keys()) if isinstance(context_dict, dict) else []
        logger.info(f"Translate line context keys: {context_keys if context_keys else 'none'}")

        prompt_generator = PromptGenerator()
        system_prompt = prompt_generator.generate_translate_sub_prompt(
            context=context_dict if context_dict else {},
            input_lang=input_lang,
            target_lang=output_lang
        )

        # Start background translation
        background_tasks.add_task(
            model_manager.run_llm_task,
            text,
            system_prompt,
            "line_translation",
            target="translation"
        )

        return {"status": "processing", "message": "Translation started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/api/translate/translate-file")
async def api_translate_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    context: str = Form("{}"),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context_window: int = Form(3)
):
    """Translate a subtitle file (.ass or .srt)."""
    if model_manager.is_llm_running():
        return {"status": "error", "message": "Translation is already running"}

    if not model_manager.is_llm_ready():
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
        background_tasks.add_task(
            model_manager.run_translate_file_task,
            tmp_file_path,
            context_dict,
            input_lang,
            output_lang,
            context_window
        )

        return {"status": "processing", "message": "Translation started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/api/translate/result")
async def get_translation_result():
    """Get the result of the translation."""
    if model_manager.is_llm_running():
        return {"status": "processing", "result": None, "error": None}
    elif model_manager.llm_error:
        error = model_manager.llm_error
        model_manager.llm_error = None
        return {"status": "error", "result": None, "message": error}
    elif model_manager.translation_result:
        result = model_manager.translation_result
        model_manager.translation_result = None
        return {"status": "complete", "result": result}
    else:
        return {"status": "idle", "result": None, "error": None}


@router.post("/api/load-audio-model")
async def load_audio_model(request: UpdateSettingsRequest, background_tasks: BackgroundTasks):
    """Apply audio settings then reload the audio model."""
    if model_manager.loading_audio_model:
        return {"status": "error", "message": "Whisper model is already loading"}
    model_manager.apply_audio_settings(request.settings or {})
    background_tasks.add_task(model_manager.reload_audio_model)
    return {"status": "loading", "message": "Whisper model loading started"}


@router.post("/api/load-llm-model")
async def load_llm_model(request: UpdateSettingsRequest, background_tasks: BackgroundTasks):
    """Apply LLM settings then reload the LLM model."""
    if model_manager.loading_llm_model:
        return {"status": "error", "message": "GPT model is already loading"}
    model_manager.apply_llm_settings(request.settings or {})
    background_tasks.add_task(model_manager.reload_llm_model)
    return {"status": "loading", "message": "GPT model loading started"}


@router.post("/api/context/generate-character-list")
async def api_generate_character_list(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context: str = Form("{}")
):
    """Generate character list from subtitle file."""
    if not model_manager.is_llm_ready():
        return {"status": "error", "message": "GPT model not loaded"}

    if model_manager.is_llm_running():
        return {"status": "error", "message": "Context generation already running"}

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Parse context from JSON string
    import json
    context_dict = json.loads(context) if context else {}

    transcript_lines = load_sub_data(tmp_path, include_speaker=True)
    transcript = "\n".join(transcript_lines)
    prompt_generator = PromptGenerator()
    system_prompt = prompt_generator.generate_character_list_prompt(
        context=context_dict if context_dict else None,
        input_lang=input_lang,
        output_lang=output_lang
    )

    background_tasks.add_task(
        model_manager.run_llm_task,
        transcript,
        system_prompt,
        "character_list",
        target="context",
        cleanup_path=tmp_path
    )
    return {"status": "processing", "message": "Character list generation started"}


@router.post("/api/context/generate-high-level-summary")
async def api_generate_high_level_summary(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context: str = Form("{}")
):
    """Generate high-level summary from subtitle file."""
    if not model_manager.is_llm_ready():
        return {"status": "error", "message": "GPT model not loaded"}

    if model_manager.is_llm_running():
        return {"status": "error", "message": "Context generation already running"}

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Parse context from JSON string
    import json
    context_dict = json.loads(context) if context else {}

    transcript_lines = load_sub_data(tmp_path, include_speaker=True)
    transcript = "\n".join(transcript_lines)
    prompt_generator = PromptGenerator()
    system_prompt = prompt_generator.generate_summary_prompt(
        context=context_dict if context_dict else None,
        input_lang=input_lang,
        output_lang=output_lang
    )

    background_tasks.add_task(
        model_manager.run_llm_task,
        transcript,
        system_prompt,
        "summary",
        target="context",
        cleanup_path=tmp_path
    )
    return {"status": "processing", "message": "Summary generation started"}


@router.post("/api/context/generate-synopsis")
async def api_generate_synopsis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context: str = Form("{}")
):
    """Generate synopsis from subtitle file."""
    if not model_manager.is_llm_ready():
        return {"status": "error", "message": "GPT model not loaded"}

    if model_manager.is_llm_running():
        return {"status": "error", "message": "Context generation already running"}

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Parse context from JSON string
    import json
    context_dict = json.loads(context) if context else {}

    transcript_lines = load_sub_data(tmp_path, include_speaker=True)
    transcript = "\n".join(transcript_lines)
    prompt_generator = PromptGenerator()
    system_prompt = prompt_generator.generate_synopsis_prompt(
        context=context_dict if context_dict else None,
        input_lang=input_lang,
        output_lang=output_lang
    )

    background_tasks.add_task(
        model_manager.run_llm_task,
        transcript,
        system_prompt,
        "synopsis",
        target="context",
        cleanup_path=tmp_path
    )
    return {"status": "processing", "message": "Synopsis generation started"}


@router.post("/api/context/generate-recap")
async def api_generate_recap(request: GenerateRecapRequest, background_tasks: BackgroundTasks):
    """Generate recap from multiple context dicts."""
    if not model_manager.llm_client or model_manager.llm_client.get_status() != "loaded":
        return {"status": "error", "message": "GPT model not loaded"}

    if model_manager.is_llm_running():
        return {"status": "error", "message": "Context generation already running"}

    all_keys = set()
    for ctx in request.contexts:
        all_keys.update(ctx.keys())

    metadata_keys = {'seriesName', 'keywords', 'inputLanguage', 'outputLanguage', 'exportDate'}
    all_keys = all_keys - metadata_keys

    sections_data = {}
    for key in all_keys:
        values = []
        for i, ctx in enumerate(request.contexts):
            value = ctx.get(key, "")
            if value and str(value).strip():
                values.append((i, str(value).strip()))
        if values:
            sections_data[key] = values

    if not sections_data:
        all_context = ""
    else:
        context_sections = []
        for key, values in sections_data.items():
            title = key.replace('_', ' ').title()
            combined = "\n\n".join([f"### Part {i+1}\n{val}" for i, val in values])
            context_sections.append(f"## {title}\n\n{combined}")
        all_context = "\n\n".join(context_sections)

    prompt_generator = PromptGenerator()
    system_prompt = prompt_generator.generate_recap_prompt(
        all_context=all_context,
        input_lang=request.input_lang,
        output_lang=request.output_lang
    )

    background_tasks.add_task(
        model_manager.run_llm_task,
        "Generate recap.",
        system_prompt,
        "recap",
        target="context"
    )
    return {"status": "processing", "message": "Recap generation started"}


@router.get("/api/context/result")
async def get_context_result():
    """Get the result of the last context generation operation."""
    if model_manager.is_llm_running():
        return {"status": "processing", "message": "Context generation in progress"}

    if model_manager.llm_error:
        error = model_manager.llm_error
        return {"status": "error", "message": error}

    if model_manager.context_result:
        result = model_manager.context_result
        return {"status": "success", "result": result}

    return {"status": "idle", "message": "No context generation has been run"}
