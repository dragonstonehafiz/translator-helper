import os
from typing import Optional

from models.audio_whisperx import AudioWhisperX
# from models.llm_claude import LLMClaude
from models.llm_deepseek import LLMDeepSeek
# from models.llm_llamacpp import LLMLlamaCpp
from models.search_tavily import SearchTavily
from interface.llm_interface import LLMInterface
from interface.audio_model_interface import AudioModelInterface
from utils.logger import setup_logger

logger = setup_logger("translator-helper")


class ModelManager:
    """Singleton that owns the lifecycle of the LLM, audio, and search clients and exposes unified infer/transcribe helpers."""

    _instance: Optional["ModelManager"] = None

    def __init__(self):
        """Initialize internal client slots and loading-state flags; use get_instance() instead."""
        if ModelManager._instance is not None:
            raise RuntimeError("ModelManager: Please use get_instance()")

        self._llm_client: Optional[LLMInterface] = None
        self._audio_client: Optional[AudioModelInterface] = None
        self._search_client: Optional[SearchTavily] = None
        self.loading_audio_model = False
        self.loading_llm_model = False
        self.loading_search_model = False
        self.llm_loading_error: Optional[str] = None
        self.audio_loading_error: Optional[str] = None
        self.search_loading_error: Optional[str] = None

    @staticmethod
    def get_instance() -> "ModelManager":
        """Return the singleton ModelManager, creating it on first call."""
        if ModelManager._instance is None:
            ModelManager._instance = ModelManager()
        return ModelManager._instance

    def get_llm_client(self) -> Optional[LLMInterface]:
        """Return the current LLM client, or None if not yet loaded."""
        return self._llm_client

    def get_audio_client(self) -> Optional[AudioModelInterface]:
        """Return the current audio client, or None if not yet loaded."""
        return self._audio_client

    def get_search_client(self) -> Optional[SearchTavily]:
        """Return the current Tavily search client, or None if not yet loaded."""
        return self._search_client

    def is_llm_running(self) -> bool:
        """Return True if the LLM client is currently executing an inference call."""
        return bool(self._llm_client and self._llm_client.is_running())

    def is_audio_running(self) -> bool:
        """Return True if the audio client is currently executing a transcription call."""
        return bool(self._audio_client and self._audio_client.is_running())

    def is_llm_ready(self) -> bool:
        """Return True if the LLM client is loaded and ready to accept inference calls."""
        return bool(self._llm_client and self._llm_client.get_status() == "loaded")

    def is_audio_ready(self) -> bool:
        """Return True if the audio client is loaded and ready to accept transcription calls."""
        return bool(self._audio_client and self._audio_client.get_status() == "loaded")

    def is_search_ready(self) -> bool:
        """Return True if the Tavily search client is loaded and ready."""
        return bool(self._search_client and self._search_client.get_status() == "loaded")

    def load_audio_model(self) -> bool:
        """Initialize the audio model; returns True on success, False if already loading or on error."""
        if self.loading_audio_model:
            return False

        try:
            self.loading_audio_model = True
            if self._audio_client is None:
                self._audio_client = AudioWhisperX()
            logger.info("Loading audio model: provider=%s model=%s", type(self._audio_client).__name__, self._audio_client.get_model())
            self._audio_client.initialize()
            self.audio_loading_error = None
            logger.info("Audio model loaded: provider=%s model=%s device=%s", type(self._audio_client).__name__, self._audio_client.get_model(), self._audio_client.get_device())
            return True
        except Exception as exc:
            self.audio_loading_error = str(exc)
            logger.error("Audio model load failed: provider=%s error=%s", type(self._audio_client).__name__ if self._audio_client else "unknown", exc, exc_info=True)
            return False
        finally:
            self.loading_audio_model = False

    def load_llm_model(self) -> bool:
        """Initialize the LLM model; returns True on success, False if already loading or on error."""
        if self.loading_llm_model:
            return False

        try:
            self.loading_llm_model = True
            if self._llm_client is None:
                self._llm_client = LLMDeepSeek()
            logger.info("Loading LLM model: provider=%s model=%s", type(self._llm_client).__name__, self._llm_client.get_model())
            self._llm_client.initialize()
            self.llm_loading_error = None
            logger.info("LLM model loaded: provider=%s model=%s temperature=%s", type(self._llm_client).__name__, self._llm_client.get_model(), self._llm_client.get_temperature())
            return True
        except Exception as exc:
            self.llm_loading_error = str(exc)
            logger.error("LLM model load failed: provider=%s error=%s", type(self._llm_client).__name__ if self._llm_client else "unknown", exc, exc_info=True)
            return False
        finally:
            self.loading_llm_model = False

    def update_llm_settings(self, settings: dict):
        """Apply settings dict to the current LLM client if one is loaded."""
        if settings and self._llm_client is not None:
            self._llm_client.configure(settings)

    def load_search_model(self) -> bool:
        """Initialize the Tavily search client; returns True on success, False if already loading or on error."""
        if self.loading_search_model:
            return False
        try:
            self.loading_search_model = True
            if self._search_client is None:
                self._search_client = SearchTavily()
            self._search_client.initialize()
            self.search_loading_error = None
            logger.info("Search model loaded: provider=Tavily")
            return True
        except Exception as exc:
            self.search_loading_error = str(exc)
            logger.error("Search model load failed: %s", exc, exc_info=True)
            return False
        finally:
            self.loading_search_model = False

    def update_search_settings(self, settings: dict) -> None:
        """Apply settings dict to the search client, creating a SearchTavily instance if none exists."""
        if settings:
            if self._search_client is None:
                self._search_client = SearchTavily()
            self._search_client.configure(settings)

    def update_audio_settings(self, settings: dict):
        """Apply settings dict to the current audio client if one is loaded."""
        if settings and self._audio_client is not None:
            self._audio_client.configure(settings)

    def llm_infer(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Delegate an inference call to the loaded LLM client; raises RuntimeError if not initialized."""
        if self._llm_client is None:
            raise RuntimeError("LLM client not initialized.")
        return self._llm_client.infer(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def audio_transcribe_line(self, file_path: str, language: str):
        """Transcribe a single audio clip to text; raises RuntimeError if audio client is not initialized."""
        if self._audio_client is None:
            raise RuntimeError("Audio client not initialized.")
        return self._audio_client.transcribe_line(file_path, language)

    def audio_transcribe_file(self, file_path: str, language: str, original_filename: str):
        """Transcribe a full audio file to an ASS subtitle file saved under outputs/transcribe-sub-files/; raises RuntimeError if audio client is not initialized."""
        if self._audio_client is None:
            raise RuntimeError("Audio client not initialized.")

        subs = self._audio_client.transcribe_file(file_path, language)
        safe_original_name = os.path.basename(original_filename)
        base_name = safe_original_name.split(".")[0]
        safe_lang = "".join(char for char in language if char.isalnum() or char in ("-", "_")) or "lang"
        output_filename = f"{base_name}.{safe_lang}.ass"
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "transcribe-sub-files")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        subs.save(output_path)
        return output_path
