import os
from typing import Optional

from models.audio_whisperx import AudioWhisperX
from models.llm_claude import LLMClaude
from utils.logger import setup_logger

logger = setup_logger("translate-file")


class ModelManager:
    _instance: Optional["ModelManager"] = None

    def __init__(self):
        if ModelManager._instance is not None:
            raise RuntimeError("ModelManager: Please use get_instance()")

        self._llm_client: Optional[LLMClaude] = None
        self._audio_client: Optional[AudioWhisperX] = None
        self.loading_audio_model = False
        self.loading_llm_model = False
        self.llm_loading_error: Optional[str] = None
        self.audio_loading_error: Optional[str] = None

        # Eager load both clients during manager initialization.
        self.load_llm_model()
        self.load_audio_model()

    @staticmethod
    def get_instance() -> "ModelManager":
        if ModelManager._instance is None:
            ModelManager._instance = ModelManager()
        return ModelManager._instance

    def get_llm_client(self) -> Optional[LLMClaude]:
        return self._llm_client

    def get_audio_client(self) -> Optional[AudioWhisperX]:
        return self._audio_client

    def is_llm_running(self) -> bool:
        return bool(self._llm_client and self._llm_client.is_running())

    def is_audio_running(self) -> bool:
        return bool(self._audio_client and self._audio_client.is_running())

    def is_llm_ready(self) -> bool:
        return bool(self._llm_client and self._llm_client.get_status() == "loaded")

    def is_audio_ready(self) -> bool:
        return bool(self._audio_client and self._audio_client.get_status() == "loaded")

    def load_audio_model(self) -> bool:
        if self.loading_audio_model:
            return False

        try:
            self.loading_audio_model = True
            if self._audio_client is None:
                self._audio_client = AudioWhisperX()
            self._audio_client.initialize()
            self.audio_loading_error = None
            logger.info(
                "Whisper model loaded: model='%s', device='%s'",
                self._audio_client.get_model(),
                self._audio_client.get_device(),
            )
            return True
        except Exception as exc:
            self.audio_loading_error = str(exc)
            logger.error("Error loading Whisper model: %s", exc, exc_info=True)
            return False
        finally:
            self.loading_audio_model = False

    def load_llm_model(self) -> bool:
        if self.loading_llm_model:
            return False

        try:
            self.loading_llm_model = True
            if self._llm_client is None:
                self._llm_client = LLMClaude()
            self._llm_client.initialize()
            self.llm_loading_error = None
            logger.info(
                "LLM loaded: model='%s', temperature=%s",
                self._llm_client.get_model(),
                self._llm_client.get_temperature(),
            )
            return True
        except Exception as exc:
            self.llm_loading_error = str(exc)
            logger.error("Error loading LLM model: %s", exc, exc_info=True)
            return False
        finally:
            self.loading_llm_model = False

    def update_llm_settings(self, settings: dict):
        if settings and self._llm_client is not None:
            self._llm_client.configure(settings)

    def update_audio_settings(self, settings: dict):
        if settings and self._audio_client is not None:
            self._audio_client.configure(settings)

    def llm_infer(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        if self._llm_client is None:
            raise RuntimeError("LLM client not initialized.")
        return self._llm_client.infer(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def audio_transcribe_line(self, file_path: str, language: str):
        if self._audio_client is None:
            raise RuntimeError("Audio client not initialized.")
        return self._audio_client.transcribe_line(file_path, language)

    def audio_transcribe_file(self, file_path: str, language: str, original_filename: str):
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
