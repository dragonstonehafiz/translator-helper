"""
Route definitions for Translator Helper backend.
"""

from fastapi import APIRouter, BackgroundTasks, File, UploadFile, Form
from pydantic import BaseModel
from typing import Optional
from settings import settings
import threading
import tempfile
import os
from models.llm_chatgpt import LLM_ChatGPT
from models.audio_whisper import AudioWhisper
from utils.prompts import PromptGenerator
from utils.translate_subs import translate_sub, translate_subs
from utils.utils import load_sub_data
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger()

# Server state variables
audio_client = None
llm_client = None
loading_whisper_model = False
loading_gpt_model = False
context_result = None
context_error = None
transcription_result = None
transcription_error = None
translation_result = None
translation_error = None


def _is_llm_running() -> bool:
    return bool(llm_client and llm_client.is_running())


def _is_whisper_running() -> bool:
    return bool(audio_client and audio_client.is_running())


# Startup function to load models based on settings
def startup_load_models():
    """Load models on startup based on .env configuration."""
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


# Request models
class LoadWhisperRequest(BaseModel):
    model_name: str
    device: str


class LoadGptRequest(BaseModel):
    model_name: str
    api_key: Optional[str] = None
    temperature: float


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


# Background task functions
def load_whisper_background(model_name: str, device: str):
    """Load Whisper model in background."""
    global audio_client, loading_whisper_model
    try:
        loading_whisper_model = True
        if audio_client is None:
            audio_client = AudioWhisper(model_name=model_name, device=device)
        else:
            audio_client.configure({"model_name": model_name, "device": device})
            audio_client.change_model(model_name)
            audio_client.set_device(device)
        audio_client.initialize()
        logger.info(f"Whisper model loaded: model='{audio_client.get_model()}', device='{audio_client.get_device()}'")
    except Exception as e:
        logger.error(f"Error loading Whisper model: {e}")
        print(f"Error loading Whisper model: {e}")
    finally:
        loading_whisper_model = False


def load_gpt_background(model_name: str, api_key: Optional[str], temperature: float):
    """Load GPT model in background."""
    global llm_client, loading_gpt_model
    try:
        loading_gpt_model = True
        if not api_key and (llm_client is None or not llm_client.is_ready()):
            raise ValueError("OpenAI API key not provided and no stored key is available.")
        if llm_client is None:
            llm_client = LLM_ChatGPT(model_name=model_name, api_key=api_key)
        else:
            if api_key:
                llm_client.configure({"api_key": api_key})
            llm_client.change_model(model_name)
        llm_client.set_temperature(temperature)
        llm_client.initialize()
        logger.info(f"LLM loaded: model='{llm_client.get_model()}', temperature={llm_client.get_temperature()}")
    except Exception as e:
        logger.error(f"Error loading GPT model: {e}")
        print(f"Error loading GPT model: {e}")
    finally:
        loading_gpt_model = False


def generate_character_list_background(file_path: str, input_lang: str, output_lang: str, context: dict):
    """Generate character list in background."""
    global context_result, context_error, llm_client
    try:
        if llm_client:
            llm_client.set_running(True)
        context_result = None
        context_error = None
        logger.info(f"Starting character list generation: file='{file_path}'")

        # Extract transcript from subtitle file
        transcript_lines = load_sub_data(file_path, include_speaker=True)
        transcript = "\n".join(transcript_lines)

        prompt_generator = PromptGenerator()
        system_prompt = prompt_generator.generate_character_list_prompt(
            context=context if context else None,
            input_lang=input_lang,
            output_lang=output_lang
        )
        result = llm_client.infer(
            prompt=transcript,
            system_prompt=system_prompt,
            temperature=llm_client.get_temperature()
        )
        context_result = {"type": "character_list", "data": result}
        logger.info("Successfully completed character list generation")
    except Exception as e:
        logger.error(f"Error generating character list: {e}")
        print(f"Error generating character list: {e}")
        context_error = str(e)
    finally:
        if llm_client:
            llm_client.set_running(False)
        logger.info("Character list generation process completed")
        # Cleanup temp file
        try:
            os.remove(file_path)
        except:
            pass


def generate_summary_background(file_path: str, input_lang: str, output_lang: str, context: dict):
    """Generate high-level summary in background."""
    global context_result, context_error, llm_client
    try:
        if llm_client:
            llm_client.set_running(True)
        context_result = None
        context_error = None
        logger.info(f"Starting summary generation: file='{file_path}'")

        # Extract transcript from subtitle file
        transcript_lines = load_sub_data(file_path, include_speaker=True)
        transcript = "\n".join(transcript_lines)

        prompt_generator = PromptGenerator()
        system_prompt = prompt_generator.generate_summary_prompt(
            context=context if context else None,
            input_lang=input_lang,
            output_lang=output_lang
        )
        result = llm_client.infer(
            prompt=transcript,
            system_prompt=system_prompt,
            temperature=llm_client.get_temperature()
        )
        context_result = {"type": "summary", "data": result}
        logger.info("Successfully completed summary generation")
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        print(f"Error generating summary: {e}")
        context_error = str(e)
    finally:
        if llm_client:
            llm_client.set_running(False)
        logger.info("Summary generation process completed")
        # Cleanup temp file
        try:
            os.remove(file_path)
        except:
            pass


def generate_synopsis_background(file_path: str, input_lang: str, output_lang: str, context: dict):
    """Generate synopsis in background."""
    global context_result, context_error, llm_client
    try:
        if llm_client:
            llm_client.set_running(True)
        context_result = None
        context_error = None
        logger.info(f"Starting synopsis generation: file='{file_path}'")

        # Extract transcript from subtitle file
        transcript_lines = load_sub_data(file_path, include_speaker=True)
        transcript = "\n".join(transcript_lines)

        prompt_generator = PromptGenerator()
        system_prompt = prompt_generator.generate_synopsis_prompt(
            context=context if context else None,
            input_lang=input_lang,
            output_lang=output_lang
        )
        result = llm_client.infer(
            prompt=transcript,
            system_prompt=system_prompt,
            temperature=llm_client.get_temperature()
        )
        context_result = {"type": "synopsis", "data": result}
        logger.info("Successfully completed synopsis generation")
    except Exception as e:
        logger.error(f"Error generating synopsis: {e}")
        print(f"Error generating synopsis: {e}")
        context_error = str(e)
    finally:
        if llm_client:
            llm_client.set_running(False)
        logger.info("Synopsis generation process completed")
        # Cleanup temp file
        try:
            os.remove(file_path)
        except:
            pass


def generate_recap_background(input_lang: str, output_lang: str, contexts: list[dict]):
    """Generate recap from multiple contexts in background."""
    global context_result, context_error, llm_client
    try:
        if llm_client:
            llm_client.set_running(True)
        context_result = None
        context_error = None
        logger.info(f"Starting recap generation: contexts={len(contexts)}")
        all_keys = set()
        for ctx in contexts:
            all_keys.update(ctx.keys())

        metadata_keys = {'seriesName', 'keywords', 'inputLanguage', 'outputLanguage', 'exportDate'}
        all_keys = all_keys - metadata_keys

        sections_data = {}
        for key in all_keys:
            values = []
            for i, ctx in enumerate(contexts):
                value = ctx.get(key, "")
                if value and str(value).strip():
                    values.append((i, str(value).strip()))
            if values:
                sections_data[key] = values

        if not sections_data:
            result = ""
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
                input_lang=input_lang,
                output_lang=output_lang
            )
            result = llm_client.infer(
                prompt="Generate recap.",
                system_prompt=system_prompt,
                temperature=llm_client.get_temperature()
            )
        context_result = {"type": "recap", "data": result}
        logger.info("Successfully completed recap generation")
    except Exception as e:
        logger.error(f"Error generating recap: {e}")
        print(f"Error generating recap: {e}")
        context_error = str(e)
    finally:
        if llm_client:
            llm_client.set_running(False)
        logger.info("Recap generation process completed")


def transcribe_line_background(file_path: str, language: str):
    """Transcribe audio in background."""
    global transcription_result, transcription_error, audio_client
    try:
        if audio_client:
            audio_client.set_running(True)
        transcription_result = None
        transcription_error = None
        logger.info(f"Starting audio transcription: file='{file_path}', language='{language}'")

        result = audio_client.transcribe_line(file_path, language)
        transcription_result = {"type": "transcription", "data": result}
        logger.info("Successfully completed audio transcription")
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        print(f"Error transcribing audio: {e}")
        transcription_error = str(e)
    finally:
        if audio_client:
            audio_client.set_running(False)
        logger.info("Audio transcription process completed")
        # Cleanup temp file
        try:
            os.remove(file_path)
        except:
            pass


def translate_line_background(text: str, context: dict, input_lang: str, output_lang: str):
    """Translate a single line in background."""
    global translation_result, translation_error, llm_client
    try:
        if llm_client:
            llm_client.set_running(True)
        translation_result = None
        translation_error = None
        logger.info(f"Starting line translation: input_lang='{input_lang}', output_lang='{output_lang}'")

        result = translate_sub(
            llm=llm_client,
            text=text,
            context=context if context else {},
            input_lang=input_lang,
            target_lang=output_lang,
            temperature=llm_client.get_temperature()
        )
        translation_result = {"type": "line_translation", "data": result}
        logger.info("Successfully completed line translation")
    except Exception as e:
        logger.error(f"Error translating line: {e}")
        print(f"Error translating line: {e}")
        translation_error = str(e)
    finally:
        if llm_client:
            llm_client.set_running(False)
        logger.info("Line translation process completed")


def translate_file_background(file_path: str, context: dict, input_lang: str, output_lang: str, context_window: int):
    """Translate subtitle file in background."""
    global translation_result, translation_error, llm_client
    try:
        if llm_client:
            llm_client.set_running(True)
        translation_result = None
        translation_error = None
        logger.info(f"Starting file translation: file='{file_path}', input_lang='{input_lang}', output_lang='{output_lang}'")

        # Load subtitle file
        import pysubs2
        subs = pysubs2.load(file_path)

        import time
        start_time = time.time()
        # Translate
        translated_subs = translate_subs(
            llm=llm_client,
            subs=subs,
            context=context if context else {},
            context_window=context_window,
            input_lang=input_lang,
            target_lang=output_lang,
            temperature=llm_client.get_temperature()
        )
        elapsed_seconds = time.time() - start_time
        logger.info("File translation completed in %.2fs", elapsed_seconds)

        # Save to temp file
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
        if llm_client:
            llm_client.set_running(False)
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


@router.get("/api/running")
async def get_running_status():
    """Get the status of running operations."""
    return {
        "running_llm": _is_llm_running(),
        "running_whisper": _is_whisper_running(),
        "loading_whisper_model": loading_whisper_model,
        "loading_gpt_model": loading_gpt_model
    }


@router.get("/api/server/variables")
async def get_server_variables():
    """Get current server configuration variables."""
    openai_ready = bool(llm_client and llm_client.is_ready())
    whisper_ready = bool(audio_client)
    is_ready = openai_ready and whisper_ready

    return {
        "audio": (audio_client.get_server_variables() if audio_client else {"whisper_model": "", "device": ""}),
        "llm": (llm_client.get_server_variables() if llm_client else {"openai_model": "", "temperature": 0.5}),
        "openai_ready": openai_ready,
        "whisper_ready": whisper_ready,
        "is_ready": is_ready
    }


@router.get("/api/settings/schema")
async def get_settings_schema():
    """Get settings schema for model configuration."""
    audio_schema = audio_client.get_settings_schema() if audio_client else AudioWhisper().get_settings_schema()
    llm_schema = llm_client.get_settings_schema() if llm_client else LLM_ChatGPT().get_settings_schema()
    return {"audio": audio_schema, "llm": llm_schema}


@router.post("/api/settings/update")
async def update_settings(request: UpdateSettingsRequest):
    """Update model settings without loading models."""
    global audio_client, llm_client

    provider = request.provider.lower()
    settings_payload = request.settings or {}

    if provider == "audio":
        if audio_client is None:
            audio_client = AudioWhisper()
        audio_client.configure(settings_payload)
        if "model_name" in settings_payload:
            audio_client.change_model(settings_payload["model_name"])
        if "device" in settings_payload:
            audio_client.set_device(settings_payload["device"])
        return {"status": "ok", "message": "Audio settings updated"}

    if provider == "llm":
        if llm_client is None:
            llm_client = LLM_ChatGPT(
                model_name=settings_payload.get("model_name", "gpt-4o"),
                api_key=settings_payload.get("api_key")
            )
        llm_client.configure(settings_payload)
        if "model_name" in settings_payload:
            llm_client.change_model(settings_payload["model_name"])
        if "temperature" in settings_payload:
            llm_client.set_temperature(settings_payload["temperature"])
        return {"status": "ok", "message": "LLM settings updated"}

    return {"status": "error", "message": "Unknown provider"}


@router.post("/api/transcribe/transcribe-line")
async def api_transcribe_line(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form(...)
):
    """Transcribe audio file using Whisper model."""
    global audio_client

    if _is_whisper_running():
        return {"status": "error", "message": "Transcription is already running"}

    if not audio_client:
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


@router.get("/api/transcribe/result")
async def get_transcription_result():
    """Get the result of the transcription."""
    global transcription_result, transcription_error

    if _is_whisper_running():
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
    global llm_client

    if _is_llm_running():
        return {"status": "error", "message": "Translation is already running"}

    if not llm_client or not llm_client.is_ready():
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
    global llm_client

    if _is_llm_running():
        return {"status": "error", "message": "Translation is already running"}

    if not llm_client or not llm_client.is_ready():
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


@router.get("/api/translate/result")
async def get_translation_result():
    """Get the result of the translation."""
    global translation_result, translation_error

    if _is_llm_running():
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


@router.post("/api/load-whisper-model")
async def load_whisper(request: LoadWhisperRequest, background_tasks: BackgroundTasks):
    """Load Whisper model in background."""
    global loading_whisper_model

    if loading_whisper_model:
        return {"status": "error", "message": "Whisper model is already loading"}

    background_tasks.add_task(load_whisper_background, request.model_name, request.device)
    return {"status": "loading", "message": "Whisper model loading started"}


@router.post("/api/load-gpt-model")
async def load_gpt(request: LoadGptRequest, background_tasks: BackgroundTasks):
    """Load GPT model in background."""
    global loading_gpt_model

    if loading_gpt_model:
        return {"status": "error", "message": "GPT model is already loading"}

    background_tasks.add_task(load_gpt_background, request.model_name, request.api_key, request.temperature)
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
    global llm_client

    if not llm_client or not llm_client.is_ready():
        return {"status": "error", "message": "GPT model not loaded"}

    if _is_llm_running():
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


@router.post("/api/context/generate-high-level-summary")
async def api_generate_high_level_summary(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context: str = Form("{}")
):
    """Generate high-level summary from subtitle file."""
    global llm_client

    if not llm_client or not llm_client.is_ready():
        return {"status": "error", "message": "GPT model not loaded"}

    if _is_llm_running():
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


@router.post("/api/context/generate-synopsis")
async def api_generate_synopsis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    input_lang: str = Form("ja"),
    output_lang: str = Form("en"),
    context: str = Form("{}")
):
    """Generate synopsis from subtitle file."""
    global llm_client

    if not llm_client or not llm_client.is_ready():
        return {"status": "error", "message": "GPT model not loaded"}

    if _is_llm_running():
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


@router.post("/api/context/generate-recap")
async def api_generate_recap(request: GenerateRecapRequest, background_tasks: BackgroundTasks):
    """Generate recap from multiple context dicts."""
    global llm_client

    if not llm_client or not llm_client.is_ready():
        return {"status": "error", "message": "GPT model not loaded"}

    if _is_llm_running():
        return {"status": "error", "message": "Context generation already running"}

    background_tasks.add_task(
        generate_recap_background,
        request.input_lang,
        request.output_lang,
        request.contexts
    )
    return {"status": "processing", "message": "Recap generation started"}


@router.get("/api/context/result")
async def get_context_result():
    """Get the result of the last context generation operation."""
    global context_result, context_error

    if _is_llm_running():
        return {"status": "processing", "message": "Context generation in progress"}

    if context_error:
        error = context_error
        return {"status": "error", "message": error}

    if context_result:
        result = context_result
        return {"status": "success", "result": result}

    return {"status": "idle", "message": "No context generation has been run"}
