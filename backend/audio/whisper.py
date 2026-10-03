import os
from dataclasses import dataclass
from typing import ClassVar

import pysubs2
import whisper

from audio.devices import device_choices
from audio.interface import AudioModelInterface
from models.config import Choice, ConfigField, DropdownOption, ModelConfig, setting
from models.state import ModelState


@dataclass
class WhisperConfig(ModelConfig):
    """Settings for the OpenAI Whisper provider, saved to audio_whisper.json."""

    CONFIG_FILE: ClassVar[str] = "audio_whisper.json"
    PROVIDER: ClassVar[str] = "audio_whisper"
    TITLE: ClassVar[str] = "Whisper"

    model_name: ConfigField[str] = setting("Model", DropdownOption((
        Choice("tiny", "tiny"),
        Choice("base", "base"),
        Choice("small", "small"),
        Choice("medium", "medium"),
        Choice("large", "large"),
        Choice("turbo", "turbo"),
    )), "medium", required=True)
    device: ConfigField[str] = setting("Device", DropdownOption(device_choices), "cpu")


class AudioWhisper(AudioModelInterface[WhisperConfig]):
    """Audio transcription backend using OpenAI Whisper segment timestamps."""

    def __init__(self):
        """Load the saved Whisper settings."""
        super().__init__(WhisperConfig.load())
        self._model = None

    def initialize(self) -> None:
        """Load the Whisper model onto the configured device."""
        try:
            self._model = self._build_model()
            self._state = ModelState.LOADED
        except Exception:
            self._model = None
            self._state = ModelState.ERROR
            raise

    def shutdown(self) -> None:
        """Release the model."""
        self._model = None
        self._state = ModelState.NOT_LOADED

    def transcribe_line(self, audio_path: str, language: str) -> str:
        """Transcribe a short clip to text."""
        result = self._require_model(audio_path).transcribe(audio_path, language=language)
        return result["text"]

    def transcribe_file(self, audio_path: str, language: str) -> pysubs2.SSAFile:
        """Transcribe an audio file into a pysubs2.SSAFile using Whisper's segment timestamps."""
        result = self._require_model(audio_path).transcribe(audio_path, language=language)

        subs = pysubs2.SSAFile()
        style = subs.styles["Default"]
        style.fontsize = 55
        style.fontname = "Arial"
        subs.styles["Default"] = style

        for seg in result["segments"]:
            subs.events.append(pysubs2.SSAEvent(
                start=seg["start"] * 1000,
                end=seg["end"] * 1000,
                text=seg["text"],
            ))
        return subs

    def _build_model(self):
        """Load and return a Whisper model for the configured model name and device."""
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        return whisper.load_model(self._config.model_name.value, device=self._config.device.value)

    def _require_model(self, audio_path: str):
        """Return the loaded model, raising when it is not initialized or the audio file is missing."""
        if self._model is None:
            raise RuntimeError("Whisper model is not initialized.")
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        return self._model
