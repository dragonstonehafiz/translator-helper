import gc
import logging
import os
import warnings
from dataclasses import dataclass
from typing import ClassVar

import pysubs2
import whisperx

from audio.devices import device_choices
from audio.interface import AudioModelInterface
from models.config import Choice, ConfigField, DropdownOption, IntegerOption, ModelConfig, setting
from models.state import ModelState

# Suppress verbose output from whisperx and its dependencies
warnings.filterwarnings("ignore", category=UserWarning, module="pyannote")
warnings.filterwarnings("ignore", category=UserWarning, module="torchcodec")
logging.getLogger("whisperx").setLevel(logging.WARNING)
logging.getLogger("pyannote").setLevel(logging.WARNING)


@dataclass
class WhisperXConfig(ModelConfig):
    """Settings for the WhisperX provider, saved to audio_whisperx.json."""

    CONFIG_FILE: ClassVar[str] = "audio_whisperx.json"
    PROVIDER: ClassVar[str] = "audio_whisperx"
    TITLE: ClassVar[str] = "WhisperX"

    model_name: ConfigField[str] = setting("Model", DropdownOption((
        Choice("tiny", "tiny"),
        Choice("base", "base"),
        Choice("small", "small"),
        Choice("medium", "medium"),
        Choice("large-v2", "large-v2"),
        Choice("turbo", "turbo"),
    )), "medium", required=True)
    device: ConfigField[str] = setting("Device", DropdownOption(device_choices), "cpu")
    compute_type: ConfigField[str] = setting("Compute Type", DropdownOption((
        Choice("float32", "float32"),
        Choice("float16", "float16"),
        Choice("int8", "int8"),
    )), "float32", help="float16/int8 require CUDA GPU")
    batch_size: ConfigField[int] = setting("Batch Size", IntegerOption(min=1, max=32), 16, help="Reduce if running out of memory")


class AudioWhisperX(AudioModelInterface[WhisperXConfig]):
    """Audio transcription backend using WhisperX for word-aligned subtitle generation."""

    def __init__(self):
        """Load the saved WhisperX settings."""
        super().__init__(WhisperXConfig.load())
        self._model = None

    def initialize(self) -> None:
        """Load the WhisperX model onto the configured device."""
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
        """Transcribe the first segment of an audio file to a plain text string."""
        model = self._require_model(audio_path)
        audio = whisperx.load_audio(audio_path)
        result = model.transcribe(audio, language=language, batch_size=self._config.batch_size.value)

        segments = result.get("segments", [])
        if not segments:
            return ""
        return segments[0]["text"].strip()

    def transcribe_file(self, audio_path: str, language: str) -> pysubs2.SSAFile:
        """Transcribe an audio file into a pysubs2.SSAFile with word-aligned timestamps via WhisperX alignment."""
        model = self._require_model(audio_path)

        device = self._runtime_device()
        audio = whisperx.load_audio(audio_path)
        result = model.transcribe(audio, language=language, batch_size=self._config.batch_size.value, chunk_size=10)

        # Align for accurate word-level timestamps
        model_a, metadata = whisperx.load_align_model(language_code=language, device=device)
        result = whisperx.align(result["segments"], model_a, metadata, audio, device)

        del model_a
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        subs = pysubs2.SSAFile()
        style = subs.styles["Default"]
        style.fontsize = 55
        style.fontname = "Arial"
        subs.styles["Default"] = style

        for seg in result["segments"]:
            words = seg.get("words", [])
            first_word = next((w for w in words if "start" in w), None)
            last_word = next((w for w in reversed(words) if "end" in w), None)
            start_time = (first_word["start"] if first_word else seg["start"]) * 1000
            end_time = (last_word["end"] if last_word else seg["end"]) * 1000

            print(f"Segment: start={start_time}ms, end={end_time}ms, text='{seg['text'].strip()}'")

            line = pysubs2.SSAEvent(
                start=start_time,
                end=end_time,
                text=seg["text"].strip()
            )
            subs.events.append(line)

        return subs

    def _build_model(self):
        """Load and return a WhisperX model instance for the configured model name, device, and compute type."""
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        return whisperx.load_model(self._config.model_name.value, self._runtime_device(), compute_type=self._config.compute_type.value)

    def _runtime_device(self) -> str:
        """Return the device name ctranslate2 accepts: "cuda" or "cpu", not "cuda:0"."""
        device = self._config.device.value
        return "cuda" if device.startswith("cuda") else device

    def _require_model(self, audio_path: str):
        """Return the loaded model, raising when it is not initialized or the audio file is missing."""
        if self._model is None:
            raise RuntimeError("WhisperX model is not initialized.")
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        return self._model
